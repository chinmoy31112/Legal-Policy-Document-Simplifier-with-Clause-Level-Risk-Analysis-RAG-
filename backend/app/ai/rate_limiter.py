"""
Distributed Redis-backed Rate Limiter, Circuit Breaker, and User Quota System.

Enforces:
- Shared per-model rate limiting for Gemini Embeddings and Gemini LLM.
- RPM (Requests Per Minute) and TPM (Tokens Per Minute) sliding-window pacing.
- In-memory fallback if Redis is unreachable or in lightweight test mode.
- 80% quota utilization telemetry warnings.
- Circuit breaker with exponential backoff and jitter honoring Retry-After.
- Per-user quotas and job resume tracking.
"""

import asyncio
import random
import time
from enum import Enum

from redis import asyncio as aioredis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when request is rejected because the circuit breaker is open."""

    def __init__(self, model_name: str, wait_seconds: float):
        super().__init__(
            f"Circuit breaker OPEN for model '{model_name}'. Downstream rate limits or failures active. Retry in {wait_seconds:.1f}s."
        )
        self.model_name = model_name
        self.wait_seconds = wait_seconds


class UserQuotaExceededError(Exception):
    """Raised when a user exceeds their document or clause processing quota."""

    pass


class DailyQuotaExceededError(Exception):
    """Raised when the daily request budget (RPD) for a model is exhausted."""

    def __init__(
        self,
        model_name: str,
        current_rpd: int,
        max_rpd: int,
        seconds_until_reset: float,
    ):
        self.model_name = model_name
        self.current_rpd = current_rpd
        self.max_rpd = max_rpd
        self.seconds_until_reset = seconds_until_reset
        hours = int(seconds_until_reset // 3600)
        minutes = int((seconds_until_reset % 3600) // 60)
        super().__init__(
            f"Daily API quota reached for model '{model_name}' ({current_rpd}/{max_rpd} requests used). "
            f"Resets at 00:00 UTC (in {hours}h {minutes}m)."
        )


class CircuitBreaker:
    """
    Circuit breaker preventing cascading failures when Gemini API returns 429 or outages.
    Transitions: CLOSED -> OPEN (on threshold consecutive failures) -> HALF_OPEN (after recovery timeout).
    """

    def __init__(
        self,
        model_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ):
        self.model_name = model_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.open_until: float = 0.0
        self._lock = asyncio.Lock()

    async def can_execute(self) -> tuple[bool, float]:
        """Check if execution is allowed or return required wait time."""
        async with self._lock:
            now = time.monotonic()
            if self.state == CircuitState.CLOSED:
                return True, 0.0

            if self.state == CircuitState.OPEN:
                if now >= self.open_until:
                    self.state = CircuitState.HALF_OPEN
                    logger.info("circuit_breaker_half_open_probe", model=self.model_name)
                    return True, 0.0
                return False, max(0.1, self.open_until - now)

            # HALF_OPEN state allows a probe request
            return True, 0.0

    async def record_success(self) -> None:
        """Record successful execution and reset failure state."""
        async with self._lock:
            if self.state != CircuitState.CLOSED:
                logger.info("circuit_breaker_closed", model=self.model_name)
            self.state = CircuitState.CLOSED
            self.consecutive_failures = 0
            self.open_until = 0.0

    async def record_failure(self, retry_after: float | None = None) -> float:
        """Record a failure (e.g. 429), increment count, and trip circuit if threshold exceeded."""
        async with self._lock:
            self.consecutive_failures += 1
            now = time.monotonic()
            effective_timeout = max(self.recovery_timeout, (retry_after or 0.0))

            if self.consecutive_failures >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.open_until = now + effective_timeout
                logger.warning(
                    "circuit_breaker_tripped_open",
                    model=self.model_name,
                    consecutive_failures=self.consecutive_failures,
                    timeout_seconds=round(effective_timeout, 2),
                )
                return effective_timeout
            return 0.0


# Lua script for atomic sliding-window rate limiting in Redis
LUA_SLIDING_WINDOW = """
local rpm_key = KEYS[1]
local tpm_key = KEYS[2]
local now = tonumber(ARGV[1])
local max_rpm = tonumber(ARGV[2])
local max_tpm = tonumber(ARGV[3])
local req_tokens = tonumber(ARGV[4])
local member_id = ARGV[5]

