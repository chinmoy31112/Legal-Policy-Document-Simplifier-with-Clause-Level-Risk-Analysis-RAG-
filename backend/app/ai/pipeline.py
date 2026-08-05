"""
The RAG Pipeline Orchestrator.

Combines the Embedding, Retrieval, and LLM services to execute the full
clause analysis workflow.
"""

from uuid import UUID

from app.core.exceptions import AIServiceError
from app.core.logging import get_logger
from app.ai.embedding import EmbeddingService
from app.ai.retrieval import RetrievalService
from app.ai.llm import LLMService
from app.ai.prompts import CLAUSE_ANALYSIS_PROMPT, DOCUMENT_SUMMARY_PROMPT
from app.ai.response_parser import LLMClauseAnalysis, LLMDocumentSummary

logger = get_logger(__name__)


class AnalysisPipeline:
    """Orchestrates the Retrieval-Augmented Generation (RAG) analysis pipeline."""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.retrieval_service = RetrievalService()
        self.llm_service = LLMService()

    async def analyze_clause(
        self,
        clause_text: str,
        document_type: str,
        jurisdiction: str | None = None,
    ) -> dict:
        """
        Execute the RAG pipeline for a single clause:
        1. Embed the target clause.
        2. Retrieve similar reference clauses from ChromaDB.
        3. Format the prompt with context.
        4. Call Gemini for structured risk analysis.
        
        Returns:
            Dictionary containing the analysis and the retrieved references.
        """
        try:
            # 1. Embed the target clause (use RETRIEVAL_QUERY for search)
            query_embedding = await self.embedding_service.embed_query(clause_text)
            
            # 2. Retrieve reference clauses
            # Filter by document_type if possible, to get relevant references
            where_filter = {}
            if document_type and document_type != "other":
                where_filter["document_type"] = document_type
                
            references = await self.retrieval_service.search(
                query_embedding=query_embedding,
                top_k=5,
                where_filter=where_filter if where_filter else None
            )
            
            # Format references for the prompt
            ref_texts = []
            retrieved_data = []
            for i, ref in enumerate(references, 1):
                # Only include references with decent similarity
                if ref["similarity"] > 0.6:  
                    text = ref.get("text", "")
                    title = ref.get("metadata", {}).get("title", "")
                    doc_type = ref.get("metadata", {}).get("document_type", "")
                    
                    ref_texts.append(f"Reference {i} ({doc_type} - {title}):\n{text}")
                    retrieved_data.append({
                        "id": ref.get("id"),
                        "text": text,
                        "similarity": ref.get("similarity")
                    })
                    
            references_str = "\n\n".join(ref_texts) if ref_texts else "No standard references found. Analyze based on general legal principles."
            
            # 3. Format the prompt
            prompt = CLAUSE_ANALYSIS_PROMPT.format(
                document_type=document_type,
                jurisdiction=jurisdiction or "General",
                clause_text=clause_text,
                reference_clauses=references_str
            )
            
            # 4. Call LLM
            llm_result = await self.llm_service.generate_structured_analysis(
                prompt=prompt,
                schema_class=LLMClauseAnalysis
            )
            
            # Validate output matches schema
            validated = LLMClauseAnalysis(**llm_result)
            
            # Combine validated output with retrieved data
            final_result = validated.model_dump()
            final_result["retrieved_clauses"] = retrieved_data
            final_result["raw_llm_response"] = llm_result
            
            return final_result
            
        except Exception as e:
            logger.error("clause_analysis_pipeline_error", error=str(e))
            raise AIServiceError(f"Clause analysis failed: {e}")

    async def generate_document_summary(
        self,
        document_type: str,
        jurisdiction: str | None,
        clause_analyses: list[dict],
    ) -> dict:
        """
        Generate an overall document summary based on all clause analyses.
        """
        try:
            total_clauses = len(clause_analyses)
            high_risk_clauses = []
            one_sided_clauses = []
            total_risk = 0
            
            for analysis in clause_analyses:
                score = analysis.get("risk_score", 0)
                category = analysis.get("risk_category", "standard")
                total_risk += score
                
                if category in ["high_risk", "potentially_unenforceable"] or score >= 60:
                    summary = analysis.get("plain_english_summary", "")
                    reasons = analysis.get("risk_reasons", [])
                    high_risk_clauses.append(f"- Score {score}: {summary}\n  Reasons: {', '.join(reasons)}")
                elif category == "one_sided" or score >= 40:
                    one_sided_clauses.append(analysis)
                    
            average_risk = total_risk / total_clauses if total_clauses > 0 else 0
            
            high_risk_str = "\n".join(high_risk_clauses) if high_risk_clauses else "None found."
            
            prompt = DOCUMENT_SUMMARY_PROMPT.format(
                document_type=document_type,
                jurisdiction=jurisdiction or "General",
                high_risk_summaries=high_risk_str,
                total_clauses=total_clauses,
                high_risk_count=len(high_risk_clauses),
                one_sided_count=len(one_sided_clauses),
                average_risk=f"{average_risk:.1f}"
            )
            
            llm_result = await self.llm_service.generate_structured_analysis(
                prompt=prompt,
                schema_class=LLMDocumentSummary
            )
            
            validated = LLMDocumentSummary(**llm_result)
            
            # Calculate actual distribution
            distribution = {
                "standard": 0,
                "slightly_unusual": 0,
                "one_sided": 0,
                "high_risk": 0,
                "potentially_unenforceable": 0
            }
            for analysis in clause_analyses:
                cat = analysis.get("risk_category", "standard")
                if cat in distribution:
                    distribution[cat] += 1
            
            final_result = validated.model_dump()
            final_result["risk_distribution"] = distribution
            
            return final_result
            
        except Exception as e:
            logger.error("document_summary_pipeline_error", error=str(e))
            raise AIServiceError(f"Document summary failed: {e}")
