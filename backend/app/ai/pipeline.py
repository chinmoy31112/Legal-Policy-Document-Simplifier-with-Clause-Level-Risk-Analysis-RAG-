"""
The Pure AI Reasoning and Risk Analysis Pipeline.

Phase 4 Deliverable:
Pure pipeline: takes clauses and retrieved references, returns validated JSON.
Must not touch: database, HTTP endpoints, auth, frontend.

Adheres to:
- Rule 1: Retrieval before reasoning, explicit no_reference_found flag.
- Rule 2: Grounding (every risk reason must cite clause quote or reference ID).
- Rule 3: Structured output only with Pydantic validation and up to 2 repair retries.
- Rule 4: Honest uncertainty (4 risk levels, indicative scores, no "unenforceable").
- Rule 5: Untrusted data boundaries and prompt-injection defense.
"""

import hashlib
import time
from typing import Any

from app.ai.embedding import GeminiEmbedder
from app.ai.grounding import GroundingValidator
from app.ai.interfaces import Embedder, LLMClient, VectorStore
from app.ai.llm import GeminiLLMClient
from app.ai.prompts import (
    BATCH_CLAUSE_ANALYSIS_PROMPT,
    CLAUSE_ANALYSIS_PROMPT,
    DOCUMENT_AGGREGATION_PROMPT,
    PROMPT_VERSION,
    REPAIR_PROMPT,
    SYSTEM_INSTRUCTION,
)
from app.ai.response_parser import (
    DocumentRiskAnalysis,
    LLMBatchClauseAnalysis,
    LLMClauseAnalysis,
    RiskLevel,
)
from app.ai.retrieval import RetrievalService
from app.ai.vector_store import get_vector_store
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import track_llm_call, track_prompt_injection, track_vector_search

logger = get_logger(__name__)


