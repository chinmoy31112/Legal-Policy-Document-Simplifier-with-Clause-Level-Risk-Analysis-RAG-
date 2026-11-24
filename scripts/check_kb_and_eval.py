"""
Check Knowledge Base overlap against labeled evaluation sets and run retrieval evaluation.
"""

import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ai.embedding import GeminiEmbedder
from app.ai.vector_store import InMemoryVectorStore
from app.services.knowledge_base_service import KnowledgeBaseService


def norm_hash(text: str) -> str:
    return hashlib.sha256(" ".join(text.split()).encode("utf-8")).hexdigest()


async def main():
    kb_file = BACKEND_DIR / "knowledge_base" / "reference_clauses.json"
    risk_file = ROOT_DIR / "tests" / "eval_data" / "risk_set" / "risk_dataset.json"
    retrieval_file = ROOT_DIR / "tests" / "eval_data" / "retrieval_set" / "retrieval_truth.json"
    seg_file = ROOT_DIR / "tests" / "eval_data" / "segmentation_set" / "ground_truth.json"

    # 1. Load KB
    kb_clauses = json.loads(kb_file.read_text(encoding="utf-8"))
    kb_hashes = {norm_hash(c["text"]): c for c in kb_clauses}

    # 2. Check metadata (sources and licenses)
    unknown_sources = [c["id"] for c in kb_clauses if not c.get("source") or c.get("source") == "unknown"]
    unknown_licenses = [c["id"] for c in kb_clauses if not c.get("license") or c.get("license") == "unknown"]
    sources_summary = {}
    licenses_summary = {}
    for c in kb_clauses:
        s = c.get("source", "unknown")
        lic = c.get("license", "unknown")
        sources_summary[s] = sources_summary.get(s, 0) + 1
        licenses_summary[lic] = licenses_summary.get(lic, 0) + 1

    # 3. Check overlaps
    overlaps = []

    # Check risk set
    if risk_file.exists():
        risk_data = json.loads(risk_file.read_text(encoding="utf-8"))
        for item in risk_data:
            h = norm_hash(item.get("clause_text", ""))
            if h in kb_hashes:
                overlaps.append({
                    "eval_source": f"risk_set:{item.get('split')}",
                    "clause_id": item.get("clause_id"),
                    "kb_id": kb_hashes[h]["id"],
                })

    # Check segmentation set
    if seg_file.exists():
        seg_data = json.loads(seg_file.read_text(encoding="utf-8"))
        doc_list = seg_data if isinstance(seg_data, list) else seg_data.get("documents", [])
        for doc in doc_list:
            for c in doc.get("clauses", []):
                snippet = c.get("text", c.get("text_snippet", ""))
                if snippet:
                    h = norm_hash(snippet)
                    if h in kb_hashes:
                        overlaps.append({
                            "eval_source": f"segmentation_set:{doc.get('document')}",
                            "clause_id": c.get("order"),
                            "kb_id": kb_hashes[h]["id"],
                        })

    # 4. Retrieval Evaluation
    retrieval_exists = retrieval_file.exists()
    retrieval_metrics = {}

    if retrieval_exists:
        retrieval_data = json.loads(retrieval_file.read_text(encoding="utf-8"))
        embedder = GeminiEmbedder(force_offline=True)
        store = InMemoryVectorStore(expected_dim=embedder.dimension, expected_model=embedder.model_name)
        service = KnowledgeBaseService(embedder=embedder, vector_store=store)

        # Index KB
        index_stat = await service.index_reference_clauses_file(kb_file)

        in_domain_total = 0
        in_domain_hits_5 = 0
        reciprocal_ranks = []
        latencies_ms = []
        ood_total = 0
        ood_rejected = 0

        for item in retrieval_data:
            q_text = item["query_text"]
            is_ood = item.get("is_out_of_domain", False)
            acceptable_ids = set(item.get("acceptable_reference_ids", []))
            expected_cat = item.get("expected_category")

            t0 = time.perf_counter()
            resp = await service.retrieve(q_text, top_k=5)
            elapsed = (time.perf_counter() - t0) * 1000
            latencies_ms.append(elapsed)

            if is_ood:
                ood_total += 1
                if resp.no_reference_found and len(resp.results) == 0:
                    ood_rejected += 1
            else:
                in_domain_total += 1
                retrieved_ids = [r.id for r in resp.results]
                retrieved_cats = [r.metadata.get("category") for r in resp.results]

                hit = any(rid in acceptable_ids for rid in retrieved_ids) or any(
                    rc == expected_cat for rc in retrieved_cats
                )
                if hit:
                    in_domain_hits_5 += 1

                rr = 0.0
                for rank, r in enumerate(resp.results, start=1):
                    if r.id in acceptable_ids or r.metadata.get("category") == expected_cat:
                        rr = 1.0 / rank
                        break
                reciprocal_ranks.append(rr)

        recall_5 = round(in_domain_hits_5 / in_domain_total, 4) if in_domain_total > 0 else 0.0
        mrr = round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else 0.0
        ood_rej_pct = round((ood_rejected / ood_total * 100), 2) if ood_total > 0 else 100.0
        avg_lat = round(sum(latencies_ms) / len(latencies_ms), 2)

        retrieval_metrics = {
            "retrieval_gold_set_exists": True,
            "queries_evaluated": len(retrieval_data),
            "in_domain_queries": in_domain_total,
            "recall_at_5": recall_5,
            "mrr": mrr,
            "ood_queries": ood_total,
            "ood_rejection_percent": ood_rej_pct,
            "avg_latency_ms": avg_lat,
        }
    else:
        retrieval_metrics = {
            "retrieval_gold_set_exists": False,
        }

    output = {
        "total_kb_clauses": len(kb_clauses),
        "unique_clause_hashes": len(kb_hashes),
        "sources_summary": sources_summary,
        "licenses_summary": licenses_summary,
        "unknown_sources_count": len(unknown_sources),
        "unknown_licenses_count": len(unknown_licenses),
        "unknown_source_clause_ids": unknown_sources,
        "evaluation_overlap_count": len(overlaps),
        "evaluation_overlaps": overlaps,
        "retrieval_metrics": retrieval_metrics,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
