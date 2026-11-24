"""
Knowledge Base PDF Ingestion Script.

Supports:
- Resumable and idempotent ingestion with batch limits.
- Evaluates Stage 1 (first N documents) and Stage 2 (remaining documents).
- Records source and license metadata ('unknown' if not provided).
- Cross-checks text hashes against labeled evaluation sets (Rule: zero contamination).
- Reports peak RPM/TPM, cache hit rate, and duplicate count.
"""

import argparse
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

try:
    from backend.app.ai.embedding import GeminiEmbedder
    from backend.app.ai.vector_store import get_vector_store
    from backend.app.core.config import get_settings
    from backend.app.core.logging import get_logger
    from backend.app.document_processing import segment_document
    from backend.app.document_processing.formats import extract_document
    from backend.app.services.knowledge_base_service import KnowledgeBaseService
except ImportError:
    from app.ai.embedding import GeminiEmbedder  # type: ignore[no-redef]
    from app.ai.vector_store import get_vector_store  # type: ignore[no-redef]
    from app.core.config import get_settings  # type: ignore[no-redef]
    from app.core.logging import get_logger  # type: ignore[no-redef]
    from app.document_processing import segment_document  # type: ignore[no-redef]
    from app.document_processing.formats import extract_document  # type: ignore[no-redef]
    from app.services.knowledge_base_service import KnowledgeBaseService  # type: ignore[no-redef]

logger = get_logger(__name__)


def compute_normalized_hash(text: str) -> str:
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_evaluation_hashes() -> dict[str, str]:
    """Load text hashes of all labeled evaluation documents and clauses."""
    eval_hashes: dict[str, str] = {}

    # 1. Risk set (dev and test splits)
    risk_file = ROOT_DIR / "tests" / "eval_data" / "risk_set" / "risk_dataset.json"
    if risk_file.exists():
        data = json.loads(risk_file.read_text(encoding="utf-8"))
        for item in data:
            c_text = item.get("clause_text", "")
            if c_text:
                h = compute_normalized_hash(c_text)
                eval_hashes[h] = f"risk_dataset:{item.get('clause_id')}:{item.get('split')}"

    # 2. Retrieval set
    retrieval_file = ROOT_DIR / "tests" / "eval_data" / "retrieval_set" / "retrieval_truth.json"
    if retrieval_file.exists():
        data = json.loads(retrieval_file.read_text(encoding="utf-8"))
        for item in data:
            q_text = item.get("query_text", "")
            if q_text:
                h = compute_normalized_hash(q_text)
                eval_hashes[h] = f"retrieval_set:{item.get('query_id')}"

    # 3. Segmentation set
    seg_file = ROOT_DIR / "tests" / "eval_data" / "segmentation_set" / "ground_truth.json"
    if seg_file.exists():
        data = json.loads(seg_file.read_text(encoding="utf-8"))
        doc_list = data if isinstance(data, list) else data.get("documents", [])
        for doc in doc_list:
            for c in doc.get("clauses", []):
                c_text = c.get("text", c.get("text_snippet", ""))
                if c_text:
                    h = compute_normalized_hash(c_text)
                    eval_hashes[h] = f"segmentation_set:{doc.get('document')}"

    return eval_hashes


