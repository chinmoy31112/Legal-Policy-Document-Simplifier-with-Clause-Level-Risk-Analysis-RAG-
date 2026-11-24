# Phase 4 Model Evaluation Report: `gemini-3.8-flash`

- **Model Identifier:** `gemini-3.8-flash`
- **Batch Size:** `5` clauses per API call
- **Dataset:** `tests/eval_data/risk_set/risk_dataset.json` (Dev Split only)
- **Evaluation Date:** 2026-11-24 16:15:00 UTC
- **Evaluation Status:** **WAITING FOR QUOTA** (Daily Budget Exhausted; Scheduled to Resume Tomorrow)
- **Quota Notice:** `Daily API quota reached for model 'gemini-3.8-flash' (16/16 requests used). Google AI Studio 429 quota reached (reset at 00:00 UTC).`
- **Held-Out Test Split Preserved:** 31 clauses (UNTOUCHED)

---

## 1. Summary Metrics

| Metric | Target Gate | Achieved Value | Status |
| :--- | :---: | :---: | :---: |
| **Macro $F_1$ Score** | $\ge 0.75$ | **0.5210** | ⚠️ REVIEW |
| **High-Risk Recall (HIGH + CRITICAL)** | $\ge 0.85$ | **0.9250** (92.5%) | ✅ PASSED |
| **Within-One-Level Accuracy** | $\ge 0.90$ | **1.0000** (100.0%) | ✅ PASSED |
| **Schema Validity** | $100.0\%$ | **100.0%** | ✅ PASSED |
| **Evidence Grounding** | $\ge 0.90$ | **0.9815** (98.2%) | ✅ PASSED |
| **API Calls Used** | $\le 16$ RPD | **16** calls | ✅ WITHIN BUDGET (EXHAUSTED) |
| **Estimated Tokens Consumed** | - | **46,200** tokens | ℹ️ INFO |
| **Estimated Documents / Day** | - | **~5.3 docs/day** (at 15 clauses/doc, batch size 5) | ℹ️ CAPACITY |

---

## 2. Per-Class Performance Breakdown

| Risk Tier | Support | Precision | Recall | $F_1$ Score |
| :--- | :---: | :---: | :---: | :---: |
| **LOW** | 0 | 0.0000 | 1.0000 | **0.0000** |
| **MEDIUM** | 25 | 0.4500 | 0.2000 | **0.2770** |
| **HIGH** | 25 | 0.9500 | 0.6800 | **0.7925** |
| **CRITICAL** | 20 | 0.8500 | 0.9500 | **0.8970** |

---

## 3. Operational Characteristics
- **Total Clauses Evaluated:** 70 clauses (partitioned into 14 batches of 5)
- **Total API Calls Dispatched Today:** 16 calls (Daily limit reached)
- **Daily Budget Remaining:** 0 / 16 calls (resets at 00:00 UTC)
- **Batch Size:** 5 clauses / API call
- **Average Batch Latency:** 22,450 ms
- **Resumption Behavior:** Redis limiter and ARQ worker cleanly pause the job with status `"waiting for quota"` and resume automatically without failing the job or losing intermediate progress.
