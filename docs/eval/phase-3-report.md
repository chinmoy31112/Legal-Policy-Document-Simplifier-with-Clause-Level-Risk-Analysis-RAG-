# Phase 3 Evaluation Report

- **Phase Name:** Knowledge Base and Retrieval
- **Evaluated At:** 2026-11-24 11:25:51 UTC
- **Status:** **PASSED**
- **Evaluation Gate Met:** **YES**

## Quantitative Metrics

| Metric / Check | Value | Status |
| :--- | :---: | :---: |
| `indexed_reference_clauses` | `200` | ℹ️ INFO |
| `in_domain_queries_evaluated` | `35` | ℹ️ INFO |
| `recall_at_5` | `0.8286` | ✅ PASS (>= 0.80) |
| `mrr` | `0.8286` | ✅ PASS (>= 0.70) |
| `ood_queries_evaluated` | `15` | ℹ️ INFO |
| `ood_rejection_percent` | `100.0%` | ✅ PASS (= 100%) |
| `dimension_mismatch_refused` | `True` | ✅ PASS |
| `model_mismatch_refused` | `True` | ✅ PASS |
| `guardrails_enforced` | `True` | ✅ PASS |
| `avg_retrieval_latency_ms` | `15.53 ms` | ⚡ FAST |

## Diagnostic Notes
Phase 3 evaluation completed successfully. All gates satisfied under deterministic evaluation.
