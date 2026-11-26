"""
Server-Sent Events (SSE) Broadcaster for Live Document Processing Telemetry.

Supports both in-process asyncio queues and cross-process Redis Pub/Sub bridging
(`sse:doc:{document_id}`) so a dedicated ARQ worker publishes live events that
stream immediately through the FastAPI SSE endpoint.
"""

import asyncio
import json
import os
import threading
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_PROCESS_ID = os.getpid()


class SSEBroadcaster:
    """
    Hybrid in-memory + Redis Pub/Sub broadcaster for SSE streams.
    Thread-safe and asyncio-safe across worker and API processes.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = threading.Lock()
        self._redis_tasks: set[asyncio.Task[Any]] = set()

    @staticmethod
    async def _publish_to_redis(doc_key: str, payload: dict[str, Any]) -> None:
        """Forward event to Redis Pub/Sub channel so other OS processes receive it."""
        try:
            from redis import asyncio as aioredis

            settings = get_settings()
            client = aioredis.from_url(
                settings.redis_url,
                socket_connect_timeout=0.5,
                socket_timeout=0.5,
            )
            try:
                msg = json.dumps({**payload, "_pid": _PROCESS_ID})
                await client.publish(f"sse:doc:{doc_key}", msg)
            finally:
                await client.aclose()
        except Exception:
            pass

    def publish(self, document_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event locally and broadcast over Redis Pub/Sub."""
        doc_key = str(document_id)
        payload = {
            "event": event_type,
            "document_id": doc_key,
            "timestamp": datetime.now(UTC).isoformat(),
            **data,
        }

        with self._lock:
            queues = list(self._subscribers.get(doc_key, set()))

        for q in queues:
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                pass

        try:
            loop = asyncio.get_running_loop()
            task = loop.create_task(self._publish_to_redis(doc_key, payload))
            self._redis_tasks.add(task)
            task.add_done_callback(self._redis_tasks.discard)
        except RuntimeError:
            pass

        logger.debug(
            "sse_event_published",
            document_id=doc_key,
            sse_event=event_type,
            subscriber_count=len(queues),
        )

    async def subscribe(
        self, document_id: str, timeout_seconds: float = 300.0
    ) -> AsyncGenerator[str, None]:
        """
        Subscribe to events for a specific document and yield SSE-formatted strings.
        Listens to both in-process queues and Redis Pub/Sub (deduping own PID).
        """
        doc_key = str(document_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)

        with self._lock:
            if doc_key not in self._subscribers:
                self._subscribers[doc_key] = set()
            self._subscribers[doc_key].add(queue)

        stop_redis = asyncio.Event()
        redis_listener_task: asyncio.Task[None] | None = None

        async def _listen_redis() -> None:
            try:
                from redis import asyncio as aioredis

                settings = get_settings()
                client = aioredis.from_url(
                    settings.redis_url,
                    socket_connect_timeout=1.0,
                    socket_timeout=2.0,
                )
                pubsub = client.pubsub()
                await pubsub.subscribe(f"sse:doc:{doc_key}")
                try:
                    while not stop_redis.is_set():
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=0.5
                        )
                        if message and message.get("type") == "message":
                            raw = message.get("data")
                            if isinstance(raw, bytes):
                                raw = raw.decode("utf-8", errors="ignore")
                            if isinstance(raw, str):
                                parsed = json.loads(raw)
                                if parsed.get("_pid") != _PROCESS_ID:
                                    parsed.pop("_pid", None)
                                    try:
                                        queue.put_nowait(parsed)
                                    except asyncio.QueueFull:
                                        pass
                        else:
                            await asyncio.sleep(0.05)
                finally:
                    try:
                        await pubsub.unsubscribe(f"sse:doc:{doc_key}")
                        await pubsub.close()
                    except Exception:
                        pass
                    await client.aclose()
            except Exception:
                pass

        try:
            redis_listener_task = asyncio.create_task(_listen_redis())

            # Send initial connected heartbeat
            initial_data = json.dumps(
                {
                    "event": "connected",
                    "document_id": doc_key,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            yield f"event: connected\ndata: {initial_data}\n\n"

            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=timeout_seconds)
                    event_name = payload.get("event", "message")
                    data_str = json.dumps(payload)
                    yield f"event: {event_name}\ndata: {data_str}\n\n"

                    if event_name in ("completed", "failed", "cancelled"):
                        break
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep connection alive
                    yield ": ping\n\n"

        finally:
            stop_redis.set()
            if redis_listener_task is not None:
                redis_listener_task.cancel()
                try:
                    await redis_listener_task
                except (asyncio.CancelledError, Exception):
                    pass
            with self._lock:
                if doc_key in self._subscribers:
                    self._subscribers[doc_key].discard(queue)
                    if not self._subscribers[doc_key]:
                        del self._subscribers[doc_key]


# Global singleton
_broadcaster: SSEBroadcaster | None = None
_broadcaster_lock = threading.Lock()


def get_sse_broadcaster() -> SSEBroadcaster:
    """Retrieve global SSEBroadcaster singleton."""
    global _broadcaster
    if _broadcaster is None:
        with _broadcaster_lock:
            if _broadcaster is None:
                _broadcaster = SSEBroadcaster()
    return _broadcaster


def broadcast_event(document_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Helper to publish an SSE event."""
    get_sse_broadcaster().publish(document_id, event_type, data)
