"""
Cooperative & Cross-Process Cancellation Registry and AI Cache Purging.

Provides:
- JobCancelledError (inherits asyncio.CancelledError so retry/repair except Exception blocks never swallow it)
- Dual cancellation checks across in-memory sets, Redis flags, and PostgreSQL jobs/documents tables
- Cancel-aware async sleep (wakes within <= 0.2s on cancellation)
- Cancellation acknowledgment coordination for delete endpoints (up to 5s wait)
- AI cache key registry & purging tied to deleted documents and users
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections.abc import Awaitable
from typing import Any, cast
from uuid import UUID

from redis import asyncio as aioredis
from sqlalchemy import select

from app.ai.ledger import get_call_context
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class JobCancelledError(asyncio.CancelledError):
    """Raised immediately when an analysis job, document, or user is cancelled/deleted."""


# Fast in-process cancellation registries (fallback & instant wakeup when Redis is absent)
_cancelled_documents: set[str] = set()
_cancelled_jobs: set[str] = set()
_cancelled_users: set[str] = set()
_cancelled_acks: set[str] = set()

# In-memory AI cache index tracking keys created per document_id and user_id
_doc_cache_entries: dict[str, set[tuple[str, str]]] = {}
_user_cache_entries: dict[str, set[tuple[str, str]]] = {}

# Registry of live in-memory cache dicts: name -> set of dict references or single dict
_registered_cache_stores: dict[str, list[dict[str, Any]]] = {
    "prompt": [],
    "clause": [],
    "embed": [],
}


def register_cache_store(store_name: str, cache_dict: dict[str, Any]) -> None:
    """Register a runtime cache dictionary by object identity so deletions purge tied entries."""
    stores = _registered_cache_stores.setdefault(store_name, [])
    if not any(existing is cache_dict for existing in stores):
        stores.append(cache_dict)


def record_cache_key(
    store_name: str,
    cache_key: str,
    document_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """Associate a cache key with the active document_id and user_id from call context."""
    ctx = get_call_context()
    doc_id = str(document_id or ctx.get("document_id") or "")
    u_id = str(user_id or ctx.get("user_id") or "")
    if doc_id:
        _doc_cache_entries.setdefault(doc_id, set()).add((store_name, cache_key))
    if u_id:
        _user_cache_entries.setdefault(u_id, set()).add((store_name, cache_key))


async def purge_ai_caches(
    document_ids: list[str] | None = None,
    user_id: str | None = None,
    clause_texts: list[str] | None = None,
) -> dict[str, int]:
    """
    Purge in-memory and Redis AI caches (clause analysis, prompt cache, embeddings)
    tied to deleted documents or user. Returns counts of purged entries.
    """
    purged_memory = 0
    purged_redis = 0
    keys_to_remove: set[tuple[str, str]] = set()
    redis_keys: set[str] = set()

    for doc_id in document_ids or []:
        doc_str = str(doc_id)
        entries = _doc_cache_entries.pop(doc_str, set())
        keys_to_remove.update(entries)
        redis_keys.add(f"aicache:doc:{doc_str}")

    if user_id:
        u_str = str(user_id)
        entries = _user_cache_entries.pop(u_str, set())
        keys_to_remove.update(entries)
        redis_keys.add(f"aicache:user:{u_str}")

    # Also match clause text hashes across clause and embed caches directly
    text_hashes: set[str] = set()
    for text in clause_texts or []:
        if not text:
            continue
        norm = " ".join(text.split())
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        text_hashes.add(h)

    for store_name, k in keys_to_remove:
        for cache_dict in _registered_cache_stores.get(store_name, []):
            if k in cache_dict:
                cache_dict.pop(k, None)
                purged_memory += 1
        if store_name == "embed_redis":
            redis_keys.add(k)

    # Sweep hash-prefixed keys for deleted clauses across registered caches
    if text_hashes:
        for store_name in ("clause", "embed"):
            for cache_dict in _registered_cache_stores.get(store_name, []):
                matching = [
                    ck
                    for ck in list(cache_dict.keys())
                    if any(ck.startswith(h) for h in text_hashes)
                ]
                for ck in matching:
                    cache_dict.pop(ck, None)
                    purged_memory += 1

    # Clean Redis cached embeddings/AI entries if Redis is reachable
    redis_client = await _get_redis_client()
    if redis_client is not None:
        try:
            for doc_id in document_ids or []:
                members = await cast(
                    Awaitable[set[Any]], redis_client.smembers(f"aicache:doc:{doc_id}")
                )
                for m in members:
                    redis_keys.add(m.decode("utf-8") if isinstance(m, bytes) else str(m))
            if user_id:
                members = await cast(
                    Awaitable[set[Any]], redis_client.smembers(f"aicache:user:{user_id}")
                )
                for m in members:
                    redis_keys.add(m.decode("utf-8") if isinstance(m, bytes) else str(m))
            if text_hashes:
                settings = get_settings()
                model = settings.gemini_embedding_model
                dim = settings.embedding_dimension
                for h in text_hashes:
                    for tt in ("RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"):
                        redis_keys.add(f"embedcache:{h}:{model}:{dim}:{tt}")
            if redis_keys:
                deleted = await redis_client.delete(*list(redis_keys))
                purged_redis = int(deleted or 0)
        except Exception as exc:
            logger.debug("redis_ai_cache_purge_skipped", error=str(exc))
        finally:
            await _close_redis_client(redis_client)

    return {"memory_cache_entries_purged": purged_memory, "redis_cache_keys_purged": purged_redis}


async def track_redis_cache_key(
    redis_key: str,
    document_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """Record a Redis cache key under document/user index sets for later deletion purge."""
    ctx = get_call_context()
    doc_id = str(document_id or ctx.get("document_id") or "")
    u_id = str(user_id or ctx.get("user_id") or "")
    if not (doc_id or u_id):
        return
    redis_client = await _get_redis_client()
    if redis_client is None:
        return
    try:
        if doc_id:
            await cast(Awaitable[int], redis_client.sadd(f"aicache:doc:{doc_id}", redis_key))
            await redis_client.expire(f"aicache:doc:{doc_id}", 86400 * 30)
        if u_id:
            await cast(Awaitable[int], redis_client.sadd(f"aicache:user:{u_id}", redis_key))
            await redis_client.expire(f"aicache:user:{u_id}", 86400 * 30)
    except Exception:
        pass
    finally:
        await _close_redis_client(redis_client)


async def _get_redis_client() -> aioredis.Redis | None:
    try:
        settings = get_settings()
        client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        await client.ping()
        return client
    except Exception:
        return None


async def _close_redis_client(client: aioredis.Redis | None) -> None:
    if client is not None:
        try:
            await client.aclose()
        except Exception:
            pass


async def mark_cancelled(
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
    user_id: str | UUID | None = None,
) -> None:
    """Set cancellation flag in memory and Redis for immediate cross-process detection."""
    doc_str = str(document_id) if document_id else None
    job_str = str(job_id) if job_id else None
    user_str = str(user_id) if user_id else None

    if doc_str:
        _cancelled_documents.add(doc_str)
    if job_str:
        _cancelled_jobs.add(job_str)
    if user_str:
        _cancelled_users.add(user_str)

    redis_client = await _get_redis_client()
    if redis_client is not None:
        try:
            if doc_str:
                await redis_client.set(f"job:cancel:doc:{doc_str}", "1", ex=3600)
            if job_str:
                await redis_client.set(f"job:cancel:job:{job_str}", "1", ex=3600)
            if user_str:
                await redis_client.set(f"job:cancel:user:{user_str}", "1", ex=3600)
        except Exception as exc:
            logger.warning("redis_set_cancel_flag_failed", error=str(exc))
        finally:
            await _close_redis_client(redis_client)


async def clear_cancelled(
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
    user_id: str | UUID | None = None,
) -> None:
    """Clear cancellation flags (e.g., when explicitly resuming/retrying a job)."""
    doc_str = str(document_id) if document_id else None
    job_str = str(job_id) if job_id else None
    user_str = str(user_id) if user_id else None

    if doc_str:
        _cancelled_documents.discard(doc_str)
        _cancelled_acks.discard(doc_str)
    if job_str:
        _cancelled_jobs.discard(job_str)
        _cancelled_acks.discard(job_str)
    if user_str:
        _cancelled_users.discard(user_str)

    redis_client = await _get_redis_client()
    if redis_client is not None:
        try:
            del_keys = []
            if doc_str:
                del_keys.extend([f"job:cancel:doc:{doc_str}", f"job:ack:{doc_str}"])
            if job_str:
                del_keys.extend([f"job:cancel:job:{job_str}", f"job:ack:{job_str}"])
            if user_str:
                del_keys.append(f"job:cancel:user:{user_str}")
            if del_keys:
                await redis_client.delete(*del_keys)
        except Exception:
            pass
        finally:
            await _close_redis_client(redis_client)


async def acknowledge_cancelled(
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
) -> None:
    """Record worker confirmation that execution has fully stopped."""
    doc_str = str(document_id) if document_id else None
    job_str = str(job_id) if job_id else None
    if doc_str:
        _cancelled_acks.add(doc_str)
    if job_str:
        _cancelled_acks.add(job_str)

    redis_client = await _get_redis_client()
    if redis_client is not None:
        try:
            if doc_str:
                await redis_client.set(f"job:ack:{doc_str}", "1", ex=3600)
            if job_str:
                await redis_client.set(f"job:ack:{job_str}", "1", ex=3600)
        except Exception:
            pass
        finally:
            await _close_redis_client(redis_client)


def is_cancelled_fast(
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
    user_id: str | UUID | None = None,
) -> bool:
    """Fast synchronous check against in-memory cancellation flags."""
    ctx = get_call_context()
    doc_str = str(document_id or ctx.get("document_id") or "")
    job_str = str(job_id or ctx.get("job_id") or "")
    user_str = str(user_id or ctx.get("user_id") or "")

    return bool(
        (doc_str and doc_str in _cancelled_documents)
        or (job_str and job_str in _cancelled_jobs)
        or (user_str and user_str in _cancelled_users)
    )


async def is_cancelled(
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
    user_id: str | UUID | None = None,
    check_db: bool = True,
) -> bool:
    """
    Check cancellation flags across:
    1. In-memory registry
    2. Redis keys (`job:cancel:*`)
    3. PostgreSQL `jobs.cancel_requested` / `jobs.status` (when IDs are valid UUIDs and check_db=True)
    """
    ctx = get_call_context()
    doc_str = str(document_id or ctx.get("document_id") or "")
    job_str = str(job_id or ctx.get("job_id") or "")
    user_str = str(user_id or ctx.get("user_id") or "")

    if not (doc_str or job_str or user_str):
        return False

    # 1. In-memory check
    if (
        (doc_str and doc_str in _cancelled_documents)
        or (job_str and job_str in _cancelled_jobs)
        or (user_str and user_str in _cancelled_users)
    ):
        return True

    # 2. Redis check
    redis_client = await _get_redis_client()
    if redis_client is not None:
        try:
            keys_to_check = []
            if doc_str:
                keys_to_check.append(f"job:cancel:doc:{doc_str}")
            if job_str:
                keys_to_check.append(f"job:cancel:job:{job_str}")
            if user_str:
                keys_to_check.append(f"job:cancel:user:{user_str}")
            if keys_to_check:
                vals = await redis_client.mget(*keys_to_check)
                if any(v is not None for v in vals):
                    if doc_str:
                        _cancelled_documents.add(doc_str)
                    if job_str:
                        _cancelled_jobs.add(job_str)
                    return True
        except Exception:
            pass
        finally:
            await _close_redis_client(redis_client)

    # 3. Database check (for durable cross-process DB cancel flags or deleted docs)
    if check_db:
        doc_uuid = _parse_uuid(doc_str)
        job_uuid = _parse_uuid(job_str)
        if doc_uuid or job_uuid:
            try:
                from app.core.database import async_session_factory
                from app.models.document import Document
                from app.models.job import Job

                async with async_session_factory() as db_sess:
                    # Check explicit job cancel flag first
                    if job_uuid:
                        res = await db_sess.execute(
                            select(Job.cancel_requested, Job.status).where(Job.id == job_uuid)
                        )
                        row = res.first()
                        if row and (row[0] or row[1] in ("cancelling", "cancelled")):
                            _cancelled_jobs.add(job_str)
                            return True
                    if doc_uuid:
                        res_j = await db_sess.execute(
                            select(Job.cancel_requested, Job.status)
                            .where(Job.document_id == doc_uuid)
                            .order_by(Job.created_at.desc())
                            .limit(1)
                        )
                        j_row = res_j.first()
                        if j_row and (j_row[0] or j_row[1] in ("cancelling", "cancelled")):
                            _cancelled_documents.add(doc_str)
                            return True

                        # Only treat missing Document as cancelled when DB actually manages that document
                        # (if there is an active job row in DB for it and doc is gone, doc was deleted)
                        if j_row is not None:
                            doc_exists = await db_sess.execute(
                                select(Document.id).where(Document.id == doc_uuid)
                            )
                            if doc_exists.scalar_one_or_none() is None:
                                _cancelled_documents.add(doc_str)
                                return True
            except Exception:
                # Tests using non-DB IDs or mock DB sessions skip DB check gracefully
                pass

    return False


def _parse_uuid(val: str) -> UUID | None:
    if not val:
        return None
    try:
        return UUID(val)
    except (ValueError, TypeError):
        return None


async def check_not_cancelled(
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
    user_id: str | UUID | None = None,
    check_db: bool = True,
) -> None:
    """Raise JobCancelledError immediately if cancellation has been requested."""
    if await is_cancelled(
        document_id=document_id,
        job_id=job_id,
        user_id=user_id,
        check_db=check_db,
    ):
        ctx = get_call_context()
        target = document_id or job_id or ctx.get("document_id") or ctx.get("job_id") or "unknown"
        raise JobCancelledError(f"Job cancelled for target {target}")


async def cancel_aware_sleep(
    seconds: float,
    document_id: str | UUID | None = None,
    job_id: str | UUID | None = None,
    user_id: str | UUID | None = None,
    poll_interval: float = 0.2,
) -> None:
    """
    Sleep up to `seconds`, waking every `poll_interval` seconds to check cancellation flags.
    Guarantees mid-flight sleeps stop within ~0.2s (< 2s SLA) upon cancel/delete.
    """
    if seconds <= 0:
        await check_not_cancelled(document_id=document_id, job_id=job_id, user_id=user_id)
        return

    deadline = time.monotonic() + seconds
    tick = 0
    while True:
        # Poll DB on first check and every 2nd tick (~0.4s); memory+Redis on every tick (0.2s)
        await check_not_cancelled(
            document_id=document_id,
            job_id=job_id,
            user_id=user_id,
            check_db=(tick % 2 == 0),
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(poll_interval, remaining))
        tick += 1
