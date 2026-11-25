"""
Export Service.

Generates structured JSON and human-readable Markdown exports
for document-level and clause-level risk analyses.

Enforces:
- Per-user data isolation: rejects unauthorized access with NotFoundError.
- Mandatory legal disclaimer included on every export format.
- Grounded citations (verbatim quotes & reference clause IDs).
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.document import Document
from app.repositories.analysis_repo import AnalysisResultRepository, DocumentAnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.repositories.document_repo import DocumentRepository

LEGAL_DISCLAIMER = (
    "This analysis provides informational document simplification and risk assessment only. "
    "It does not constitute legal advice. Review by a qualified attorney is recommended "
    "before executing legal agreements."
)


class ExportService:
    """Service generating JSON and Markdown exports of document analyses."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.document_repo = DocumentRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.analysis_repo = AnalysisResultRepository(session)
        self.doc_analysis_repo = DocumentAnalysisRepository(session)

    async def _get_authorized_document(self, document_id: UUID, user_id: UUID) -> Document:
        """Fetch document verifying user ownership for data isolation."""
        document = await self.document_repo.get_by_id_and_user(document_id, user_id)
        if document is None:
            raise NotFoundError("Document", str(document_id))
        return document

    async def export_json(self, document_id: UUID, user_id: UUID) -> dict[str, Any]:
        """
        Generate validated JSON export of document analysis and all clauses.
        """
        document = await self._get_authorized_document(document_id, user_id)
        doc_analysis = await self.doc_analysis_repo.get_by_document(document_id)
        clause_analyses = await self.analysis_repo.get_by_document(document_id)
        clauses = await self.clause_repo.get_by_document(document_id)
        clause_map = {UUID(str(c.id)): c for c in clauses}

        clause_exports: list[dict[str, Any]] = []
        for ca in clause_analyses:
            clause = clause_map.get(UUID(str(ca.clause_id)))
            clause_exports.append({
                "clause_id": str(ca.clause_id),
                "clause_index": clause.clause_index if clause else None,
                "clause_number": clause.clause_number if clause else None,
                "title": clause.title if clause else "Clause",
                "category": clause.category if clause else "General",
                "original_text": clause.content if clause else "",
                "plain_english": ca.plain_english_summary,
                "risk_level": ca.risk_category,
                "risk_score": ca.risk_score,
                "confidence": ca.confidence_score,
                "risk_reasons": ca.risk_reasons or [],
                "missing_protections": ca.missing_protections or [],
                "suggested_rewrite": ca.suggested_rewrite,
                "legal_review_note": ca.potential_legal_concern,
                "retrieved_references": ca.retrieved_clauses or [],
            })

        score = doc_analysis.overall_risk_score if doc_analysis else None
        if score is None:
            risk_level = "NOT_APPLICABLE"
        elif score >= 75:
            risk_level = "CRITICAL"
        elif score >= 50:
            risk_level = "HIGH"
        elif score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "document": {
                "id": str(document.id),
                "filename": document.original_filename,
                "document_type": document.document_type,
                "jurisdiction": document.jurisdiction or "General",
                "file_size": document.file_size,
                "uploaded_at": document.created_at.isoformat() if document.created_at else None,
                "status": document.status,
            },
            "risk_summary": {
                "overall_risk_score": score,
                "overall_risk_level": risk_level,
                "executive_summary": doc_analysis.overall_summary if doc_analysis else "No analysis available.",
                "category_breakdown": doc_analysis.risk_distribution if doc_analysis else {},
                "negotiation_priorities": doc_analysis.top_risky_clauses if doc_analysis else [],
                "recommendations": doc_analysis.recommendations if doc_analysis else [],
            },
            "clauses": clause_exports,
            "disclaimer": LEGAL_DISCLAIMER,
        }

    async def export_markdown(self, document_id: UUID, user_id: UUID) -> str:
        """
        Generate structured Markdown report of document risk assessment.
        """
        data = await self.export_json(document_id, user_id)
        doc = data["document"]
        summary = data["risk_summary"]
        clauses = data["clauses"]

        score_val = summary.get("overall_risk_score")
        score_display = f"**{score_val}/100** ({summary['overall_risk_level']})" if score_val is not None else "**N/A** (Risk Scoring Skipped for Non-Legal Document)"

        md_lines = [
            f"# Legal Document Simplification & Risk Report: {doc['filename']}",
            "",
            "> **IMPORTANT NOTICE:** " + LEGAL_DISCLAIMER,
            "",
            "## 1. Executive Summary",
            "",
            f"- **Document Type:** `{doc['document_type']}`",
            f"- **Jurisdiction:** `{doc['jurisdiction']}`",
            f"- **Overall Risk Score:** {score_display}",
            f"- **Total Clauses Analyzed:** {len(clauses)}",
            "",
            summary["executive_summary"],
            "",
            "## 2. Category Risk Breakdown",
            "",
            "| Category | Clause Count | Average Risk Score | Max Risk Tier |",
            "| :--- | :---: | :---: | :---: |",
        ]

        breakdown = summary.get("category_breakdown", {})
        if isinstance(breakdown, dict) and breakdown:
            for cat, stats in breakdown.items():
                if isinstance(stats, dict):
                    count = stats.get("clause_count", 1)
                    avg_score = stats.get("avg_score", "-")
                    max_lvl = stats.get("max_risk_level", stats.get("max_risk", "-"))
                    md_lines.append(f"| {cat} | {count} | {avg_score} | `{max_lvl}` |")
        else:
            md_lines.append("| General | " + str(len(clauses)) + " | " + str(summary.get('overall_risk_score') or '-') + " | `LOW` |")

        # Negotiation Priorities
        priorities = summary.get("negotiation_priorities", [])
        if priorities:
            md_lines.extend([
                "",
                "## 3. Top Negotiation Priorities",
                "",
            ])
            for idx, p in enumerate(priorities, start=1):
                issue = p.get("issue", "Disproportionate risk")
                change = p.get("suggested_change", "Seek reciprocal terms")
                lvl = p.get("risk_level", p.get("priority", "HIGH"))
                md_lines.append(f"{idx}. **[{lvl}] {issue}**")
                md_lines.append(f"   - *Recommended Negotiation Adjustment:* {change}")

        # Clause-by-Clause breakdown
        md_lines.extend([
            "",
            "## 4. Clause-by-Clause Risk Analysis",
            "",
        ])

        for c in clauses:
            title = c.get("title") or f"Clause {c.get('clause_index', '')}"
            risk_lvl = c.get("risk_level", "LOW")
            score = c.get("risk_score", 0)
            conf = c.get("confidence", 0.0)

            md_lines.extend([
                f"### {title}",
                f"- **Risk Level:** `{risk_lvl}` (Score: {score}/100, Confidence: {conf})",
                f"- **Plain English Meaning:** {c.get('plain_english', '')}",
            ])

            reasons = c.get("risk_reasons", [])
            if reasons:
                md_lines.append("- **Identified Concerns & Grounded Citations:**")
                for r in reasons:
                    md_lines.append(f"  - {r}")

            missing = c.get("missing_protections", [])
            if missing:
                md_lines.append(f"- **Missing Protections:** {', '.join(missing)}")

            rewrite = c.get("suggested_rewrite")
            if rewrite:
                md_lines.append("- **Suggested Balanced Rewrite:**")
                md_lines.append(f"  > {rewrite}")

            note = c.get("legal_review_note")
            if note:
                md_lines.append(f"- **Notice:** *{note}*")

            md_lines.append("")

        md_lines.extend([
            "---",
            "> **Disclaimer:** " + LEGAL_DISCLAIMER,
            "",
        ])

        return "\n".join(md_lines)
