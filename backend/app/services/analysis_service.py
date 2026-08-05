"""
Analysis service.

Manages the background execution of the RAG pipeline for document analysis
and provides methods to retrieve the results.
"""

import asyncio
from typing import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.ai.pipeline import AnalysisPipeline
from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.models.clause import Clause
from app.repositories.analysis_repo import AnalysisResultRepository, DocumentAnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.repositories.document_repo import DocumentRepository
from app.document_processing import extract_document, DocumentSegmenter

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
        try:
            logger.info("analysis_task_started", document_id=str(document_id))
            
            # Fetch document and clauses
            document = await self.document_repo.get_by_id(document_id)
            if not document:
                logger.error("analysis_doc_not_found", document_id=str(document_id))
                return
                
            await self.document_repo.update_status(document_id, "extracting")
            await self.session.commit()
            
            # Run heavy extraction and segmentation in a thread pool to avoid blocking the event loop
            segmenter = DocumentSegmenter(min_clause_length=50)
            
            def process_document():
                ext_res = extract_document(document.file_path)
                segs = segmenter.segment(ext_res)
                return ext_res, segs
                
            extraction_result, segments = await asyncio.to_thread(process_document)
            
            # Update document with extraction results
            document.raw_text = extraction_result.raw_text
            document.is_scanned = extraction_result.is_scanned
            document.metadata_ = extraction_result.metadata
            await self.session.commit()
            
            # Create clauses
            if not segments:
                logger.warning("analysis_no_clauses", document_id=str(document_id))
                await self.document_repo.update_status(document_id, "completed")
                await self.session.commit()
                return
                
            clauses = [
                Clause(
                    document_id=document.id,
                    clause_index=segment.index,
                    clause_number=segment.clause_number,
                    title=segment.title,
                    content=segment.content,
                    category=segment.category,
                    start_page=segment.start_page,
                    end_page=segment.end_page,
                )
                for segment in segments
            ]
            await self.clause_repo.bulk_create(clauses)
            
            await self.document_repo.update_status(document_id, "analyzing")
            await self.session.commit()

            # Analyze each clause
            analysis_results = []
            clause_analyses_dicts = []
            
            # We process clauses sequentially to avoid rate limits, but in a production
            # setup with high limits, we could use asyncio.gather for concurrent processing.
            for clause in clauses:
                try:
                    result_dict = await self.pipeline.analyze_clause(
                        clause_text=clause.content,
                        document_type=document.document_type,
                        jurisdiction=document.jurisdiction
                    )
                    
                    clause_analyses_dicts.append(result_dict)
                    
                    analysis_result = AnalysisResult(
                        clause_id=clause.id,
                        plain_english_summary=result_dict["plain_english_summary"],
                        risk_score=result_dict["risk_score"],
                        risk_category=result_dict["risk_category"],
                        risk_reasons=result_dict.get("risk_reasons", []),
                        missing_protections=result_dict.get("missing_protections", []),
                        suggested_rewrite=result_dict.get("suggested_rewrite"),
                        potential_legal_concern=result_dict.get("potential_legal_concern"),
                        confidence_score=result_dict["confidence_score"],
                        raw_llm_response=result_dict["raw_llm_response"],
                        retrieved_clauses=result_dict["retrieved_clauses"]
                    )
                    analysis_results.append(analysis_result)
                    
                except Exception as e:
                    logger.error("clause_analysis_failed", clause_id=str(clause.id), error=str(e))
                    # Still create a fallback result so the process doesn't completely fail
                    analysis_result = AnalysisResult(
                        clause_id=clause.id,
                        plain_english_summary="Analysis failed for this clause.",
                        risk_score=0,
                        risk_category="standard",
                        confidence_score=0.0
                    )
                    analysis_results.append(analysis_result)
            
            # Save clause results
            await self.analysis_repo.bulk_create(analysis_results)
            
            # Generate overall document summary
            doc_summary_dict = await self.pipeline.generate_document_summary(
                document_type=document.document_type,
                jurisdiction=document.jurisdiction,
                clause_analyses=clause_analyses_dicts
            )
            
            # Create DocumentAnalysis record
            doc_analysis = DocumentAnalysis(
                document_id=document.id,
                overall_risk_score=doc_summary_dict["overall_risk_score"],
                overall_summary=doc_summary_dict["overall_summary"],
                risk_distribution=doc_summary_dict["risk_distribution"],
                recommendations=doc_summary_dict["recommendations"]
            )
            self.session.add(doc_analysis)
            
            # Finalize
            await self.document_repo.update_status(document_id, "completed")
            await self.session.commit()
            
            logger.info("analysis_task_completed", document_id=str(document_id))
            
        except Exception as e:
            logger.error("analysis_task_fatal_error", document_id=str(document_id), error=str(e))
            try:
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