class RiskAnalysisPipeline:
    """
    Orchestrates the pure AI risk reasoning pipeline:
    Clause -> Retrieval -> Prompt Formatting -> Gemini Structured Reasoning ->
    Grounding Validation -> Schema Validation -> Document Aggregation.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        retrieval_service: RetrievalService | None = None,
        embedder: Embedder | None = None,
        vector_store: VectorStore | None = None,
        grounding_validator: GroundingValidator | None = None,
        clause_model: str | None = None,
        summary_model: str | None = None,
    ):
        self.settings = get_settings()
        self.embedder = embedder or GeminiEmbedder()
        self.vector_store = vector_store or get_vector_store()
        self.retrieval_service = retrieval_service or RetrievalService(
            embedder=self.embedder,
            vector_store=self.vector_store,
        )
        self.clause_model_name = clause_model or self.settings.gemini_clause_model
        self.summary_model_name = summary_model or self.settings.gemini_summary_model

        if llm_client is not None:
            self.clause_llm = llm_client
            self.summary_llm = llm_client
        else:
            self.clause_llm = GeminiLLMClient(model_name=self.clause_model_name)
            self.summary_llm = GeminiLLMClient(model_name=self.summary_model_name)

        self.llm_client = self.clause_llm  # backward compatibility alias
        self.grounding_validator = grounding_validator or GroundingValidator(min_precision=0.90)
        self._clause_cache: dict[str, dict[str, Any]] = {}

    def _cache_key(self, clause_text: str, model_name: str) -> str:
        """Composite cache key: clause hash + prompt version + resolved model version."""
        normalized = " ".join(clause_text.split())
        clause_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return f"{clause_hash}:{PROMPT_VERSION}:{model_name}"

    async def analyze_clause(
        self,
        clause_text: str,
        document_type: str = "general_contract",
        jurisdiction: str | None = None,
        clause_id: str | None = None,
        clause_vector: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a single clause adhering to Rules 1, 2, 3, 4, 5.

        Steps:
        1. Check hash-based result cache (clause hash + prompt version + model name).
        2. Retrieval before reasoning (Rule 1). Reuses pre-computed clause_vector if provided.
        3. Prompt formatting with untrusted delimiters (Rule 5).
        4. Structured LLM reasoning with repair retries (Rule 3).
        5. Grounding validation (Rule 2).
        6. Return validated JSON with runtime statistics.
        """
        model_name = getattr(self.clause_llm, "model_name", self.clause_model_name)
        cache_key = self._cache_key(clause_text, model_name)

        # 0. Check cache
        if cache_key in self._clause_cache:
            cached = dict(self._clause_cache[cache_key])
            cached["clause_id"] = clause_id
            cached["from_cache"] = True
            return cached

        start_time = time.perf_counter()

        # 1. Step 1: Retrieval before reasoning (Rule 1)
        t_ret_0 = time.perf_counter()
        retrieval_resp = await self.retrieval_service.retrieve(
            query_text=clause_text,
            query_vector=clause_vector,
            top_k=self.settings.retrieval_top_k,
        )
        track_vector_search(time.perf_counter() - t_ret_0)

        # Detect adversarial injection patterns for security telemetry
        lowered_clause = clause_text.lower()
        if any(marker in lowered_clause for marker in ["system override", "ignore previous instructions", "disregard all rules", "defense attorney"]):
            track_prompt_injection()

        ref_texts: list[str] = []
        allowed_ref_ids: set[str] = set()

        if retrieval_resp.no_reference_found or not retrieval_resp.results:
            retrieved_context_str = (
                "[NO REFERENCE FOUND: No standard reference clause cleared the similarity threshold. "
                "Assess risk conservatively based on baseline fairness standards and flag higher uncertainty.]"
            )
            no_ref_flag = "true"
        else:
            for idx, r in enumerate(retrieval_resp.results, start=1):
                allowed_ref_ids.add(r.id.upper())
                ref_texts.append(
                    f"[{r.id}] ({r.metadata.get('category', 'Standard')} - {r.metadata.get('title', 'Reference')}):\n"
                    f"{r.metadata.get('text', '')}"
                )
            retrieved_context_str = "\n\n".join(ref_texts)
            no_ref_flag = "false"

        # 2. Step 2: Format prompt with strict security delimiters (Rule 5)
        prompt = CLAUSE_ANALYSIS_PROMPT.format(
            document_type=document_type,
            jurisdiction=jurisdiction or "General",
            clause_text=clause_text,
            retrieved_context=retrieved_context_str,
            no_reference_flag=no_ref_flag,
        )

        # 3. Step 3: Call LLM with structured output and repair retries (Rule 3)
        llm_t0 = time.perf_counter()
        analysis = await self.llm_client.generate_structured(
            prompt=prompt,
            response_model=LLMClauseAnalysis,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        track_llm_call(getattr(self.llm_client, "model_name", "gemini-2.5-flash"), time.perf_counter() - llm_t0)

        # 4. Step 4: Validate grounding citations (Rule 2)
        grounding_result = self.grounding_validator.validate(
            risk_reasons=analysis.risk_reasons,
            clause_text=clause_text,
            allowed_ref_ids=allowed_ref_ids,
        )

        # If grounding precision < 0.90, perform repair attempt
        if not grounding_result.is_valid:
            logger.warning(
                "grounding_validation_failed_repairing",
                precision=grounding_result.grounding_precision,
                ungrounded=grounding_result.ungrounded_reasons,
            )
            repair_prompt = REPAIR_PROMPT.format(
                validation_errors=grounding_result.error_message,
                previous_response=analysis.model_dump_json(),
            )
            analysis = await self.llm_client.generate_structured(
                prompt=repair_prompt,
                response_model=LLMClauseAnalysis,
                system_instruction=SYSTEM_INSTRUCTION,
            )
            # Re-evaluate grounding
            grounding_result = self.grounding_validator.validate(
                risk_reasons=analysis.risk_reasons,
                clause_text=clause_text,
                allowed_ref_ids=allowed_ref_ids,
            )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        output_dict = analysis.model_dump()
        output_dict["clause_id"] = clause_id
        output_dict["runtime_ms"] = elapsed_ms
        output_dict["model_version"] = getattr(self.clause_llm, "last_model_version", None) or model_name
        output_dict["grounding_precision"] = grounding_result.grounding_precision
        output_dict["is_grounded"] = grounding_result.is_valid
        output_dict["retrieved_references"] = [
            {"id": r.id, "score": r.score, "category": r.metadata.get("category")}
            for r in retrieval_resp.results
        ]
        output_dict["no_reference_found"] = retrieval_resp.no_reference_found

        # Cache validated result
        self._clause_cache[cache_key] = dict(output_dict)

        return output_dict

    async def analyze_clauses_batch(
        self,
        clauses: list[dict[str, Any]],
        document_type: str = "general_contract",
        jurisdiction: str | None = None,
        batch_size: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze a list of clauses in batches using Gemini structured output.
        - Checks hash cache (clause_hash + prompt_version + model_name).
        - Partitions uncached clauses into chunks (default size 4).
        - Re-sends only failed or invalid clauses individually.
        """
        effective_batch_size = max(1, batch_size or self.settings.gemini_analysis_batch_size)
        results: list[dict[str, Any] | None] = [None] * len(clauses)
        pending_indices: list[int] = []

        model_name = getattr(self.clause_llm, "model_name", self.clause_model_name)

        # 1. Resolve cached clauses first
        for idx, c in enumerate(clauses):
            c_text = c.get("clause_text", "")
            c_id = c.get("clause_id")
            ckey = self._cache_key(c_text, model_name)
            if ckey in self._clause_cache:
                cached_res = dict(self._clause_cache[ckey])
                cached_res["clause_id"] = c_id
                cached_res["from_cache"] = True
                results[idx] = cached_res
            else:
                pending_indices.append(idx)

        # 2. Process uncached clauses in batches
        for chunk_start in range(0, len(pending_indices), effective_batch_size):
            chunk_indices = pending_indices[chunk_start : chunk_start + effective_batch_size]
            batch_clauses = [clauses[i] for i in chunk_indices]

            # Run retrieval for each clause in the chunk
            batch_retrievals = []
            for c in batch_clauses:
                r_resp = await self.retrieval_service.retrieve(
                    query_text=c["clause_text"],
                    query_vector=c.get("clause_vector"),
                    top_k=self.settings.retrieval_top_k,
                )
                batch_retrievals.append(r_resp)

            batch_items_text = []
            for b_idx, (c, r_resp) in enumerate(zip(batch_clauses, batch_retrievals, strict=False), start=1):
                ref_texts = [
                    f"[{r.id}] ({r.metadata.get('category', 'Standard')} - {r.metadata.get('title', 'Reference')}): {r.metadata.get('text', '')}"
                    for r in r_resp.results
                ]
                ref_context = "\n".join(ref_texts) if ref_texts else "[NO REFERENCE FOUND]"
                batch_items_text.append(
                    f"--- CLAUSE {b_idx} (ID: {c.get('clause_id', f'c_{b_idx}')}) ---\n"
                    f"<<<UNTRUSTED_DOCUMENT_CLAUSE>>>\n{c['clause_text']}\n<<<END_UNTRUSTED_DOCUMENT_CLAUSE>>>\n"
                    f"Retrieved Reference Context:\n{ref_context}\n"
                )

            batch_prompt = BATCH_CLAUSE_ANALYSIS_PROMPT.format(
                document_type=document_type,
                jurisdiction=jurisdiction or "General",
                batch_count=len(batch_clauses),
                batch_clauses_text="\n".join(batch_items_text),
            )

            failed_indices = []
            try:
                batch_res = await self.clause_llm.generate_structured(
                    prompt=batch_prompt,
                    response_model=LLMBatchClauseAnalysis,
                    system_instruction=SYSTEM_INSTRUCTION,
                )
                batch_items = getattr(batch_res, "items", [])

                if len(batch_items) != len(batch_clauses):
                    logger.warning(
                        "batch_clause_count_mismatch",
                        expected=len(batch_clauses),
                        received=len(batch_items),
                    )
                    failed_indices = list(chunk_indices)
                else:
                    for orig_idx, item, r_resp, c in zip(
                        chunk_indices, batch_items, batch_retrievals, batch_clauses, strict=False
                    ):
                        allowed_ref_ids = {r.id.upper() for r in r_resp.results}
                        grounding = self.grounding_validator.validate(
                            risk_reasons=item.risk_reasons,
                            clause_text=c["clause_text"],
                            allowed_ref_ids=allowed_ref_ids,
                        )
                        if not grounding.is_valid:
                            failed_indices.append(orig_idx)
                        else:
                            res_dict = item.model_dump()
                            res_dict["clause_id"] = c.get("clause_id")
                            res_dict["model_version"] = getattr(self.clause_llm, "last_model_version", None) or model_name
                            res_dict["grounding_precision"] = grounding.grounding_precision
                            res_dict["is_grounded"] = True
                            res_dict["retrieved_references"] = [
                                {"id": r.id, "score": r.score, "category": r.metadata.get("category")}
                                for r in r_resp.results
                            ]
                            res_dict["no_reference_found"] = r_resp.no_reference_found
                            # Cache validated result
                            ckey = self._cache_key(c["clause_text"], model_name)
                            self._clause_cache[ckey] = dict(res_dict)
                            results[orig_idx] = res_dict

            except Exception as exc:
                logger.warning("batch_llm_call_failed", error=str(exc))
                failed_indices = list(chunk_indices)

            # Re-send only failed or invalid clauses
            if failed_indices:
                logger.info("resending_failed_or_invalid_clauses", count=len(failed_indices))
                for orig_idx in failed_indices:
                    c = clauses[orig_idx]
                    single_res = await self.analyze_clause(
                        clause_text=c["clause_text"],
                        document_type=document_type,
                        jurisdiction=jurisdiction,
                        clause_id=c.get("clause_id"),
                        clause_vector=c.get("clause_vector"),
                    )
                    results[orig_idx] = single_res

        return [r for r in results if r is not None]

    async def aggregate_document(
        self,
        clause_results: list[dict[str, Any]],
        document_type: str = "general_contract",
        jurisdiction: str | None = None,
    ) -> DocumentRiskAnalysis:
        """
        Synthesize document-level risk assessment from analyzed clauses.
        Computes holistic risk score, executive summary, category breakdown, and negotiation priorities.
        """
        if not clause_results:
            return DocumentRiskAnalysis.model_validate({
                "overall_risk_score": 0,
                "overall_risk_level": "LOW",
                "executive_summary": "No clauses provided for document analysis.",
                "key_risks": [],
                "category_breakdown": {},
                "negotiation_priorities": [],
            })

        # 1. Compute statistical aggregations
        total_clauses = len(clause_results)
        total_score = sum(c.get("risk_score", 0) for c in clause_results)
        avg_score = round(total_score / total_clauses) if total_clauses > 0 else 0

        categories: dict[str, list[int]] = {}
        high_risk_summaries: list[str] = []
        priorities: list[dict[str, Any]] = []

        for c in clause_results:
            score = c.get("risk_score", 0)
            lvl = c.get("risk_level", "LOW")
            cat = c.get("category", "General")
            categories.setdefault(cat, []).append(score)

            if lvl in ("CRITICAL", "HIGH") or score >= 50:
                summary_line = (
                    f"[{lvl} - Score {score}] Clause: {c.get('plain_english', '')[:100]}...\n"
                    f"Reasons: {', '.join(c.get('risk_reasons', []))}"
                )
                high_risk_summaries.append(summary_line)

                if len(priorities) < 5:
                    priorities.append({
                        "clause_id": c.get("clause_id"),
                        "risk_level": lvl,
                        "risk_score": score,
                        "issue": c.get("risk_reasons", ["Asymmetric risk"])[0] if c.get("risk_reasons") else "Asymmetric risk",
                        "suggested_change": c.get("suggested_rewrite") or "Seek mutual reciprocity or eliminate unilateral clause.",
                    })

        # Category breakdown
        breakdown: dict[str, Any] = {}
        for cat, scores in categories.items():
            max_s = max(scores)
            max_lvl: RiskLevel = "CRITICAL" if max_s >= 75 else ("HIGH" if max_s >= 50 else ("MEDIUM" if max_s >= 25 else "LOW"))
            breakdown[cat] = {
                "clause_count": len(scores),
                "avg_score": round(sum(scores) / len(scores)),
                "max_risk_level": max_lvl,
            }

        # Determine overall risk level
        overall_level: RiskLevel = "LOW"
        if any(c.get("risk_level") == "CRITICAL" for c in clause_results) or avg_score >= 70:
            overall_level = "CRITICAL"
        elif any(c.get("risk_level") == "HIGH" for c in clause_results) or avg_score >= 45:
            overall_level = "HIGH"
        elif any(c.get("risk_level") == "MEDIUM" for c in clause_results) or avg_score >= 25:
            overall_level = "MEDIUM"

        # 2. Call LLM for executive synthesis
        prompt = DOCUMENT_AGGREGATION_PROMPT.format(
            document_type=document_type,
            jurisdiction=jurisdiction or "General",
            total_clauses=total_clauses,
            clause_summaries="\n\n".join(high_risk_summaries[:10]) if high_risk_summaries else "All clauses standard.",
        )

        doc_analysis = await self.summary_llm.generate_structured(
            prompt=prompt,
            response_model=DocumentRiskAnalysis,
            system_instruction=SYSTEM_INSTRUCTION,
        )

        # Merge calculated breakdown and priorities with LLM summary
        doc_analysis.overall_risk_score = avg_score
        doc_analysis.overall_risk_level = overall_level
        doc_analysis.category_breakdown = breakdown
        if priorities:
            doc_analysis.negotiation_priorities = priorities

        return doc_analysis

    async def generate_document_summary(
        self,
        document_type: str = "general_contract",
        jurisdiction: str | None = None,
        clause_analyses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Convenience method for generating document summary dictionary."""
        res = await self.aggregate_document(
            clause_results=clause_analyses or [],
            document_type=document_type,
            jurisdiction=jurisdiction,
        )
        return {
            "overall_risk_score": res.overall_risk_score,
            "overall_summary": res.executive_summary,
            "risk_distribution": res.category_breakdown,
            "recommendations": res.key_risks,
            "disclaimer": res.disclaimer,
            "model_version": getattr(self.summary_llm, "last_model_version", None) or self.summary_model_name,
        }


# Backward compatibility alias
AnalysisPipeline = RiskAnalysisPipeline