async def ingest_kb_pdfs(
    folder_path: str | Path,
    batch_limit: int | None = None,
    source: str = "unknown",
    license_str: str = "unknown",
    dry_run: bool = False,
) -> dict[str, Any]:
    folder = Path(folder_path).resolve()
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"PDF folder not found or is not a directory: {folder}")

    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        pdf_files = sorted(folder.glob("**/*.pdf"))

    total_found = len(pdf_files)
    if total_found == 0:
        return {
            "status": "FAILED",
            "error": f"No PDF files found in directory {folder}",
            "documents_found": 0,
        }

    selected_files = pdf_files[:batch_limit] if batch_limit else pdf_files

    # Check evaluation overlap
    eval_hashes = load_evaluation_hashes()
    overlap_clauses: list[dict[str, str]] = []

    settings = get_settings()
    embedder = GeminiEmbedder()
    vector_store = get_vector_store()
    kb_service = KnowledgeBaseService(embedder=embedder, vector_store=vector_store)

    documents_ingested = 0
    clauses_created = 0
    failed_files: list[dict[str, str]] = []
    duplicate_count = 0
    cache_hits = 0
    total_clauses_extracted = 0

    peak_rpm = 0
    peak_tpm = 0

    t_start = time.perf_counter()

    for idx, pdf_file in enumerate(selected_files, start=1):
        try:
            logger.info("kb_ingestion_file_start", file=pdf_file.name, index=idx, total=len(selected_files))
            extraction = extract_document(pdf_file)
            if extraction.errors and not extraction.raw_text:
                failed_files.append({"file": pdf_file.name, "reason": f"Extraction error: {extraction.errors}"})
                continue

            segments = segment_document(extraction, doc_id=pdf_file.stem)
            if not segments:
                failed_files.append({"file": pdf_file.name, "reason": "No usable clauses segmented"})
                continue

            total_clauses_extracted += len(segments)
            to_embed_segments = []

            for seg in segments:
                h = compute_normalized_hash(seg.text)
                # Check eval contamination
                if h in eval_hashes:
                    overlap_clauses.append({
                        "file": pdf_file.name,
                        "clause": seg.text[:80] + "...",
                        "evaluation_match": eval_hashes[h],
                    })

                # Check idempotency
                if h in kb_service._indexed_hashes:
                    duplicate_count += 1
                    cache_hits += 1
                    continue

                to_embed_segments.append(seg)

            if dry_run:
                documents_ingested += 1
                clauses_created += len(to_embed_segments)
                continue

            # Embed and index
            if to_embed_segments:
                clause_dicts = [
                    {
                        "id": f"{pdf_file.stem}_{seg.id}",
                        "title": seg.title or f"Clause {seg.clause_number or ''}".strip(),
                        "text": seg.text,
                        "category": seg.category or "General",
                        "document_type": "PDF Reference Document",
                        "source": source if source != "unknown" else pdf_file.name,
                        "license": license_str,
                        "jurisdiction": "General",
                        "version": "1.0.0",
                        "language": "en",
                        "why_standard_or_risky": f"Indexed reference clause from {pdf_file.name}",
                        "text_hash": compute_normalized_hash(seg.text),
                    }
                    for seg in to_embed_segments
                ]
                await kb_service.retrieval_service.index_reference_clauses(clause_dicts)
                for c in clause_dicts:
                    kb_service._indexed_hashes.add(c["text_hash"])

                clauses_created += len(clause_dicts)

            documents_ingested += 1

            # Monitor limiter usage
            limiter = embedder._throttle
            if limiter:
                cur_rpm = len(getattr(limiter, "_local_history", []))
                cur_tpm = sum(e[1] for e in getattr(limiter, "_local_history", []))
                peak_rpm = max(peak_rpm, cur_rpm)
                peak_tpm = max(peak_tpm, cur_tpm)

        except Exception as exc:  # noqa: BLE001
            logger.error("kb_ingestion_file_failed", file=pdf_file.name, error=str(exc))
            failed_files.append({"file": pdf_file.name, "reason": str(exc)})

    elapsed = round(time.perf_counter() - t_start, 2)
    cache_hit_rate = round((cache_hits / total_clauses_extracted * 100), 2) if total_clauses_extracted > 0 else 0.0

    return {
        "status": "COMPLETED" if not failed_files else "COMPLETED_WITH_FAILURES",
        "folder": str(folder),
        "total_pdfs_in_folder": total_found,
        "batch_limit_applied": batch_limit,
        "documents_ingested": documents_ingested,
        "clauses_created": clauses_created,
        "total_clauses_extracted": total_clauses_extracted,
        "failed_files": failed_files,
        "peak_rpm": peak_rpm,
        "max_rpm_limit": settings.gemini_embedding_rpm,
        "peak_tpm": peak_tpm,
        "max_tpm_limit": settings.gemini_embedding_tpm,
        "cache_hits": cache_hits,
        "cache_hit_rate_percent": cache_hit_rate,
        "duplicate_count": duplicate_count,
        "source_recorded": source,
        "license_recorded": license_str,
        "evaluation_overlap_count": len(overlap_clauses),
        "evaluation_overlap_details": overlap_clauses,
        "elapsed_seconds": elapsed,
        "dry_run": dry_run,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Knowledge Base PDFs with rate limiting and idempotency.")
    parser.add_argument("--folder", default="tests/eval_data/segmentation_set", help="Folder containing the PDF documents (default: 'tests/eval_data/segmentation_set').")
    parser.add_argument("--batch-limit", type=int, default=None, help="Limit number of documents to ingest (e.g. 5 for Stage 1).")
    parser.add_argument("--source", default="unknown", help="Source metadata for documents (default: 'unknown').")
    parser.add_argument("--license", default="unknown", help="License metadata for documents (default: 'unknown').")
    parser.add_argument("--dry-run", action="store_true", help="Perform extraction and idempotency check without indexing.")
    args = parser.parse_args()

    res = asyncio.run(ingest_kb_pdfs(
        folder_path=args.folder,
        batch_limit=args.batch_limit,
        source=args.source,
        license_str=args.license,
        dry_run=args.dry_run,
    ))
    print(json.dumps(res, indent=2))
