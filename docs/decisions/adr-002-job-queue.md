# ADR 002: Asynchronous Job Queue Selection (ARQ + Redis vs. Celery vs. FastAPI BackgroundTasks)

## Status
Accepted

## Context
PDF processing, clause segmentation, Google GenAI embedding batches, and Gemini reasoning pipelines take between 5 to 60 seconds per document. Synchronous HTTP request-response cycles would exceed browser timeouts, degrade user experience, and risk HTTP connection drops. We need an asynchronous background job processing architecture.

We evaluated three options:
1. **ARQ + Redis**: Lightweight, native `asyncio` job queue designed for modern asynchronous Python.
2. **Celery + Redis/RabbitMQ**: Established distributed task queue with extensive multi-broker features.
3. **FastAPI BackgroundTasks**: Built-in starlette background tasks executing inside the web server process.

## Trade-offs in Three Lines
1. **ARQ + Redis** runs natively on Python's `asyncio` event loop with minimal memory overhead, zero multiprocessing serialization impedance, and native non-blocking Redis streams.
2. **Celery** is mature with robust enterprise monitoring tooling (Flower) but relies heavily on synchronous OS fork workers, complex task serialization, and substantial dependency bloat.
3. **FastAPI BackgroundTasks** requires zero extra infrastructure but shares memory with the web API; heavy PyMuPDF memory spikes or CPU parsing could crash the web API worker without job retry capabilities.

## Decision
We select **ARQ + Redis**.

The backend will expose an asynchronous job dispatch interface:
- API endpoint `POST /api/v1/documents/upload` stores the file, creates a `PENDING` processing job, and returns HTTP 202 with `job_id`.
- The ARQ worker picks up the job from Redis, runs PyMuPDF extraction, clause segmentation, vector queries, and Gemini analysis, updating progress milestones (`PARSING`, `EMBEDDING`, `ANALYZING`, `COMPLETED`, `FAILED`) in the database.
- Frontend queries job status via `GET /api/v1/jobs/{job_id}` (or WebSocket progress events).

## Consequences
- Clean operational boundary: Web API process remains responsive and lightweight.
- Jobs survive HTTP disconnects; failing API calls to Gemini can be safely retried with exponential backoff inside the worker.
- Requires Redis service running in `docker-compose.yml`.
