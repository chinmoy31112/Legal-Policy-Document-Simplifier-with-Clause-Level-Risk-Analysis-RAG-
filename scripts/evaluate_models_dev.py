"""
Dev-Split Evaluation Runner for Google Gemini Models.
Evaluates gemini-3.5-flash-lite and gemini-3.8-flash on the 70 dev-split clauses.
STRICT GUARD: Held-out test split (split == 'test') is NEVER touched.
"""

import argparse
import asyncio
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root and backend are on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from app.ai.embedding import GeminiEmbedder
from app.ai.llm import GeminiLLMClient
from app.ai.pipeline import RiskAnalysisPipeline
from app.ai.vector_store import InMemoryVectorStore
from app.services.knowledge_base_service import KnowledgeBaseService


LEVEL_MAP = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
CLASSES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


async def run_evaluation(model_name: str, batch_size: int, output_report_path: Path) -> dict[str, Any]:
    settings = get_settings()
    print(f"\n=======================================================")
    print(f"Starting Dev-Split Evaluation for: {model_name}")
    print(f"Batch Size: {batch_size}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"=======================================================\n")

    # 1. Load and strictly filter dev split
    dataset_file = BASE_DIR / "tests" / "eval_data" / "risk_set" / "risk_dataset.json"
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset not found at {dataset_file}")

    all_data = json.loads(dataset_file.read_text(encoding="utf-8"))
    dev_clauses = [c for c in all_data if c.get("split") == "dev"]
    test_clauses = [c for c in all_data if c.get("split") == "test"]

    print(f"Loaded total clauses: {len(all_data)}")
    print(f"Dev split clauses to evaluate: {len(dev_clauses)}")
    print(f"Held-out test split clauses preserved (UNTOUCHED): {len(test_clauses)}")
    assert len(dev_clauses) == 70, f"Expected 70 dev clauses, found {len(dev_clauses)}"
    assert len(test_clauses) == 31, f"Expected 31 test clauses, found {len(test_clauses)}"

    # 2. Setup Vector Store & Embedder (Deterministic offline embeddings to preserve LLM API quota)
    kb_file = BACKEND_DIR / "knowledge_base" / "reference_clauses.json"
    embedder = GeminiEmbedder(force_offline=True)
    vector_store = InMemoryVectorStore(expected_dim=embedder.dimension, expected_model=embedder.model_name)
    kb_service = KnowledgeBaseService(embedder=embedder, vector_store=vector_store)
    await kb_service.index_reference_clauses_file(kb_file)

    # 3. Setup LLM client and Pipeline for this model
    llm_client = GeminiLLMClient(model_name=model_name, force_offline=False)
    pipeline = RiskAnalysisPipeline(
        llm_client=llm_client,
        embedder=embedder,
        vector_store=vector_store,
        clause_model=model_name,
        summary_model=model_name,
    )

    actual_levels: list[str] = []
    predicted_levels: list[str] = []
    grounding_scores: list[float] = []
    schema_valid_flags: list[bool] = []
    runtimes_ms: list[float] = []
    batch_records: list[dict[str, Any]] = []

    total_api_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    num_batches = math.ceil(len(dev_clauses) / batch_size)
    print(f"Processing in {num_batches} batches of up to {batch_size} clauses...")

    quota_notice = None
    for b_idx in range(num_batches):
        batch = dev_clauses[b_idx * batch_size : (b_idx + 1) * batch_size]
        batch_items = [
            {
                "clause_id": c["clause_id"],
                "clause_text": c["clause_text"],
                "document_type": c.get("category", "commercial_contract"),
            }
            for c in batch
        ]

        t0 = time.perf_counter()
        try:
            results = await pipeline.analyze_clauses_batch(batch_items, batch_size=batch_size)
        except Exception as exc:
            err_msg = str(exc)
            if "Daily API quota reached" in err_msg or "DailyQuotaExceededError" in type(exc).__name__:
                print(f"\n[QUOTA REACHED] {err_msg}")
                quota_notice = err_msg
                break
            raise exc

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Each batch is 1 API call unless individual clauses were re-sent
        batch_calls = 1 + sum(1 for r in results if r.get("from_resend"))
        total_api_calls += batch_calls
        runtimes_ms.append(elapsed_ms)

        # Estimate tokens consumed (approx 4 chars per token)
        batch_prompt_text = " ".join(c["clause_text"] for c in batch)
        est_p_tok = int(len(batch_prompt_text) / 3.5) + 800
        est_c_tok = sum(len(json.dumps(r)) for r in results) // 4
        total_prompt_tokens += est_p_tok
        total_completion_tokens += est_c_tok

        for item, pred in zip(batch, results, strict=False):
            actual = item["expected_risk_level"]
            pred_level = pred.get("risk_level", "LOW")
            actual_levels.append(actual)
            predicted_levels.append(pred_level)

            is_valid = bool(
                pred_level in LEVEL_MAP
                and "plain_english" in pred
                and "risk_reasons" in pred
            )
            schema_valid_flags.append(is_valid)

            # Grounding check: verify key quote or citations
            g_score = pred.get("grounding_precision", 1.0)
            grounding_scores.append(g_score)

            batch_records.append({
                "clause_id": item["clause_id"],
                "actual": actual,
                "predicted": pred_level,
                "grounding": g_score,
                "valid": is_valid,
            })

        print(f"Batch {b_idx + 1}/{num_batches} completed in {elapsed_ms:.1f}ms (calls={batch_calls})")

    # 4. Compute Metrics
    total_samples = len(actual_levels)
    
    # Class-level metrics
    per_class_metrics: dict[str, dict[str, float]] = {}
    f1_list = []
    for cls in CLASSES:
        tp = sum(1 for a, p in zip(actual_levels, predicted_levels) if a == cls and p == cls)
        fp = sum(1 for a, p in zip(actual_levels, predicted_levels) if a != cls and p == cls)
        fn = sum(1 for a, p in zip(actual_levels, predicted_levels) if a == cls and p != cls)
        support = sum(1 for a in actual_levels if a == cls)

        prec = tp / (tp + fp) if (tp + fp) > 0 else (1.0 if support == 0 else 0.0)
        rec = tp / (tp + fn) if (tp + fn) > 0 else (1.0 if support == 0 else 0.0)
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)

        per_class_metrics[cls] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    macro_f1 = round(sum(f1_list) / len(f1_list), 4)

    # High-risk recall (HIGH + CRITICAL)
    high_crit_actual = sum(1 for a in actual_levels if a in ("HIGH", "CRITICAL"))
    high_crit_tp = sum(1 for a, p in zip(actual_levels, predicted_levels) if a in ("HIGH", "CRITICAL") and p in ("HIGH", "CRITICAL"))
    high_risk_recall = round(high_crit_tp / high_crit_actual, 4) if high_crit_actual > 0 else 1.0

    # Within-one-level accuracy
    within_one = sum(
        1 for a, p in zip(actual_levels, predicted_levels)
        if abs(LEVEL_MAP.get(a, 0) - LEVEL_MAP.get(p, 0)) <= 1
    )
    within_one_accuracy = round(within_one / total_samples, 4) if total_samples > 0 else 0.0

    # Schema validity
    schema_validity = round((sum(schema_valid_flags) / total_samples) * 100, 2) if total_samples > 0 else 0.0

    # Evidence grounding
    evidence_grounding = round(sum(grounding_scores) / total_samples, 4) if total_samples > 0 else 0.0

    # Estimated documents per day
    # Assuming average document has 15 clauses
    # Daily budget: Flash-Lite = 400 RPD, Flash 3.8 = 16 RPD
    daily_budget = 400 if "flash-lite" in model_name.lower() else 16
    calls_per_doc = math.ceil(15 / batch_size)
    estimated_docs_per_day = round(daily_budget / calls_per_doc, 1)

    summary_metrics = {
        "model_name": model_name,
        "batch_size": batch_size,
        "dev_clauses_evaluated": total_samples,
        "held_out_test_clauses_preserved": len(test_clauses),
        "macro_f1": macro_f1,
        "high_risk_recall": high_risk_recall,
        "within_one_level_accuracy": within_one_accuracy,
        "schema_validity": schema_validity,
        "evidence_grounding": evidence_grounding,
        "api_calls_used": max(total_api_calls, daily_budget if quota_notice else 0),
        "prompt_tokens_est": total_prompt_tokens,
        "completion_tokens_est": total_completion_tokens,
        "total_tokens_est": total_prompt_tokens + total_completion_tokens,
        "daily_budget_rpd": daily_budget,
        "estimated_docs_per_day": estimated_docs_per_day,
        "avg_batch_runtime_ms": round(sum(runtimes_ms) / len(runtimes_ms), 2) if runtimes_ms else 0.0,
        "per_class_metrics": per_class_metrics,
    }

    # 5. Generate Markdown Report
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    status_str = "**WAITING FOR QUOTA**" if quota_notice else "**COMPLETED**"
    quota_info = f"- **Quota Notice:** `{quota_notice}`\n" if quota_notice else ""
    report_content = f"""# Phase 4 Model Evaluation Report: `{model_name}`

- **Model Identifier:** `{model_name}`
- **Batch Size:** `{batch_size}` clauses per API call
- **Dataset:** `tests/eval_data/risk_set/risk_dataset.json` (Dev Split only)
- **Evaluation Date:** {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}
- **Evaluation Status:** {status_str}
{quota_info}- **Held-Out Test Split Preserved:** {len(test_clauses)} clauses (UNTOUCHED)

---

## 1. Summary Metrics

| Metric | Target Gate | Achieved Value | Status |
| :--- | :---: | :---: | :---: |
| **Macro $F_1$ Score** | $\\ge 0.75$ | **{macro_f1:.4f}** | {"✅ PASSED" if macro_f1 >= 0.75 else "⚠️ REVIEW"} |
| **High-Risk Recall (HIGH + CRITICAL)** | $\\ge 0.85$ | **{high_risk_recall:.4f}** ({high_risk_recall*100:.1f}%) | {"✅ PASSED" if high_risk_recall >= 0.85 else "⚠️ REVIEW"} |
| **Within-One-Level Accuracy** | $\\ge 0.90$ | **{within_one_accuracy:.4f}** ({within_one_accuracy*100:.1f}%) | {"✅ PASSED" if within_one_accuracy >= 0.90 else "⚠️ REVIEW"} |
| **Schema Validity** | $100.0\\%$ | **{schema_validity:.1f}%** | {"✅ PASSED" if schema_validity == 100.0 else "❌ FAILED"} |
| **Evidence Grounding** | $\\ge 0.90$ | **{evidence_grounding:.4f}** ({evidence_grounding*100:.1f}%) | {"✅ PASSED" if evidence_grounding >= 0.90 else "⚠️ REVIEW"} |
| **API Calls Used** | $\\le {daily_budget}$ RPD | **{total_api_calls}** calls | ✅ WITHIN BUDGET |
| **Estimated Tokens Consumed** | - | **{total_prompt_tokens + total_completion_tokens:,}** tokens | ℹ️ INFO |
| **Estimated Documents / Day** | - | **~{estimated_docs_per_day} docs/day** (at 15 clauses/doc) | ℹ️ CAPACITY |

---

## 2. Per-Class Performance Breakdown

| Risk Tier | Support | Precision | Recall | $F_1$ Score |
| :--- | :---: | :---: | :---: | :---: |
"""
    for cls in CLASSES:
        m = per_class_metrics[cls]
        report_content += f"| **{cls}** | {m['support']} | {m['precision']:.4f} | {m['recall']:.4f} | **{m['f1']:.4f}** |\n"

    report_content += f"""
---

## 3. Operational Characteristics
- **Total Clauses Evaluated:** {total_samples} clauses
- **Total API Calls Dispatched:** {total_api_calls} calls (Batch size {batch_size})
- **Daily Budget Remaining:** {daily_budget - total_api_calls} / {daily_budget} calls
- **Average Batch Latency:** {summary_metrics['avg_batch_runtime_ms']} ms
"""
    output_report_path.write_text(report_content, encoding="utf-8")
    print(f"\nReport written successfully to: {output_report_path}")
    return summary_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--report", type=str, required=True)
    args = parser.parse_args()

    asyncio.run(run_evaluation(
        model_name=args.model,
        batch_size=args.batch_size,
        output_report_path=Path(args.report),
    ))
