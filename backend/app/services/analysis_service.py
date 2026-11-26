"""
Analysis service.

Manages the background execution of the RAG pipeline for document analysis
and provides methods to retrieve the results.
"""

import asyncio
import math
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ledger import get_call_ledger, set_call_context
from app.ai.pipeline import AnalysisPipeline
from app.ai.rate_limiter import (
    DailyQuotaExceededError,
    UserQuotaExceededError,
    get_user_quota_limiter,
)
from app.config import get_settings
from app.core.cancellation import (
    acknowledge_cancelled,
    check_not_cancelled,
    is_cancelled,
)
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.metrics import track_clause_risk
from app.core.sse import broadcast_event
from app.document_processing import DocumentSegmenter, extract_document
from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.models.clause import Clause
from app.models.document import Document
from app.models.job import Job
from app.repositories.analysis_repo import AnalysisResultRepository, DocumentAnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.job_repo import JobRepository

logger = get_logger(__name__)


class AnalysisService:
    """Service for running and managing document analysis tasks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.analysis_repo = AnalysisResultRepository(session)
        self.doc_analysis_repo = DocumentAnalysisRepository(session)
        self.job_repo = JobRepository(session)
        self.pipeline = AnalysisPipeline()
        settings = get_settings()
        if settings.use_latency_fake and settings.app_env == "test":
            from app.ai.latency_fake import (
                LatencySimulatingFakeEmbedder,
                LatencySimulatingFakeLLM,
            )

            fake_llm = LatencySimulatingFakeLLM(
                model_name=settings.gemini_clause_model,
                sleep_range=(
                    settings.latency_fake_min_seconds,
                    settings.latency_fake_max_seconds,
                ),
            )
            fake_embedder = LatencySimulatingFakeEmbedder(sleep_range=(0.05, 0.1))
            self.pipeline.clause_llm = fake_llm
            self.pipeline.summary_llm = fake_llm
            self.pipeline.embedder = fake_embedder
            self.pipeline.retrieval_service.embedder = fake_embedder

    async def _run_analysis_task(self, document_id: UUID, job_id: UUID | None = None) -> None:
        """
        Background task to run the full RAG analysis pipeline on a document.
        Enforces persistent Job state tracking and cooperative cancellation at every step.
        """
        job_start_time = time.perf_counter()
        active_job_id: UUID | None = job_id
        doc_user_id: UUID | None = None
        try:
            logger.info(
                "analysis_task_started",
                document_id=str(document_id),
                job_id=str(job_id) if job_id else None,
            )

            # Resolve or create Job row for durable tracking
            active_job: Job | None = None
            if job_id is not None:
                active_job = await self.job_repo.get_by_id(job_id)
            if active_job is None:
                active_job = await self.job_repo.get_latest_for_document(document_id)

            # Fetch document
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                logger.error("analysis_doc_not_found", document_id=str(document_id))
                return

            doc_user_id = cast(UUID | None, document.user_id)
            doc_type_str = document.document_type
            doc_jurisdiction_str = document.jurisdiction

            if active_job is None:
                active_job = Job(
                    document_id=document_id,
                    user_id=doc_user_id,
                    status="running",
                    stage="extracting",
                    started_at=datetime.now(UTC).replace(tzinfo=None),
                )
                self.session.add(active_job)
                await self.session.flush()
            else:
                if active_job.cancel_requested or active_job.status in ("cancelling", "cancelled"):
                    active_job_id = active_job.id
                    raise asyncio.CancelledError("Job already cancelled before start.")
                active_job.status = "running"
                active_job.stage = "extracting"
                if active_job.started_at is None:
                    active_job.started_at = datetime.now(UTC).replace(tzinfo=None)

            active_job_id = active_job.id

            # Establish call context for Call Ledger + Cancellation tracing across all outbound calls
            set_call_context(
                job_id=str(active_job_id),
                document_id=str(document_id),
                user_id=str(doc_user_id) if doc_user_id else None,
            )

            await check_not_cancelled(
                document_id=document_id, job_id=active_job_id, user_id=doc_user_id
            )

            if document.status == "completed":
                logger.info("analysis_task_already_completed", document_id=str(document_id))
                await self.session.execute(
                    update(Job)
                    .where(Job.id == active_job_id)
                    .values(
                        status="completed",
                        stage="completed",
                        completed_at=datetime.now(UTC).replace(tzinfo=None),
                    )
                )
                await self.session.commit()
                return

            # Resolve document file path robustly (handling relative/absolute paths across root and backend cwd)
            resolved_file_path = Path(document.file_path)
            if not resolved_file_path.exists():
                settings = get_settings()
                cand1 = settings.upload_path / str(document.user_id) / document.filename
                cand2 = Path("backend") / resolved_file_path
                cand3 = Path.cwd() / resolved_file_path
                if cand1.exists():
                    resolved_file_path = cand1
                elif cand2.exists():
                    resolved_file_path = cand2
                elif cand3.exists():
                    resolved_file_path = cand3

            if resolved_file_path.exists():
                document.file_path = str(resolved_file_path.resolve())

            # Measure upload stage duration
            stage_upload = 0.0
            if document.metadata_ and "upload_duration_seconds" in document.metadata_:
                stage_upload = float(document.metadata_["upload_duration_seconds"])
            else:
                t_stat_0 = time.perf_counter()
                if resolved_file_path.exists():
                    _ = resolved_file_path.stat().st_size
                stage_upload = time.perf_counter() - t_stat_0

            await self.document_repo.update_status(document_id, "extracting")
            await self.session.commit()
            broadcast_event(
                str(document_id),
                "status",
                {
                    "status": "extracting",
                    "job_status": "running",
                    "stage": "extracting",
                    "total_clauses": 0,
                    "analyzed_clauses": 0,
                },
            )

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
            # Measure extraction and segmentation in separate stages
            segmenter = DocumentSegmenter(min_clause_length=50)

            t_ext_0 = time.perf_counter()
            extraction_result = await asyncio.to_thread(extract_document, str(resolved_file_path))
            stage_extraction = time.perf_counter() - t_ext_0

            # Update document with extracted text prior to intake classification
            doc_obj = await self.document_repo.get_by_id(document_id)
            if doc_obj:
                doc_obj.raw_text = extraction_result.raw_text
                doc_obj.is_scanned = extraction_result.is_scanned
                existing_meta = doc_obj.metadata_ or {}
                if extraction_result.metadata:
                    existing_meta.update(extraction_result.metadata)
                doc_obj.metadata_ = existing_meta
            else:
                existing_meta = {}

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
            await self.session.execute(
                update(Job).where(Job.id == active_job_id).values(stage="classifying")
            )
            await self.session.commit()
            broadcast_event(
                str(document_id),
                "status",
                {
                    "status": "extracting",
                    "job_status": "running",
                    "stage": "classifying",
                    "total_clauses": 0,
                    "analyzed_clauses": 0,
                },
            )
            # Pre-analysis legal classification check BEFORE clause segmentation & scoring:
            # Prevents hallucinating contract risk scores on non-legal documents (e.g. setup guides).
            classification = await self.pipeline.classify_document_type(
                raw_text=extraction_result.raw_text,
                declared_type=doc_type_str,
            )

            if not classification.is_legal_document:
                logger.info(
                    "document_classified_as_non_legal",
                    document_id=str(document_id),
                    detected_type=classification.document_type_detected,
                    reason=classification.reason,
                )
                doc_non_legal = await self.document_repo.get_by_id(document_id)
                if doc_non_legal:
                    doc_non_legal.document_type = "non_legal"
                    existing_meta["detected_document_type"] = classification.document_type_detected
                    existing_meta["classification_reason"] = classification.reason
                    existing_meta["is_legal_document"] = False
                    doc_non_legal.metadata_ = existing_meta

                non_legal_summary = DocumentAnalysis(
                    document_id=document_id,
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
                await check_not_cancelled(document_id=document_id, job_id=active_job_id)
                self.session.add(non_legal_summary)
                await self.session.execute(
                    update(Job)
                    .where(Job.id == active_job_id)
                    .values(
                        status="completed",
                        stage="completed",
                        completed_at=datetime.now(UTC).replace(tzinfo=None),
                    )
                )
                await self.document_repo.update_status(document_id, "completed")
                await self.session.commit()
                broadcast_event(
                    str(document_id),
                    "completed",
                    {"overall_risk_score": None, "is_provisional": False, "is_legal": False},
                )
                return

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
            await self.session.execute(
                update(Job).where(Job.id == active_job_id).values(stage="segmenting")
            )
            await self.session.commit()
            broadcast_event(
                str(document_id),
                "status",
                {
                    "status": "segmenting",
                    "job_status": "running",
                    "stage": "segmenting",
                    "total_clauses": 0,
                    "analyzed_clauses": 0,
                },
            )
            t_seg_0 = time.perf_counter()
            segments = await asyncio.to_thread(segmenter.segment, extraction_result)
            stage_segmentation = time.perf_counter() - t_seg_0

            await self.session.commit()

            # Create clauses
            if not segments:
                logger.warning("analysis_no_clauses", document_id=str(document_id))
                await self.session.execute(
                    update(Job)
                    .where(Job.id == active_job_id)
                    .values(
                        status="failed",
                        stage="failed",
                        error_message="No clauses extracted from document.",
                        completed_at=datetime.now(UTC).replace(tzinfo=None),
                    )
                )
                await self.document_repo.update_status(document_id, "failed")
                await self.session.commit()
                return

            # Configure per-document call budget (2.5x expected calls for configured batch size)
            settings = get_settings()
            ledger = get_call_ledger()
            doc_budget = ledger.calculate_document_budget(
                len(segments),
                multiplier=2.5,
                batch_size=settings.gemini_analysis_batch_size,
            )
            ledger.set_document_budget(str(document_id), doc_budget)
            logger.info(
                "analysis_doc_call_budget_configured",
                document_id=str(document_id),
                clause_count=len(segments),
                budget=doc_budget,
            )

            # Check per-user quota
            user_quota = get_user_quota_limiter()
            user_id_str = str(doc_user_id) if doc_user_id else ""
            try:
                await user_quota.check_and_increment(
                    user_id=user_id_str, clause_count=len(segments)
                )
            except UserQuotaExceededError as q_err:
                logger.warning(
                    "user_quota_exceeded", document_id=str(document_id), error=str(q_err)
                )
                await self.session.execute(
                    update(Job)
                    .where(Job.id == active_job_id)
                    .values(
                        status="failed",
                        stage="failed",
                        error_message=str(q_err),
                        completed_at=datetime.now(UTC).replace(tzinfo=None),
                    )
                )
                await self.document_repo.update_status(document_id, "failed")
                await self.session.commit()
                return

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
            # If clauses were already created in a previous attempt, reuse them for clean resume
            existing_clauses = await self.clause_repo.get_by_document(document_id)
            if existing_clauses:
                clauses = list(existing_clauses)
            else:
                clauses = [
                    Clause(
                        document_id=document_id,
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

            total_clauses_count = len(clauses)
            await self.session.execute(
                update(Job)
                .where(Job.id == active_job_id)
                .values(total_clauses=total_clauses_count, stage="embedding")
            )
            await self.document_repo.update_status(document_id, "analyzing")
            await self.session.commit()

            # Clean job resume: check which clauses are already analyzed
            existing_analyses = await self.analysis_repo.get_by_document(document_id)
            analyzed_clause_map: dict[str, Any] = {str(a.clause_id): a for a in existing_analyses}
            existing_analyses_count = len(existing_analyses)
            broadcast_event(
                str(document_id),
                "status",
                {
                    "status": "analyzing",
                    "job_status": "running",
                    "stage": "analyzing",
                    "total_clauses": total_clauses_count,
                    "analyzed_clauses": existing_analyses_count,
                },
            )

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
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
                    raw_resp = dict(
                        prev_analysis.raw_llm_response
                        or {
                            "risk_level": prev_analysis.risk_category,
                            "risk_score": prev_analysis.risk_score,
                            "plain_english": prev_analysis.plain_english_summary,
                            "risk_reasons": prev_analysis.risk_reasons or [],
                            "missing_protections": prev_analysis.missing_protections or [],
                        }
                    )
                    if "retrieved_references" not in raw_resp and prev_analysis.retrieved_clauses:
                        raw_resp["retrieved_references"] = prev_analysis.retrieved_clauses
                    clause_analyses_dicts.append(raw_resp)
                else:
                    unanalyzed_clauses.append(clause)

            # Analyze unanalyzed clauses using configurable batch size with bounded concurrency & streaming commits
            stage_llm_batches = 0.0
            if unanalyzed_clauses:
                unanalyzed_clause_ids = [c.id for c in unanalyzed_clauses]
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
                        # Check cancel flag and verify document still exists BEFORE writing any rows
                        if await is_cancelled(
                            document_id=document_id,
                            job_id=active_job_id,
                            user_id=doc_user_id,
                        ):
                            raise asyncio.CancelledError("Job cancelled before committing batch.")

                        doc_exists_res = await self.session.execute(
                            select(Document.id).where(Document.id == document_id)
                        )
                        if doc_exists_res.scalar_one_or_none() is None:
                            logger.info(
                                "document_deleted_during_analysis_aborting",
                                document_id=str(document_id),
                            )
                            raise asyncio.CancelledError("Document was deleted during analysis.")

                        for orig_idx, result_dict in batch_items:
                            clause_uuid = unanalyzed_clause_ids[orig_idx]
                            c_id_str = str(clause_uuid)
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
                                clause_id=clause_uuid,
                                document_id=document_id,
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

                        completed_total = min(
                            total_clauses_count,
                            existing_analyses_count + len(committed_clause_ids),
                        )
                        await self.session.execute(
                            update(Job)
                            .where(Job.id == active_job_id)
                            .values(
                                stage="analyzing",
                                completed_clauses=completed_total,
                            )
                        )
                        await self.session.commit()
                        logger.info(
                            "committed_analysis_batch",
                            document_id=str(document_id),
                            batch_committed=len(batch_items),
                            total_committed=completed_total,
                        )
                        broadcast_event(
                            str(document_id),
                            "batch_completed",
                            {
                                "batch_committed": len(batch_items),
                                "total_committed": completed_total,
                                "total_clauses": total_clauses_count,
                                "status": "analyzing",
                                "job_status": "running",
                                "stage": "analyzing",
                            },
                        )

                t_batches_0 = time.perf_counter()
                batch_results = await self.pipeline.analyze_clauses_batch(
                    clauses=batch_inputs,
                    document_type=doc_type_str,
                    jurisdiction=doc_jurisdiction_str,
                    batch_size=settings.gemini_analysis_batch_size,
                    max_concurrency=3,
                    on_batch_complete=on_batch_completed,
                )
                stage_llm_batches = time.perf_counter() - t_batches_0

                # Fallback: commit any remaining clause that wasn't committed via callback
                async with db_lock:
                    await check_not_cancelled(document_id=document_id, job_id=active_job_id)
                    uncommitted_count = 0
                    for clause_uuid, result_dict in zip(
                        unanalyzed_clause_ids, batch_results, strict=False
                    ):
                        c_id_str = str(clause_uuid)
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
                            clause_id=clause_uuid,
                            document_id=document_id,
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

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
            await self.session.execute(
                update(Job).where(Job.id == active_job_id).values(stage="scoring")
            )

            # Immediate overall score computation from clause results (Part B.5)
            scores = [
                c.get("risk_score", 0)
                for c in clause_analyses_dicts
                if isinstance(c.get("risk_score"), (int, float))
            ]
            provisional_score = round(sum(scores) / len(scores)) if scores else 0
            overall_lvl = "LOW"
            if (
                any(c.get("risk_level") == "CRITICAL" for c in clause_analyses_dicts)
                or provisional_score >= 70
            ):
                overall_lvl = "CRITICAL"
            elif (
                any(c.get("risk_level") == "HIGH" for c in clause_analyses_dicts)
                or provisional_score >= 45
            ):
                overall_lvl = "HIGH"
            elif (
                any(c.get("risk_level") == "MEDIUM" for c in clause_analyses_dicts)
                or provisional_score >= 25
            ):
                overall_lvl = "MEDIUM"

            # Persist immediate provisional score to database before generating text summary
            existing_doc_analysis = await self.doc_analysis_repo.get_by_document(document_id)
            if existing_doc_analysis:
                existing_doc_analysis.overall_risk_score = provisional_score
            else:
                doc_analysis = DocumentAnalysis(
                    document_id=document_id,
                    overall_risk_score=provisional_score,
                    overall_summary="Analysis scoring complete. Finalizing summary...",
                    risk_distribution={},
                    recommendations=[],
                )
                self.session.add(doc_analysis)
            await self.session.commit()

            broadcast_event(
                str(document_id),
                "score_computed",
                {
                    "overall_risk_score": provisional_score,
                    "overall_risk_level": overall_lvl,
                    "is_provisional": True,
                },
            )

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)
            await self.session.execute(
                update(Job).where(Job.id == active_job_id).values(stage="summarizing")
            )
            await self.session.commit()

            # Generate overall document summary text afterward using configured summary model
            t_sum_0 = time.perf_counter()
            doc_summary_dict = await self.pipeline.generate_document_summary(
                document_type=doc_type_str,
                jurisdiction=doc_jurisdiction_str,
                clause_analyses=clause_analyses_dicts,
            )
            stage_summary = time.perf_counter() - t_sum_0

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)

            # Update DocumentAnalysis record with final executive synthesis
            existing_doc_analysis = await self.doc_analysis_repo.get_by_document(document_id)
            if existing_doc_analysis:
                existing_doc_analysis.overall_risk_score = doc_summary_dict["overall_risk_score"]
                existing_doc_analysis.overall_summary = doc_summary_dict["overall_summary"]
                existing_doc_analysis.risk_distribution = doc_summary_dict["risk_distribution"]
                existing_doc_analysis.recommendations = doc_summary_dict["recommendations"]
            else:
                doc_analysis = DocumentAnalysis(
                    document_id=document_id,
                    overall_risk_score=doc_summary_dict["overall_risk_score"],
                    overall_summary=doc_summary_dict["overall_summary"],
                    risk_distribution=doc_summary_dict["risk_distribution"],
                    recommendations=doc_summary_dict["recommendations"],
                )
                self.session.add(doc_analysis)
            await self.session.commit()

            broadcast_event(
                str(document_id),
                "completed",
                {
                    "overall_risk_score": doc_summary_dict["overall_risk_score"],
                    "is_provisional": False,
                },
            )

            # Final telemetry collation (Rule 6: NO sensitive document text is logged)
            batch_telemetry = getattr(self.pipeline, "last_batch_telemetry", [])
            summary_telemetry = getattr(self.pipeline, "last_summary_telemetry", {})
            stage_retrieval = sum(b.get("retrieval_seconds", 0.0) for b in batch_telemetry)
            total_limiter_wait = sum(
                b.get("rate_limiter_wait_seconds", 0.0) for b in batch_telemetry
            ) + summary_telemetry.get("rate_limiter_wait", 0.0)
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
                clause_count=total_clauses_count,
                **timing_summary,
                llm_batches=batch_telemetry,
                final_summary=summary_telemetry,
            )

            # Call ledger post-job telemetry summary (Part A.2 & Part B.1)
            ledger = get_call_ledger()
            ledger_summary = ledger.log_job_summary(
                document_id=str(document_id),
                total_time=total_time,
                limiter_wait_time=total_limiter_wait,
            )

            # Expected calls at batch size 4 = ceil(N/4) + 1 summary (Part B.1)
            expected_calls = (
                math.ceil(total_clauses_count / max(1, settings.gemini_analysis_batch_size)) + 1
            )
            actual_calls = ledger_summary.get("total_calls", 0)
            logger.info(
                "analysis_expected_vs_actual_calls",
                document_id=str(document_id),
                expected_calls=expected_calls,
                actual_calls=actual_calls,
                ratio=round(actual_calls / max(1, expected_calls), 2),
            )
            timing_summary["expected_calls"] = expected_calls
            timing_summary["actual_calls"] = actual_calls
            ledger_summary["expected_calls"] = expected_calls
            ledger_summary["actual_calls"] = actual_calls
            ledger_summary["expected_vs_actual"] = (
                f"{actual_calls} actual / {expected_calls} expected"
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
                meta["call_ledger"] = ledger_summary
                doc_for_meta.metadata_ = meta

            await check_not_cancelled(document_id=document_id, job_id=active_job_id)

            # Finalize
            await self.session.execute(
                update(Job)
                .where(Job.id == active_job_id)
                .values(
                    status="completed",
                    stage="completed",
                    completed_clauses=total_clauses_count,
                    completed_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            await self.document_repo.update_status(document_id, "completed")
            await self.session.commit()

            logger.info("analysis_task_completed", document_id=str(document_id))

        except asyncio.CancelledError:
            logger.info("analysis_task_cancelled", document_id=str(document_id))
            try:
                await self.session.rollback()
                if active_job_id is not None:
                    await self.session.execute(
                        update(Job)
                        .where(Job.id == active_job_id)
                        .values(
                            status="cancelled",
                            stage="cancelled",
                            cancel_requested=True,
                            completed_at=datetime.now(UTC).replace(tzinfo=None),
                        )
                    )
                    await self.session.commit()
            except Exception:
                pass
            await acknowledge_cancelled(document_id=document_id, job_id=active_job_id)
            broadcast_event(str(document_id), "cancelled", {"document_id": str(document_id)})
            raise

        except DailyQuotaExceededError as quota_err:
            logger.warning(
                "analysis_task_paused_daily_quota_exceeded",
                document_id=str(document_id),
                notice=str(quota_err),
            )
            try:
                if active_job_id is not None:
                    await self.session.execute(
                        update(Job)
                        .where(Job.id == active_job_id)
                        .values(
                            status="waiting_for_quota",
                            stage="waiting_for_quota",
                            error_message=str(quota_err),
                        )
                    )
                await self.document_repo.update_status(document_id, "waiting for quota")
                doc = await self.document_repo.get_by_id(document_id)
                if doc:
                    if doc.metadata_ is None:
                        doc.metadata_ = {}
                    doc.metadata_["quota_notice"] = str(quota_err)
                await self.session.commit()
                broadcast_event(
                    str(document_id),
                    "waiting_for_quota",
                    {
                        "status": "waiting for quota",
                        "job_status": "waiting_for_quota",
                        "stage": "waiting_for_quota",
                        "message": str(quota_err),
                    },
                )
            except Exception as quota_update_err:
                logger.error("failed_to_update_quota_notice", error=str(quota_update_err))

        except Exception as e:
            logger.error("analysis_task_fatal_error", document_id=str(document_id), error=str(e))
            try:
                await self.session.rollback()
                if active_job_id is not None:
                    await self.session.execute(
                        update(Job)
                        .where(Job.id == active_job_id)
                        .values(
                            status="failed",
                            stage="failed",
                            error_message=str(e)[:1000],
                            completed_at=datetime.now(UTC).replace(tzinfo=None),
                        )
                    )
                await self.document_repo.update_status(document_id, "failed")
                await self.session.commit()
                from app.services.job_service import format_user_failure_message

                broadcast_event(
                    str(document_id),
                    "failed",
                    {
                        "status": "failed",
                        "job_status": "failed",
                        "stage": "failed",
                        "message": format_user_failure_message(str(e), status="failed"),
                    },
                )
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
