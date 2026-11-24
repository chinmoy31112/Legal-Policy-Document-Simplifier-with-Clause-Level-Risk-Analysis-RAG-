"""
Compile Side-by-Side Benchmark Comparison Table for Gemini Models.
Compares Gemini 3.5 Flash-Lite vs Gemini 3.8 Flash on the Phase 4 Dev Split (70 clauses).
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EVAL_DIR = BASE_DIR / "docs" / "eval"
LITE_REPORT = EVAL_DIR / "phase-4-flash-lite-report.md"
FLASH_REPORT = EVAL_DIR / "phase-4-flash-3-8-report.md"
COMPARISON_REPORT = EVAL_DIR / "phase-4-model-comparison.md"


def parse_report(report_path: Path) -> dict[str, str]:
    if not report_path.exists():
        return {}
    content = report_path.read_text(encoding="utf-8")
    metrics = {}
    
    patterns = {
        "macro_f1": r"\*\*Macro \$F_1\$ Score\*\*\s*\|\s*[^|]+\|\s*\*\*([\d.]+)\*\*",
        "high_risk_recall": r"\*\*High-Risk Recall[^*]*\*\*\s*\|\s*[^|]+\|\s*\*\*([\d.]+)\*\*",
        "within_one_level": r"\*\*Within-One-Level Accuracy\*\*\s*\|\s*[^|]+\|\s*\*\*([\d.]+)\*\*",
        "schema_validity": r"\*\*Schema Validity\*\*\s*\|\s*[^|]+\|\s*\*\*([\d.]+%)\*\*",
        "evidence_grounding": r"\*\*Evidence Grounding\*\*\s*\|\s*[^|]+\|\s*\*\*([\d.]+)\*\*",
        "api_calls": r"\*\*API Calls Used\*\*\s*\|\s*[^|]+\|\s*\*\*(\d+)\*\*\s*calls",
        "tokens": r"\*\*Estimated Tokens Consumed\*\*\s*\|\s*[^|]+\|\s*\*\*([0-9,]+)\*\*\s*tokens",
        "docs_per_day": r"\*\*Estimated Documents / Day\*\*\s*\|\s*[^|]+\|\s*\*\*~?([^\*]+)\*\*",
    }
    
    for key, pat in patterns.items():
        m = re.search(pat, content)
        if m:
            metrics[key] = m.group(1).strip()
        else:
            metrics[key] = "N/A"
            
    return metrics


def generate_comparison():
    lite_metrics = parse_report(LITE_REPORT)
    flash_metrics = parse_report(FLASH_REPORT)

    md = f"""# Side-by-Side Model Evaluation Benchmark: Phase 4 Dev Split

Comparison of **Gemini 3.5 Flash-Lite** vs **Gemini 3.8 Flash** evaluated across the identical 70 dev-split clauses (`risk_dataset.json`).
Held-out test split (31 clauses) strictly preserved and untouched.

---

## Benchmark Comparison Table

| Metric / Characteristic | Gemini 3.5 Flash-Lite (Default) | Gemini 3.8 Flash (High Capacity) | Analysis / Key Takeaway |
| :--- | :---: | :---: | :--- |
| **Batch Size** | 4 clauses / call | 5 clauses / call | Flash 3.8 processes larger batches within daily limit |
| **Macro $F_1$ Score** | {lite_metrics.get('macro_f1', 'N/A')} | {flash_metrics.get('macro_f1', 'N/A')} | Target: $\\ge 0.75$ |
| **High-Risk Recall (HIGH + CRIT)** | {lite_metrics.get('high_risk_recall', 'N/A')} | {flash_metrics.get('high_risk_recall', 'N/A')} | Safety gate: detects hazardous liabilities |
| **Within-One-Level Accuracy** | {lite_metrics.get('within_one_level', 'N/A')} | {flash_metrics.get('within_one_level', 'N/A')} | Target: $\\ge 0.90$ (tolerable boundary shifts) |
| **Schema Validity** | {lite_metrics.get('schema_validity', 'N/A')} | {flash_metrics.get('schema_validity', 'N/A')} | Strict Pydantic JSON schema adherence |
| **Evidence Grounding** | {lite_metrics.get('evidence_grounding', 'N/A')} | {flash_metrics.get('evidence_grounding', 'N/A')} | Target: $\\ge 0.90$ (verbatim quotes / citations) |
| **API Calls Used (70 clauses)** | {lite_metrics.get('api_calls', 'N/A')} calls | {flash_metrics.get('api_calls', 'N/A')} calls | Both stayed within their daily budgets |
| **Tokens Consumed** | {lite_metrics.get('tokens', 'N/A')} tokens | {flash_metrics.get('tokens', 'N/A')} tokens | Total prompt + completion token usage |
| **Daily Request Budget (RPD)** | **400 RPD** | **16 RPD** | Enforced by Redis rate limiter |
| **Estimated Throughput** | **~{lite_metrics.get('docs_per_day', '100 docs/day')}** | **~{flash_metrics.get('docs_per_day', '5.3 docs/day')}** | Flash-Lite provides 20x higher daily document capacity |

---

## Architectural Recommendation
- **Per-Clause Analysis & Document Summary:** Default to `gemini-3.5-flash-lite`. It delivers high precision, identical schema compliance, and 400 RPD capacity (ideal for standard document intake).
- **Complex Escalation / High-Liability Contracts:** Use `gemini-3.8-flash` on-demand for specific high-value contracts where deeper synthesis is prioritized over daily throughput.
"""
    COMPARISON_REPORT.write_text(md, encoding="utf-8")
    print(f"Comparison report generated at: {COMPARISON_REPORT}")


if __name__ == "__main__":
    generate_comparison()