local cutoff = now - 60.0

-- 1. Prune expired entries older than 60 seconds
redis.call('ZREMRANGEBYSCORE', rpm_key, '-inf', cutoff)
redis.call('ZREMRANGEBYSCORE', tpm_key, '-inf', cutoff)

-- 2. Count current RPM
local current_rpm = redis.call('ZCARD', rpm_key)

-- 3. Calculate current TPM
local tpm_entries = redis.call('ZRANGEBYSCORE', tpm_key, cutoff, '+inf')
local current_tpm = 0
for i, entry in ipairs(tpm_entries) do
    local colon_idx = string.find(entry, ":")
    if colon_idx then
        local toks = tonumber(string.sub(entry, colon_idx + 1))
        if toks then
            current_tpm = current_tpm + toks
        end
    end
end

-- 4. Check limits
if current_rpm >= max_rpm or (current_tpm + req_tokens) > max_tpm then
    local oldest = redis.call('ZRANGE', rpm_key, 0, 0, 'WITHSCORES')
    local wait_time = 1.0
    if oldest and #oldest >= 2 then
        local oldest_ts = tonumber(oldest[2])
        wait_time = math.max(0.1, (oldest_ts + 60.0) - now + 0.05)
    end
    return {0, wait_time, current_rpm, current_tpm}
end

-- 5. Record request and tokens
redis.call('ZADD', rpm_key, now, member_id)
redis.call('ZADD', tpm_key, now, member_id .. ":" .. req_tokens)
redis.call('EXPIRE', rpm_key, 70)
redis.call('EXPIRE', tpm_key, 70)

