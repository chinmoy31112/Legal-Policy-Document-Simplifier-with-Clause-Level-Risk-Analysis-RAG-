"""
Analysis service.

Manages the background execution of the RAG pipeline for document analysis
and provides methods to retrieve the results.
"""

import asyncio
import os
import time
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline import AnalysisPipeline
from app.ai.rate_limiter import (
    DailyQuotaExceededError,
    UserQuotaExceededError,
    get_user_quota_limiter,
)
from app.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.metrics import track_clause_risk
from app.document_processing import DocumentSegmenter, extract_document
from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.models.clause import Clause
from app.repositories.analysis_repo import AnalysisResultRepository, DocumentAnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.repositories.document_repo import DocumentRepository

logger = get_logger(__name__)


class AnalysisService:
    """Service for running and managing document analysis tasks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.analysis_repo = AnalysisResultRepository(session)
        self.doc_analysis_repo = DocumentAnalysisRepository(session)
        self.pipeline = AnalysisPipeline()

    async def _run_analysis_task(self, document_id: UUID) -> None:
        """
        Background task to run the full RAG analysis pipeline on a document.
        """
        job_start_time = time.perf_counter()
        try:
            logger.info("analysis_task_started", document_id=str(document_id))

            # Fetch document and clauses
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                logger.error("analysis_doc_not_found", document_id=str(document_id))
                return

            if document.status == "completed":
                logger.info("analysis_task_already_completed", document_id=str(document_id))
                return

            # Measure upload stage duration
            stage_upload = 0.0
            if document.metadata_ and "upload_duration_seconds" in document.metadata_:
                stage_upload = float(document.metadata_["upload_duration_seconds"])
            else:
                t_stat_0 = time.perf_counter()
                if os.path.exists(document.file_path):
                    _ = os.path.getsize(document.file_path)
                stage_upload = time.perf_counter() - t_stat_0

            await self.document_repo.update_status(document_id, "extracting")
            await self.session.commit()

            # Measure extraction and segmentation in separate stages
            segmenter = DocumentSegmenter(min_clause_length=50)

            t_ext_0 = time.perf_counter()
            extraction_result = await asyncio.to_thread(extract_document, document.file_path)
            stage_extraction = time.perf_counter() - t_ext_0

            t_seg_0 = time.perf_counter()
            segments = await asyncio.to_thread(segmenter.segment, extraction_result)
            stage_segmentation = time.perf_counter() - t_seg_0

            # Update document with extraction results
            document.raw_text = extraction_result.raw_text
            document.is_scanned = extraction_result.is_scanned
            existing_meta = document.metadata_ or {}
            if extraction_result.metadata:
                existing_meta.update(extraction_result.metadata)
            document.metadata_ = existing_meta

            # Pre-analysis legal classification check:
            # Prevents hallucinating contract risk scores and invented provisions on non-legal documents (e.g. setup guides)
            classification = await self.pipeline.classify_document_type(
                raw_text=extraction_result.raw_text,
                declared_type=document.document_type,
            )

            if not classification.is_legal_document:
                logger.info(
                    "document_classified_as_non_legal",
                    document_id=str(document_id),
                    detected_type=classification.document_type_detected,
                    reason=classification.reason,
                )
                document.document_type = "non_legal"
                existing_meta["detected_document_type"] = classification.document_type_detected
                existing_meta["classification_reason"] = classification.reason
                existing_meta["is_legal_document"] = False
                document.metadata_ = existing_meta

                non_legal_summary = DocumentAnalysis(
                    document_id=document.id,
                    overall_risk_score=None,
                    overall_summary="This doesn't look like a legal or policy document.",
                    top_risky_clauses=[],
                    clause_statistics={"total_clauses": 0, "evaluated_clauses": 0},
                    risk_distribution={},
                    recommendations=[
                        f"Detected document type: {classification.document_type_detected}.",
                        "Upload a legal contract, Terms of Service, Privacy Policy, or NDA to run clause-level risk scoring.",
                    ],
                )
                self.session.add(non_legal_summary)
                await self.document_repo.update_status(document_id, "completed")
                await self.session.commit()
                return

            await self.session.commit()

            # Create clauses
            if not segments:
                logger.warning("analysis_no_clauses", document_id=str(document_id))
                await self.document_repo.update_status(document_id, "failed")
                await self.session.commit()
                return

            # Check per-user quota
            user_quota = get_user_quota_limiter()
            user_id_str = str(document.user_id) if getattr(document, "user_id", None) else ""
            try:
                await user_quota.check_and_increment(
                    user_id=user_id_str, clause_count=len(segments)
                )
            except UserQuotaExceededError as q_err:
                logger.warning("user_quota_exceeded", document_id=str(document_id), error=str(q_err))
                await self.document_repo.update_status(document_id, "failed")
                await self.session.commit()
                return

            # If clauses were already created in a previous attempt, reuse them for clean resume
            existing_clauses = await self.clause_repo.get_by_document(document.id)
            if existing_clauses:
                clauses = list(existing_clauses)
            else:
                clauses = [
                    Clause(
                        document_id=document.id,
                        clause_index=getattr(segment, "order", getattr(segment, "index", idx)),
                        clause_number=getattr(segment, "clause_number", str(idx + 1)),
                        title=segment.title,
                        content=getattr(segment, "text", getattr(segment, "content", "")),
                        category=getattr(segment, "category", "general"),
                        start_page=getattr(segment, "page", getattr(segment, "start_page", 1)),
                        end_page=getattr(segment, "page", getattr(segment, "end_page", 1)),
                    )
                    for idx, segment in enumerate(segments)
                ]
                await self.clause_repo.bulk_create(clauses)

            await self.document_repo.update_status(document_id, "analyzing")
            await self.session.commit()

            # Clean job resume: check which clauses are already analyzed
            existing_analyses = await self.analysis_repo.get_by_document(document.id)
            analyzed_clause_map: dict[str, Any] = {str(a.clause_id): a for a in existing_analyses}

            # Batch-embed all document clauses up front: single embedding reused for storage & retrieval
            unembedded_clauses = [c for c in clauses if c.content]
            unembedded_texts = [c.content for c in unembedded_clauses]
            clause_vectors: list[list[float]] = []
            stage_embedding = 0.0
            if unembedded_texts:
                t_emb_0 = time.perf_counter()
                clause_vectors = await self.pipeline.embedder.embed_texts(
                    unembedded_texts, task_type="RETRIEVAL_DOCUMENT"
                )
                stage_embedding = time.perf_counter() - t_emb_0

            clause_vector_map = {
                str(c.id): clause_vectors[i]
                for i, c in enumerate(unembedded_clauses)
                if i < len(clause_vectors)
            }

            # Separate already-analyzed from unanalyzed clauses for clean resume & batching
            settings = get_settings()
            clause_analyses_dicts: list[dict[str, Any]] = []
            unanalyzed_clauses: list[Clause] = []

            for clause in clauses:
                clause_id_str = str(clause.id)
                if clause_id_str in analyzed_clause_map:
                    prev_analysis = analyzed_clause_map[clause_id_str]
                    raw_resp = prev_analysis.raw_llm_response or {
                        "risk_level": prev_analysis.risk_category,
                        "risk_score": prev_analysis.risk_score,
                        "plain_english": prev_analysis.plain_english_summary,
                        "risk_reasons": prev_analysis.risk_reasons or [],
                        "missing_protections": prev_analysis.missing_protections or [],
                    }
                    clause_analyses_dicts.append(raw_resp)
                else:
                    unanalyzed_clauses.append(clause)

            # Analyze unanalyzed clauses using configurable batch size with bounded concurrency & streaming commits
            stage_llm_batches = 0.0
            if unanalyzed_clauses:
                batch_inputs = [
                    {
                        "clause_id": str(c.id),
                        "clause_text": c.content,
                        "clause_vector": clause_vector_map.get(str(c.id)),
                    }
                    for c in unanalyzed_clauses
                ]

                db_lock = asyncio.Lock()
                committed_clause_ids: set[str] = set()

                async def on_batch_completed(batch_items: list[tuple[int, dict[str, Any]]]) -> None:
                    async with db_lock:
                        for orig_idx, result_dict in batch_items:
                            clause = unanalyzed_clauses[orig_idx]
                            c_id_str = str(clause.id)
                            if c_id_str in committed_clause_ids:
                                continue
                            committed_clause_ids.add(c_id_str)

                            plain_eng = result_dict.get("plain_english") or result_dict.get(
                                "plain_english_summary", ""
                            )
                            risk_lvl = result_dict.get("risk_level") or result_dict.get(
                                "risk_category", "LOW"
                            )
                            conf = (
                                result_dict.get("confidence")
                                if "confidence" in result_dict
                                else result_dict.get("confidence_score", 0.0)
                            )
                            concern = result_dict.get("legal_review_note") or result_dict.get(
                                "potential_legal_concern"
                            )
                            refs = result_dict.get("retrieved_references") or result_dict.get(
                                "retrieved_clauses", []
                            )

                            track_clause_risk(str(risk_lvl))

                            analysis_result = AnalysisResult(
                                clause_id=clause.id,
                                document_id=document.id,
                                plain_english_summary=plain_eng,
                                risk_score=result_dict.get("risk_score", 0),
                                risk_category=risk_lvl,
                                risk_reasons=result_dict.get("risk_reasons", []),
                                missing_protections=result_dict.get("missing_protections", []),
                                suggested_rewrite=result_dict.get("suggested_rewrite"),
                                potential_legal_concern=concern,
                                confidence_score=conf,
                                raw_llm_response=result_dict.get("raw_llm_response", result_dict),
                                retrieved_clauses=refs,
                            )
                            self.session.add(analysis_result)
                            clause_analyses_dicts.append(result_dict)

                        await self.session.commit()
                        logger.info(
                            "committed_analysis_batch",
                            document_id=str(document_id),
                            batch_committed=len(batch_items),
                            total_committed=len(committed_clause_ids),
                        )

                t_batches_0 = time.perf_counter()
                batch_results = await self.pipeline.analyze_clauses_batch(
                    clauses=batch_inputs,
                    document_type=document.document_type,
                    jurisdiction=document.jurisdiction,
                    batch_size=settings.gemini_analysis_batch_size,
                    max_concurrency=3,
                    on_batch_complete=on_batch_completed,
                )
                stage_llm_batches = time.perf_counter() - t_batches_0

                # Fallback: commit any remaining clause that wasn't committed via callback
                async with db_lock:
                    uncommitted_count = 0
                    for clause, result_dict in zip(unanalyzed_clauses, batch_results, strict=False):
                        c_id_str = str(clause.id)
                        if c_id_str in committed_clause_ids:
                            continue
                        committed_clause_ids.add(c_id_str)
                        plain_eng = result_dict.get("plain_english") or result_dict.get(
                            "plain_english_summary", ""
                        )
                        risk_lvl = result_dict.get("risk_level") or result_dict.get(
                            "risk_category", "LOW"
                        )
                        conf = (
                            result_dict.get("confidence")
                            if "confidence" in result_dict
                            else result_dict.get("confidence_score", 0.0)
                        )
                        concern = result_dict.get("legal_review_note") or result_dict.get(
                            "potential_legal_concern"
                        )
                        refs = result_dict.get("retrieved_references") or result_dict.get(
                            "retrieved_clauses", []
                        )

                        track_clause_risk(str(risk_lvl))

                        analysis_result = AnalysisResult(
                            clause_id=clause.id,
                            document_id=document.id,
                            plain_english_summary=plain_eng,
                            risk_score=result_dict.get("risk_score", 0),
                            risk_category=risk_lvl,
                            risk_reasons=result_dict.get("risk_reasons", []),
                            missing_protections=result_dict.get("missing_protections", []),
                            suggested_rewrite=result_dict.get("suggested_rewrite"),
                            potential_legal_concern=concern,
                            confidence_score=conf,
                            raw_llm_response=result_dict.get("raw_llm_response", result_dict),
                            retrieved_clauses=refs,
                        )
                        self.session.add(analysis_result)
                        clause_analyses_dicts.append(result_dict)
                        uncommitted_count += 1

                    if uncommitted_count > 0:
                        await self.session.commit()

            # Generate overall document summary using configured summary model
            t_sum_0 = time.perf_counter()
            doc_summary_dict = await self.pipeline.generate_document_summary(
                document_type=document.document_type,
                jurisdiction=document.jurisdiction,
                clause_analyses=clause_analyses_dicts,
            )
            stage_summary = time.perf_counter() - t_sum_0

            # Create or update DocumentAnalysis record
            existing_doc_analysis = await self.doc_analysis_repo.get_by_document(document.id)
            if existing_doc_analysis:
                existing_doc_analysis.overall_risk_score = doc_summary_dict["overall_risk_score"]
                existing_doc_analysis.overall_summary = doc_summary_dict["overall_summary"]
                existing_doc_analysis.risk_distribution = doc_summary_dict["risk_distribution"]
                existing_doc_analysis.recommendations = doc_summary_dict["recommendations"]
            else:
                doc_analysis = DocumentAnalysis(
                    document_id=document.id,
                    overall_risk_score=doc_summary_dict["overall_risk_score"],
                    overall_summary=doc_summary_dict["overall_summary"],
                    risk_distribution=doc_summary_dict["risk_distribution"],
                    recommendations=doc_summary_dict["recommendations"],
                )
                self.session.add(doc_analysis)

            # Final telemetry collation (Rule 6: NO sensitive document text is logged)
            batch_telemetry = getattr(self.pipeline, "last_batch_telemetry", [])
            summary_telemetry = getattr(self.pipeline, "last_summary_telemetry", {})
            stage_retrieval = sum(b.get("retrieval_seconds", 0.0) for b in batch_telemetry)
            total_limiter_wait = (
                sum(b.get("rate_limiter_wait_seconds", 0.0) for b in batch_telemetry)
                + summary_telemetry.get("rate_limiter_wait", 0.0)
            )
            total_time = time.perf_counter() - job_start_time

            timing_summary = {
                "stage_upload_seconds": round(stage_upload, 3),
                "stage_extraction_seconds": round(stage_extraction, 3),
                "stage_segmentation_seconds": round(stage_segmentation, 3),
                "stage_embedding_seconds": round(stage_embedding, 3),
                "stage_retrieval_seconds": round(stage_retrieval, 3),
                "stage_llm_batches_seconds": round(stage_llm_batches, 3),
                "stage_summary_seconds": round(stage_summary, 3),
                "total_time_seconds": round(total_time, 3),
                "total_rate_limiter_wait_seconds": round(total_limiter_wait, 3),
                "batch_calls_count": len(batch_telemetry),
            }

            logger.info(
                "analysis_job_stage_timing",
                document_id=str(document_id),
                clause_count=len(clauses),
                **timing_summary,
                llm_batches=batch_telemetry,
                final_summary=summary_telemetry,
            )

            # Store timing metadata on document record
            doc_for_meta = await self.document_repo.get_by_id(document_id)
            if doc_for_meta:
                meta = doc_for_meta.metadata_ or {}
                meta["stage_timing"] = {
                    **timing_summary,
                    "llm_batches": batch_telemetry,
                    "final_summary": summary_telemetry,
                }
                doc_for_meta.metadata_ = meta

            # Finalize
            await self.document_repo.update_status(document_id, "completed")
            await self.session.commit()

            logger.info("analysis_task_completed", document_id=str(document_id))

        except DailyQuotaExceededError as quota_err:
            logger.warning(
                "analysis_task_paused_daily_quota_exceeded",
                document_id=str(document_id),
                notice=str(quota_err),
            )
            try:
                await self.document_repo.update_status(document_id, "waiting for quota")
                doc = await self.document_repo.get_by_id(document_id)
                if doc:
                    if doc.metadata_ is None:
                        doc.metadata_ = {}
                    doc.metadata_["quota_notice"] = str(quota_err)
                await self.session.commit()
            except Exception as quota_update_err:
                logger.error("failed_to_update_quota_notice", error=str(quota_update_err))

        except Exception as e:
            logger.error("analysis_task_fatal_error", document_id=str(document_id), error=str(e))
            try:
                await self.session.rollback()
                await self.document_repo.update_status(document_id, "failed")
                await self.session.commit()
            except Exception as rollback_err:
                logger.error("analysis_task_rollback_failed", error=str(rollback_err))

    def trigger_analysis(self, document_id: UUID) -> None:
        """
        Trigger analysis for a document in the background.

        Note: In FastAPI, it's better to use BackgroundTasks. We provide this
        for flexibility, but the endpoint should ideally inject BackgroundTasks
        and pass `self._run_analysis_task(document_id)`.
        """
        # Create an independent async task
        # Warning: Using the same session in a background task while the main request
        # finishes can cause DetachedInstanceError. The background task needs its own session.
        # This is handled correctly in the router using BackgroundTasks and a new session factory.
        pass

    async def get_document_analysis(self, document_id: UUID) -> DocumentAnalysis:
        """Get the overall analysis summary for a document."""
        analysis = await self.doc_analysis_repo.get_by_document(document_id)
        if not analysis:
            raise NotFoundError("DocumentAnalysis", str(document_id))
        return analysis

    async def get_clause_analyses(self, document_id: UUID) -> Sequence[AnalysisResult]:
        """Get all individual clause analyses for a document."""
        return await self.analysis_repo.get_by_document(document_id)
