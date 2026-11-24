# ADR 004: Google Gemini Model Verification & Selection

## Status
Accepted (Updated for Free-Tier Limits & Models as Config)

## Context
Per Rule 7 ("Models are configuration, not code") and Rule 8 ("One embedding model"):
The system decouples model choice from code logic via environment configuration:
- Clause Analysis Model: `GEMINI_CLAUSE_MODEL` (default: `gemini-3.5-flash-lite`, swappable to `gemini-3.8-flash`).
- Document Summary Model: `GEMINI_SUMMARY_MODEL` (default: `gemini-3.5-flash-lite`).
- Optional Escalation Model: `GEMINI_ESCALATION_MODEL` (disabled by default via `GEMINI_ENABLE_ESCALATION=false`).
- Embedding Model: `GEMINI_EMBEDDING_MODEL` (default: `gemini-embedding-2`).

All models and their free-tier limits have been verified against Google GenAI API endpoints and documentation.

## Free-Tier Limits & Enforced Throttles

| Model | Free-Tier Limits | Configured Throttled Limits | Daily Budget (RPD) |
| :--- | :--- | :--- | :--- |
| **`gemini-3.5-flash-lite`** | 15 RPM, ~250k TPM, 500 RPD | **12 RPM, 250k TPM** | **400 RPD** |
| **`gemini-3.8-flash`** | 5 RPM, ~250k TPM, 20 RPD | **4 RPM, 250k TPM** | **16 RPD** |
| **`gemini-embedding-2`** | 100 RPM, 80k TPM, 1000 RPD | **80 RPM, 80k TPM** | **1,000 RPD** |

## Shared Rate Limiter & Budget Exhaustion Guardrail
1. **Shared Rate Limiter:** A Redis-backed token bucket (`SharedModelRateLimiter`) throttles RPM and TPM, and enforces daily budgets (RPD) with atomic counters.
2. **Quota Exhaustion:** When a daily budget is exhausted, a `DailyQuotaExceededError` is raised. Analysis jobs transition to `"waiting for quota"` status with a human-readable countdown in `metadata_["quota_notice"]` rather than failing. Jobs resume automatically once the quota counter resets.
3. **Batching:** Clause analysis supports batching (default batch size 4 for Flash-Lite, 5 for Flash) with individual schema and grounding validation. Failed or ungrounded clauses are re-sent individually without discarding successful batch items.
4. **Cache Invalidation:** Pipeline analysis results are cached using the composite key: `{model_name}:{prompt_version}:{clause_hash}`. Switching models or prompt versions cleanly triggers fresh evaluation without stale cache pollution.
