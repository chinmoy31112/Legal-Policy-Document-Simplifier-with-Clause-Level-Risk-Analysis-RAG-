"""
Latency-Simulating Fake LLM and Embedder for Concurrency, Timing, and Reliability Tests.

Adheres to:
- Sleeps 10-14 s per call (configurable) to accurately simulate real Gemini API latency.
- Obeys the exact same SharedModelRateLimiter (RPM, TPM, RPD) as the real model.
- Can inject 429 (per-minute and per-day), 503 (high demand), and invalid JSON errors.
- Records every outbound call, attempt, retry, and repair into the Call Ledger.
- Produces valid, schema-compliant Pydantic models via deterministic reasoning.
"""

import asyncio
import json
import random
import time
from typing import Any, TypeVar

from pydantic import BaseModel

from app.ai.embedding import GeminiEmbedder
from app.ai.interfaces import Embedder, LLMClient
from app.ai.ledger import CallLedger, get_call_ledger
from app.ai.llm import GeminiLLMClient
from app.ai.rate_limiter import (
    DailyQuotaExceededError,
    SharedModelRateLimiter,
    get_model_rate_limiter,
)
from app.core.exceptions import AIServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class LatencySimulatingFakeLLM(LLMClient):
    """
    Fake LLM that simulates real API latency (default 10-14s),
    obeys model rate limits, records every attempt in the Call Ledger,
    and supports dynamic injection of 429, 503, and invalid JSON failures.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.5-flash-lite",
        sleep_range: tuple[float, float] = (10.0, 14.0),
        rate_limiter: SharedModelRateLimiter | None = None,
        inject_429_minute: int = 0,
        inject_429_day: bool = False,
        inject_503: int = 0,
        inject_invalid_json: int = 0,
    ):
        self._model_name = model_name
        self.sleep_range = sleep_range
        self._rate_limiter = rate_limiter or get_model_rate_limiter(model_name)
        self.inject_429_minute = inject_429_minute
        self.inject_429_day = inject_429_day
        self.inject_503 = inject_503
        self.inject_invalid_json = inject_invalid_json
        self.ledger: CallLedger = get_call_ledger()
        self.last_call_metrics: dict[str, Any] = {}
        self._offline_generator = GeminiLLMClient(model_name=model_name, force_offline=True)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def _prompt_cache(self) -> dict[str, Any]:
        return self._offline_generator._prompt_cache

    def set_injections(
        self,
        inject_429_minute: int = 0,
        inject_429_day: bool = False,
        inject_503: int = 0,
        inject_invalid_json: int = 0,
    ) -> None:
        """Dynamically update injection counts."""
        self.inject_429_minute = inject_429_minute
        self.inject_429_day = inject_429_day
        self.inject_503 = inject_503
        self.inject_invalid_json = inject_invalid_json

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_instruction: str | None = None,
    ) -> T:
        """
        Execute structured generation with latency simulation, rate limiter pacing,
        error injection, and Call Ledger logging.
        """
        from app.core.cancellation import cancel_aware_sleep, check_not_cancelled, is_cancelled

        await check_not_cancelled()
        est_tokens = max(10, len(prompt.split()) * 2 + 100)
        t_start = time.perf_counter()

        # 1. Obey rate limiter (RPM, TPM, RPD)
        slot_id = await self._rate_limiter.acquire(estimated_tokens=est_tokens)

        # 2. Simulate realistic network and inference latency (cancel-aware 0.2s poll)
        sleep_duration = random.uniform(self.sleep_range[0], self.sleep_range[1])
        try:
            if sleep_duration > 0:
                await cancel_aware_sleep(sleep_duration)
            if await is_cancelled():
                await self._rate_limiter.release_slot(member_id=slot_id, refund_rpd=True)
                await check_not_cancelled()
        except asyncio.CancelledError:
            await self._rate_limiter.release_slot(member_id=slot_id, refund_rpd=True)
            raise
        elapsed = time.perf_counter() - t_start

        # 3. Optional test-mode Redis injection trigger (APP_ENV=test only, for Playwright/worker E2E tests)
        from app.core.config import get_settings

        if get_settings().app_env == "test" and not self.inject_429_day:
            try:
                from redis import asyncio as aioredis

                from app.ai.ledger import get_call_context

                ctx = get_call_context()
                doc_id_ctx = str(ctx.get("document_id") or "")
                purpose_ctx = str(ctx.get("purpose") or "")
                r_client = aioredis.from_url(
                    get_settings().redis_url,
                    decode_responses=True,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                )
                try:
                    flag_val = None
                    if doc_id_ctx:
                        flag_val = await r_client.get(f"test:inject_daily_quota:{doc_id_ctx}")
                    if flag_val is None:
                        flag_val = await r_client.get("test:inject_daily_quota")
                    if flag_val == "always" or (flag_val == "analyze" and purpose_ctx == "analyze"):
                        self.inject_429_day = True
                finally:
                    await r_client.aclose()
            except Exception:
                pass

        # 3b. Injected failure: 429 Daily Quota Exhaustion
        if self.inject_429_day:
            self.ledger.record_call(
                status="429 day",
                latency=elapsed,
                tokens=est_tokens,
                model_name=self._model_name,
            )
            self._rate_limiter.mark_daily_quota_exhausted(
                notice="Injected daily quota limit exceeded"
            )
            raise DailyQuotaExceededError(
                model_name=self._model_name,
                current_rpd=self._rate_limiter.max_rpd,
                max_rpd=self._rate_limiter.max_rpd,
                seconds_until_reset=self._rate_limiter._seconds_until_midnight_utc(),
                notice="Daily API quota reached. Job paused.",
            )

        # 4. Injected failure: 429 Per-Minute Rate Limit
        if self.inject_429_minute > 0:
            self.inject_429_minute -= 1
            self.ledger.record_call(
                status="429 minute",
                latency=elapsed,
                tokens=est_tokens,
                model_name=self._model_name,
            )
            await self._rate_limiter.circuit_breaker.record_failure(retry_after=2.0)
            raise AIServiceError("429 RESOURCE_EXHAUSTED: Rate limit exceeded. Retry in 2.0s")

        # 5. Injected failure: 503 Service Unavailable
        if self.inject_503 > 0:
            self.inject_503 -= 1
            self.ledger.record_call(
                status="503",
                latency=elapsed,
                tokens=est_tokens,
                model_name=self._model_name,
            )
            await self._rate_limiter.circuit_breaker.record_failure(retry_after=1.0)
            raise AIServiceError(
                "503 Service Unavailable: The model is overloaded. Please try again later."
            )

        # 6. Injected failure: Invalid JSON / Schema Violation (tests repair flow)
        if self.inject_invalid_json > 0:
            self.inject_invalid_json -= 1
            self.ledger.record_call(
                status="invalid JSON",
                latency=elapsed,
                tokens=est_tokens,
                model_name=self._model_name,
            )
            raise json.JSONDecodeError("Injected malformed JSON from LLM", "{invalid_json: ...", 0)

        # 7. Success: produce deterministic validated reasoning output
        result = self._offline_generator._generate_offline_reasoning(
            prompt, response_model, record_ledger=False
        )
        await self._rate_limiter.circuit_breaker.record_success()
        self._rate_limiter.record_success()

        # Record successful outbound call in the ledger
        self.ledger.record_call(
            status="ok",
            latency=elapsed,
            tokens=est_tokens,
            model_name=self._model_name,
        )

        self.last_call_metrics = {
            "latency": round(elapsed, 3),
            "input_tokens": est_tokens,
            "output_tokens": 120,
            "retries": 0,
            "repair_count": 0,
            "rate_limiter_wait": 0.0,
        }
        return result

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
    ) -> str:
        """Simulate freeform text generation with latency."""
        from app.core.cancellation import cancel_aware_sleep, check_not_cancelled, is_cancelled

        await check_not_cancelled()
        est_tokens = max(10, len(prompt.split()) + 50)
        t_start = time.perf_counter()
        slot_id = await self._rate_limiter.acquire(estimated_tokens=est_tokens)

        sleep_duration = random.uniform(self.sleep_range[0], self.sleep_range[1])
        try:
            if sleep_duration > 0:
                await cancel_aware_sleep(sleep_duration)
            if await is_cancelled():
                await self._rate_limiter.release_slot(member_id=slot_id, refund_rpd=True)
                await check_not_cancelled()
        except asyncio.CancelledError:
            await self._rate_limiter.release_slot(member_id=slot_id, refund_rpd=True)
            raise
        elapsed = time.perf_counter() - t_start

        if self.inject_429_day:
            self.ledger.record_call(
                status="429 day", latency=elapsed, tokens=est_tokens, model_name=self._model_name
            )
            raise DailyQuotaExceededError(model_name=self._model_name)

        if self.inject_429_minute > 0:
            self.inject_429_minute -= 1
            self.ledger.record_call(
                status="429 minute", latency=elapsed, tokens=est_tokens, model_name=self._model_name
            )
            raise AIServiceError("429 RESOURCE_EXHAUSTED")

        if self.inject_503 > 0:
            self.inject_503 -= 1
            self.ledger.record_call(
                status="503", latency=elapsed, tokens=est_tokens, model_name=self._model_name
            )
            raise AIServiceError("503 Service Unavailable")

        self.ledger.record_call(
            status="ok", latency=elapsed, tokens=est_tokens, model_name=self._model_name
        )
        return "Simulated text analysis response."


class LatencySimulatingFakeEmbedder(Embedder):
    """
    Fake Embedder that obeys model rate limits, logs to Call Ledger,
    and returns deterministic category-anchored embeddings.
    """

    def __init__(
        self,
        model_name: str = "gemini-embedding-2",
        dimension: int = 768,
        sleep_range: tuple[float, float] = (0.5, 1.0),
    ):
        self._model_name = model_name
        self._dimension = dimension
        self.sleep_range = sleep_range
        self._rate_limiter = get_model_rate_limiter(model_name)
        self.ledger: CallLedger = get_call_ledger()
        self._offline_embedder = GeminiEmbedder(model_name=model_name, force_offline=True)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_texts(
        self, texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
    ) -> list[list[float]]:
        from app.core.cancellation import cancel_aware_sleep, check_not_cancelled, is_cancelled

        if not texts:
            return []
        await check_not_cancelled()
        est_tokens = max(1, sum(len(t.split()) for t in texts) * 2)
        t_start = time.perf_counter()

        slot_id = await self._rate_limiter.acquire(estimated_tokens=est_tokens)
        sleep_sec = random.uniform(self.sleep_range[0], self.sleep_range[1])
        try:
            if sleep_sec > 0:
                await cancel_aware_sleep(sleep_sec)
            if await is_cancelled():
                await self._rate_limiter.release_slot(member_id=slot_id, refund_rpd=True)
                await check_not_cancelled()
        except asyncio.CancelledError:
            await self._rate_limiter.release_slot(member_id=slot_id, refund_rpd=True)
            raise
        elapsed = time.perf_counter() - t_start

        self.ledger.record_call(
            purpose="embed",
            status="ok",
            latency=elapsed,
            tokens=est_tokens,
            model_name=self._model_name,
        )
        return [self._offline_embedder._generate_offline_embedding(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self.embed_texts([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]
