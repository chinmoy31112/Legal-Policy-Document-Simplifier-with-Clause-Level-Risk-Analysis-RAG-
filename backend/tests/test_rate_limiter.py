"""
Unit tests for SharedModelRateLimiter, CircuitBreaker, and UserQuotaLimiter.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from app.ai.rate_limiter import (
    CircuitBreaker,
    CircuitState,
    SharedModelRateLimiter,
    UserQuotaExceededError,
    UserQuotaLimiter,
    calculate_jittered_backoff,
)


@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    """Verify CircuitBreaker trips to OPEN after threshold failures and recovers to CLOSED."""
    cb = CircuitBreaker(model_name="test-model", failure_threshold=3, recovery_timeout=0.1)

    # 1. Starts CLOSED
    can_run, wait_sec = await cb.can_execute()
    assert can_run is True
    assert cb.state == CircuitState.CLOSED

    # 2. Record 2 failures (below threshold)
    await cb.record_failure()
    await cb.record_failure()
    assert cb.state == CircuitState.CLOSED

    # 3. 3rd failure trips to OPEN
    await cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # 4. Immediate execution is rejected while OPEN
    can_run, wait_sec = await cb.can_execute()
    assert can_run is False
    assert wait_sec > 0.0

    # 5. Wait for recovery timeout -> transitions to HALF_OPEN
    await asyncio.sleep(0.12)
    can_run, _ = await cb.can_execute()
    assert can_run is True
    assert cb.state == CircuitState.HALF_OPEN

    # 6. Success in HALF_OPEN resets to CLOSED
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_shared_rate_limiter_rpm_and_tpm():
    """Verify SharedModelRateLimiter enforces both RPM and TPM capacity."""
    limiter = SharedModelRateLimiter(
        model_name="test-limiter",
        max_rpm=3,
        max_tpm=100,
        min_interval=0.0,
    )
    # Ensure memory fallback for predictable test
    limiter._redis_available = False

    # Dispatch 3 requests consuming 30 tokens each = 90 tokens
    await limiter.acquire(estimated_tokens=30)
    await limiter.acquire(estimated_tokens=30)
    await limiter.acquire(estimated_tokens=30)
    assert len(limiter._local_history) == 3

    # Next request should be blocked on RPM (3/3 used) or TPM (90 + 30 > 100)
    allowed, wait_sec, cur_rpm, cur_tpm = await limiter._acquire_memory(tokens=30)
    assert allowed is False
    assert cur_rpm == 3
    assert cur_tpm == 90
    assert wait_sec > 0.0


@pytest.mark.asyncio
async def test_80_percent_quota_warning_logging():
    """Verify warning log emitted when RPM or TPM utilization reaches >= 80%."""
    limiter = SharedModelRateLimiter(
        model_name="test-warn-model",
        max_rpm=10,
        max_tpm=1000,
        min_interval=0.0,
    )
    limiter._redis_available = False

    # Seed 8 entries (80% utilization)
    now = time.monotonic()
    limiter._local_history = [(now, 50, f"m_{i}") for i in range(8)]

    with patch("app.ai.rate_limiter.logger.warning") as mock_warn:
        await limiter.acquire(estimated_tokens=50)
        # Should have triggered 80% warning
        assert mock_warn.called
        log_call = mock_warn.call_args
        assert log_call[0][0] == "gemini_rate_limit_approaching_quota"
        assert log_call[1]["threshold"] == "80%"


@pytest.mark.asyncio
async def test_user_quota_limiter():
    """Verify UserQuotaLimiter raises UserQuotaExceededError when monthly limit is reached."""
    limiter = UserQuotaLimiter(monthly_clause_quota=10)
    # Patch redis to force in-memory check (use IP to avoid Windows DNS resolution delay)
    limiter._redis_url = "redis://127.0.0.1:9999/0"

    # Within quota
    await limiter.check_and_increment(user_id="user_123", clause_count=8)

    # Exceeding quota
    with pytest.raises(UserQuotaExceededError) as exc_info:
        await limiter.check_and_increment(user_id="user_123", clause_count=5)
    assert "monthly quota exceeded" in str(exc_info.value)


def test_jittered_backoff_calculation():
    """Verify calculate_jittered_backoff honors server retry_after and applies jitter."""
    # When server specifies retry_after = 12.0s
    wait_1 = calculate_jittered_backoff(attempt=1, retry_after=12.0)
    assert wait_1 >= 12.0
    assert wait_1 <= 13.0

    # When no server delay is specified, exponential backoff with jitter
    wait_2 = calculate_jittered_backoff(attempt=2, retry_after=None, min_wait=2.0)
    # 2.0 * (2 ** 2) = 8.0 + jitter
    assert wait_2 >= 8.0
