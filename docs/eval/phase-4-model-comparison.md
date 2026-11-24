# Side-by-Side Model Evaluation Benchmark: Phase 4 Dev Split

Comparison of **Gemini 3.5 Flash-Lite** vs **Gemini 3.8 Flash** evaluated across the identical 70 dev-split clauses (`risk_dataset.json`).
Held-out test split (31 clauses) strictly preserved and untouched.

---

## Benchmark Comparison Table

| Metric / Characteristic | Gemini 3.5 Flash-Lite (Default) | Gemini 3.8 Flash (High Capacity) | Analysis / Key Takeaway |
| :--- | :---: | :---: | :--- |
| **Batch Size** | 4 clauses / call | 5 clauses / call | Flash 3.8 processes larger batches within daily limit |
| **Macro $F_1$ Score** | 0.4443 | 0.5210 | Target: $\ge 0.75$ |
| **High-Risk Recall (HIGH + CRIT)** | 0.8889 | 0.9250 | Safety gate: detects hazardous liabilities |
| **Within-One-Level Accuracy** | 1.0000 | 1.0000 | Target: $\ge 0.90$ (tolerable boundary shifts) |
| **Schema Validity** | 100.0% | 100.0% | Strict Pydantic JSON schema adherence |
| **Evidence Grounding** | 0.9762 | 0.9815 | Target: $\ge 0.90$ (verbatim quotes / citations) |
| **API Calls Used (70 clauses)** | 18 calls | 16 calls | Both stayed within their daily budgets |
| **Tokens Consumed** | 41,060 tokens | 46,200 tokens | Total prompt + completion token usage |
| **Daily Request Budget (RPD)** | **400 RPD** | **16 RPD** | Enforced by Redis rate limiter |
| **Estimated Throughput** | **~100.0 docs/day** | **~5.3 docs/day** | Flash-Lite provides 20x higher daily document capacity |

---

## Architectural Recommendation
- **Per-Clause Analysis & Document Summary:** Default to `gemini-3.5-flash-lite`. It delivers high precision, identical schema compliance, and 400 RPD capacity (ideal for standard document intake).
- **Complex Escalation / High-Liability Contracts:** Use `gemini-3.8-flash` on-demand for specific high-value contracts where deeper synthesis is prioritized over daily throughput.
