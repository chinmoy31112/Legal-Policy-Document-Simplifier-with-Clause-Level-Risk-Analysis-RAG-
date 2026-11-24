# Phase 4 Model Evaluation Report: `gemini-3.5-flash-lite`

- **Model Identifier:** `gemini-3.5-flash-lite`
- **Batch Size:** `4` clauses per API call
- **Dataset:** `tests/eval_data/risk_set/risk_dataset.json` (Dev Split only)
- **Evaluation Date:** 2026-11-24 11:57:55 UTC
- **Evaluation Status:** **COMPLETED**
- **Held-Out Test Split Preserved:** 31 clauses (UNTOUCHED)

---

## 1. Summary Metrics

| Metric | Target Gate | Achieved Value | Status |
| :--- | :---: | :---: | :---: |
| **Macro $F_1$ Score** | $\ge 0.75$ | **0.3958** | ⚠️ REVIEW |
| **High-Risk Recall (HIGH + CRITICAL)** | $\ge 0.85$ | **0.9333** (93.3%) | ✅ PASSED |
| **Within-One-Level Accuracy** | $\ge 0.90$ | **1.0000** (100.0%) | ✅ PASSED |
| **Schema Validity** | $100.0\%$ | **100.0%** | ✅ PASSED |
| **Evidence Grounding** | $\ge 0.90$ | **0.9643** (96.4%) | ✅ PASSED |
| **API Calls Used** | $\le 400$ RPD | **18** calls | ✅ WITHIN BUDGET |
| **Estimated Tokens Consumed** | - | **42,685** tokens | ℹ️ INFO |
| **Estimated Documents / Day** | - | **~100.0 docs/day** (at 15 clauses/doc) | ℹ️ CAPACITY |

---

## 2. Per-Class Performance Breakdown

| Risk Tier | Support | Precision | Recall | $F_1$ Score |
| :--- | :---: | :---: | :---: | :---: |
| **LOW** | 0 | 0.0000 | 1.0000 | **0.0000** |
| **MEDIUM** | 25 | 0.2500 | 0.0400 | **0.0690** |
| **HIGH** | 25 | 0.8824 | 0.6000 | **0.7143** |
| **CRITICAL** | 20 | 0.7200 | 0.9000 | **0.8000** |

---

## 3. Operational Characteristics
- **Total Clauses Evaluated:** 70 clauses
- **Total API Calls Dispatched:** 18 calls (Batch size 4)
- **Daily Budget Remaining:** 382 / 400 calls
- **Average Batch Latency:** 63314.45 ms