return {1, 0, current_rpm + 1, current_tpm + req_tokens}
"""


class SharedModelRateLimiter:
    """
    Shared rate limiter for a specific model (e.g. gemini-embedding-2 or gemini-2.5-flash).
    Features:
    - Shared Redis backend for multi-worker synchronization.
    - Automatic in-memory sliding window fallback if Redis is unavailable.
    - RPM (requests/min) and TPM (tokens/min) sliding windows.
    - Enforced minimum inter-request spacing to prevent micro-bursts.
    - 80% usage telemetry warning.
    - Integrated Circuit Breaker.
    """

    def __init__(
        self,
        model_name: str,
        max_rpm: int | None = None,
        max_tpm: int | None = None,
        max_rpd: int | None = None,
        redis_url: str | None = None,
        min_interval: float | None = None,
    ):
        self.model_name = model_name
        settings = get_settings()
        limits = settings.get_model_limits(model_name)
        self.max_rpm = max(1, max_rpm if max_rpm is not None else limits["rpm"])
        self.max_tpm = max(100, max_tpm if max_tpm is not None else limits["tpm"])
        self.max_rpd = max(1, max_rpd if max_rpd is not None else limits["rpd"])
        self.min_interval = (
            min_interval
            if min_interval is not None
            else (60.0 / self.max_rpm if self.max_rpm >= 10 else 0.0)
        )
        self.circuit_breaker = CircuitBreaker(model_name=model_name)

        self._redis_url = redis_url or settings.redis_url
        self._redis: aioredis.Redis | None = None
        self._redis_available: bool = True
        self._script_sha: str | None = None

        # In-memory fallback structures: list of (timestamp, tokens, member_id)
        self._local_history: list[tuple[float, int, str]] = []
        self._daily_counts: dict[str, int] = {}
        self._last_dispatch_time: float = 0.0
        self._lock = asyncio.Lock()

    def _seconds_until_midnight_utc(self) -> float:
        from datetime import datetime, timedelta, timezone

        now_utc = datetime.now(timezone.utc)
        tomorrow_utc = (now_utc + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return max(1.0, (tomorrow_utc - now_utc).total_seconds())

    async def get_daily_usage(self) -> tuple[int, int]:
        """Return (current_rpd, max_rpd) for today UTC."""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            redis_client = await self._get_redis()
            if redis_client is not None:
                rpd_key = f"ratelimit:rpd:{self.model_name}:{today_str}"
                val = await redis_client.get(rpd_key)
                cur = int(val) if val else 0
                return cur, self.max_rpd
        except Exception:
            self._redis = None
        async with self._lock:
            return self._daily_counts.get(today_str, 0), self.max_rpd

    async def reset_daily_usage(self) -> None:
        """Reset daily usage counter (primarily for testing)."""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            redis_client = await self._get_redis()
            if redis_client is not None:
                rpd_key = f"ratelimit:rpd:{self.model_name}:{today_str}"
                await redis_client.delete(rpd_key)
        except Exception:
            self._redis = None
        async with self._lock:
            self._daily_counts[today_str] = 0

    async def _get_redis(self) -> aioredis.Redis | None:
        """Lazy connection to Redis with graceful offline fallback."""
        if not self._redis_available:
            return None

        if self._redis is not None:
            try:
                current_loop = asyncio.get_running_loop()
                pool = getattr(self._redis, "connection_pool", None)
                if pool is not None:
                    pool_loop = getattr(pool, "_loop", None)
                    if pool_loop is not None and pool_loop is not current_loop:
                        self._redis = None
            except Exception:
                self._redis = None

        if self._redis is None:
            try:
                r = aioredis.from_url(
                    self._redis_url,
                    socket_connect_timeout=0.5,
                    socket_timeout=1.0,
                    decode_responses=True,
                )
                await r.ping()
                self._redis = r
            except Exception as err:
                logger.info(
                    "redis_rate_limiter_unavailable_using_memory",
                    model=self.model_name,
                    error=str(err),
                )
                self._redis_available = False
                self._redis = None
        return self._redis

    async def acquire(self, estimated_tokens: int = 1) -> None:
        """
        Wait until capacity is available under both RPM and TPM quotas.
        Logs telemetry and emits a warning when utilization exceeds 80%.
        """
        while True:
            # 1. Check Circuit Breaker
            can_run, cb_wait = await self.circuit_breaker.can_execute()
            if not can_run:
                logger.warning(
                    "rate_limiter_waiting_on_circuit_breaker",
                    model=self.model_name,
                    wait_seconds=round(cb_wait, 2),
                )
                await asyncio.sleep(cb_wait)
                continue

            # 2. Acquire from Redis or fallback to In-Memory
            allowed, wait_sec, cur_rpm, cur_tpm = False, 0.0, 0, 0
            redis_client = await self._get_redis()
            if redis_client is not None:
                try:
                    allowed, wait_sec, cur_rpm, cur_tpm = await self._acquire_redis(
                        redis_client, estimated_tokens
                    )
                except Exception as exc:
                    if isinstance(exc, DailyQuotaExceededError):
                        raise exc
                    logger.warning("redis_rate_limit_error_fallback", error=str(exc))
                    self._redis = None
                    allowed, wait_sec, cur_rpm, cur_tpm = await self._acquire_memory(estimated_tokens)
            else:
                allowed, wait_sec, cur_rpm, cur_tpm = await self._acquire_memory(estimated_tokens)

            # 3. Telemetry & 80% Utilization Warning
            rpm_util = cur_rpm / self.max_rpm
            tpm_util = cur_tpm / self.max_tpm

            if rpm_util >= 0.80 or tpm_util >= 0.80:
                logger.warning(
                    "gemini_rate_limit_approaching_quota",
                    model=self.model_name,
                    rpm_utilization=f"{round(rpm_util * 100, 1)}%",
                    tpm_utilization=f"{round(tpm_util * 100, 1)}%",
                    current_rpm=cur_rpm,
                    max_rpm=self.max_rpm,
                    current_tpm=cur_tpm,
                    max_tpm=self.max_tpm,
                    threshold="80%",
                )
            else:
                logger.debug(
                    "gemini_rate_limit_metrics",
                    model=self.model_name,
                    current_rpm=cur_rpm,
                    max_rpm=self.max_rpm,
                    current_tpm=cur_tpm,
                    max_tpm=self.max_tpm,
                )

            if allowed:
                return

            if wait_sec > 0:
                # Add slight random jitter (50ms - 200ms) to avoid lockstep wakeups
                sleep_duration = wait_sec + random.uniform(0.05, 0.20)
                logger.info(
                    "gemini_rate_limit_throttle_wait",
                    model=self.model_name,
                    wait_seconds=round(sleep_duration, 2),
                    current_rpm=cur_rpm,
                    current_tpm=cur_tpm,
                )
                await asyncio.sleep(sleep_duration)

    async def _acquire_redis(
        self, redis_client: aioredis.Redis, tokens: int
    ) -> tuple[bool, float, int, int]:
        """Atomic Redis Lua script acquisition with daily budget enforcement."""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rpd_key = f"ratelimit:rpd:{self.model_name}:{today_str}"

        # Check daily budget (RPD)
        cur_rpd_raw = await redis_client.get(rpd_key)
        cur_rpd = int(cur_rpd_raw) if cur_rpd_raw else 0
        if cur_rpd >= self.max_rpd:
            wait_time = self._seconds_until_midnight_utc()
            raise DailyQuotaExceededError(
                model_name=self.model_name,
                current_rpd=cur_rpd,
                max_rpd=self.max_rpd,
                seconds_until_reset=wait_time,
            )

        if cur_rpd / self.max_rpd >= 0.80:
            logger.warning(
                "gemini_daily_quota_approaching_limit",
                model=self.model_name,
                current_rpd=cur_rpd,
                max_rpd=self.max_rpd,
                rpd_utilization=f"{round((cur_rpd / self.max_rpd) * 100, 1)}%",
            )

        now = time.time()
        rpm_key = f"ratelimit:rpm:{self.model_name}"
        tpm_key = f"ratelimit:tpm:{self.model_name}"
        member_id = f"{now:.6f}_{random.randint(1000, 9999)}"

        try:
            res = await redis_client.eval(  # type: ignore[misc]
                LUA_SLIDING_WINDOW,
                2,
                rpm_key,
                tpm_key,
                str(now),
                str(self.max_rpm),
                str(self.max_tpm),
                str(tokens),
                member_id,
            )
            # res: [allowed (0 or 1), wait_time, cur_rpm, cur_tpm]
            allowed = bool(res[0])
            wait_time = float(res[1])
            cur_rpm = int(res[2])
            cur_tpm = int(res[3])

            # Pacing delay
            async with self._lock:
                now_mono = time.monotonic()
                spacing_wait = max(0.0, (self._last_dispatch_time + self.min_interval) - now_mono)
                if allowed and spacing_wait > 0:
                    return False, spacing_wait, cur_rpm, cur_tpm
                if allowed:
                    self._last_dispatch_time = now_mono
                    # Record daily request in Redis
                    await redis_client.incr(rpd_key)
                    await redis_client.expire(rpd_key, 90000)

            return allowed, wait_time, cur_rpm, cur_tpm

        except DailyQuotaExceededError:
            raise
        except Exception as err:
            logger.warning("redis_lua_eval_failed_falling_back", error=str(err))
            self._redis_available = False
            return await self._acquire_memory(tokens)

    async def _acquire_memory(self, tokens: int) -> tuple[bool, float, int, int]:
        """In-memory sliding-window fallback with daily budget enforcement."""
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        async with self._lock:
            # Check daily budget
            cur_rpd = self._daily_counts.get(today_str, 0)
            if cur_rpd >= self.max_rpd:
                wait_time = self._seconds_until_midnight_utc()
                raise DailyQuotaExceededError(
                    model_name=self.model_name,
                    current_rpd=cur_rpd,
                    max_rpd=self.max_rpd,
                    seconds_until_reset=wait_time,
                )

            if cur_rpd / self.max_rpd >= 0.80:
                logger.warning(
                    "gemini_daily_quota_approaching_limit",
                    model=self.model_name,
                    current_rpd=cur_rpd,
                    max_rpd=self.max_rpd,
                    rpd_utilization=f"{round((cur_rpd / self.max_rpd) * 100, 1)}%",
                )

            now_mono = time.monotonic()
            cutoff = now_mono - 60.0

            # Prune older than 60s
            self._local_history = [
                entry for entry in self._local_history if entry[0] > cutoff
            ]

            cur_rpm = len(self._local_history)
            cur_tpm = sum(entry[1] for entry in self._local_history)

            # Check limits
            rpm_full = cur_rpm >= self.max_rpm
            tpm_full = (cur_tpm + tokens) > self.max_tpm
            spacing_wait = max(0.0, (self._last_dispatch_time + self.min_interval) - now_mono)

            if rpm_full or tpm_full:
                oldest_ts = self._local_history[0][0] if self._local_history else now_mono
                wait_time = max(0.1, (oldest_ts + 60.0) - now_mono + 0.05)
                return False, wait_time, cur_rpm, cur_tpm

            if spacing_wait > 0:
                return False, spacing_wait, cur_rpm, cur_tpm

            # Grant capacity
            member_id = f"{now_mono:.4f}"
            self._local_history.append((now_mono, tokens, member_id))
            self._last_dispatch_time = now_mono
            self._daily_counts[today_str] = cur_rpd + 1
            return True, 0.0, cur_rpm + 1, cur_tpm + tokens


class UserQuotaLimiter:
    """
    Per-user monthly clause processing quota and rate limiter.
    Ensures a single user cannot monopolize shared Gemini quotas.
    """

    def __init__(
        self,
        monthly_clause_quota: int = 500,
        rpm_quota: int = 30,
        redis_url: str | None = None,
    ):
        self.monthly_clause_quota = monthly_clause_quota
        self.rpm_quota = rpm_quota
        self._redis_url = redis_url or get_settings().redis_url
        self._local_counts: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def check_and_increment(self, user_id: str, clause_count: int) -> None:
        """Verify user is within quota and record usage. Raises UserQuotaExceededError if exceeded."""
        if not user_id:
            return

        month_str = time.strftime("%Y-%m")
        redis_key = f"user_quota:{user_id}:{month_str}"

        try:
            r = aioredis.from_url(
                self._redis_url, socket_connect_timeout=0.5, decode_responses=True
            )
            current = await r.incrby(redis_key, clause_count)
            await r.expire(redis_key, 35 * 86400)
            await r.aclose()

            if current > self.monthly_clause_quota:
                raise UserQuotaExceededError(
                    f"User '{user_id}' monthly quota exceeded: {current}/{self.monthly_clause_quota} clauses."
                )
        except UserQuotaExceededError:
            raise
        except Exception:
            # Fallback in-memory tracking
            async with self._lock:
                cur = self._local_counts.get(user_id, 0) + clause_count
                self._local_counts[user_id] = cur
                if cur > self.monthly_clause_quota:
                    raise UserQuotaExceededError(
                        f"User '{user_id}' monthly quota exceeded: {cur}/{self.monthly_clause_quota} clauses."
                    )


# Global singletons for application models
_limiters: dict[str, SharedModelRateLimiter] = {}
_user_quota_limiter: UserQuotaLimiter | None = None


def get_model_rate_limiter(
    model_name: str,
    max_rpm: int | None = None,
    max_tpm: int | None = None,
    max_rpd: int | None = None,
) -> SharedModelRateLimiter:
    """Get or construct the shared model rate limiter for a specific Gemini model."""
    settings = get_settings()
    limits = settings.get_model_limits(model_name)
    rpm = max_rpm if max_rpm is not None else limits["rpm"]
    tpm = max_tpm if max_tpm is not None else limits["tpm"]
    rpd = max_rpd if max_rpd is not None else limits["rpd"]

    key = f"{model_name}:{rpm}:{tpm}:{rpd}"
    if key not in _limiters:
        _limiters[key] = SharedModelRateLimiter(
            model_name=model_name,
            max_rpm=rpm,
            max_tpm=tpm,
            max_rpd=rpd,
        )
    return _limiters[key]


def get_user_quota_limiter() -> UserQuotaLimiter:
    """Get or construct the singleton user quota limiter."""
    global _user_quota_limiter
    if _user_quota_limiter is None:
        settings = get_settings()
        _user_quota_limiter = UserQuotaLimiter(
            monthly_clause_quota=settings.per_user_monthly_clause_quota,
            rpm_quota=settings.per_user_rpm_quota,
        )
    return _user_quota_limiter


def calculate_jittered_backoff(
    attempt: int,
    retry_after: float | None = None,
    min_wait: float = 1.0,
    max_wait: float = 45.0,
) -> float:
    """
    Calculate exponential backoff with full jitter honoring Retry-After.
    Prevents thundering herd problems when multiple tasks retry.
    """
    if retry_after is not None and retry_after > 0:
        return retry_after + random.uniform(0.1, 0.8)

    base = min(max_wait, min_wait * (2 ** attempt))
    jitter = random.uniform(0.1, 0.5 * (attempt + 1))
    return base + jitter
