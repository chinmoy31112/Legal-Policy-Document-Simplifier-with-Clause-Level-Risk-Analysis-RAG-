"""
Export Service.

Generates structured JSON and human-readable Markdown exports
for document-level and clause-level risk analyses.

Enforces:
- Per-user data isolation: rejects unauthorized access with NotFoundError.
- Mandatory legal disclaimer included on every export format.
- Grounded citations (verbatim quotes & reference clause IDs).
"""

import html
import io
from datetime import datetime
from typing import Any
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline import resolve_jurisdiction
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


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page numbers."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 54, 28, page_text)
        self.drawString(54, 28, "Confidential — Legal Simplification & Risk Assessment Report")
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 38, letter[0] - 54, 38)
        self.restoreState()


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
                "jurisdiction": resolve_jurisdiction(document.jurisdiction),
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

    async def export_pdf(self, document_id: UUID, user_id: UUID) -> bytes:
        """
        Generate structured, publication-ready PDF risk analysis report.
        """
        data = await self.export_json(document_id, user_id)
        doc_info = data.get("document", {})
        summary = data.get("risk_summary", {})
        clauses = data.get("clauses", [])
        disclaimer = data.get("disclaimer", LEGAL_DISCLAIMER)

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=3,
        )
        sub_title_style = ParagraphStyle(
            "ReportSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=10,
        )
        h2_style = ParagraphStyle(
            "ReportH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6,
        )
        h3_style = ParagraphStyle(
            "ReportH3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=3,
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        )
        disclaimer_style = ParagraphStyle(
            "ReportDisclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10.5,
            textColor=colors.HexColor("#475569"),
        )
        rewrite_style = ParagraphStyle(
            "ReportRewrite",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11.5,
            textColor=colors.HexColor("#0f766e"),
        )

        story: list[Any] = []

        # Title & Metadata
        filename = html.escape(str(doc_info.get("filename", "Document")))
        generated_date = datetime.now().strftime("%B %d, %Y, %I:%M %p")
        story.append(Paragraph("Legal Document Simplification &amp; Risk Report", title_style))
        story.append(
            Paragraph(
                f"<b>File:</b> {filename} &nbsp;|&nbsp; <b>Jurisdiction:</b> {html.escape(str(doc_info.get('jurisdiction', 'General')))} &nbsp;|&nbsp; <b>Generated:</b> {generated_date}",
                sub_title_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

        # Top KPI Summary Box
        score_val = summary.get("overall_risk_score")
        risk_level = summary.get("overall_risk_level", "LOW")
        score_text = f"<b>{score_val}</b> / 100" if score_val is not None else "<b>N/A</b> (Non-Legal)"

        risk_colors = {
            "CRITICAL": "#ef4444",
            "HIGH": "#f97316",
            "MEDIUM": "#eab308",
            "LOW": "#10b981",
            "NOT_APPLICABLE": "#64748b",
        }
        badge_color = colors.HexColor(risk_colors.get(str(risk_level).upper(), "#64748b"))

        summary_table_data = [
            [
                Paragraph("<b>Document Classification:</b>", body_style),
                Paragraph(html.escape(str(doc_info.get("document_type", "General")).replace("_", " ").title()), body_style),
                Paragraph("<b>Overall Risk Assessment:</b>", body_style),
                Paragraph(f"<font color='{badge_color}'><b>{score_text} &nbsp;[{risk_level}]</b></font>", body_style),
            ],
            [
                Paragraph("<b>Total Clauses Evaluated:</b>", body_style),
                Paragraph(str(len(clauses)), body_style),
                Paragraph("<b>Audit Status:</b>", body_style),
                Paragraph(html.escape(str(doc_info.get("status", "completed")).upper()), body_style),
            ],
        ]
        summary_table = Table(summary_table_data, colWidths=[130, 122, 130, 122])
        summary_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(summary_table)
        story.append(Spacer(1, 10))

        # Legal Disclaimer Callout
        disclaimer_text = html.escape(disclaimer or LEGAL_DISCLAIMER)
        disc_table = Table([[Paragraph(f"<b>LEGAL DISCLAIMER:</b> {disclaimer_text}", disclaimer_style)]], colWidths=[504])
        disc_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(disc_table)
        story.append(Spacer(1, 10))

        # Section 1: Executive Summary
        story.append(Paragraph("1. Executive Risk Summary", h2_style))
        exec_summary = summary.get("executive_summary") or "No executive summary available."
        story.append(Paragraph(html.escape(exec_summary), body_style))
        story.append(Spacer(1, 8))

        # Section 2: Category Risk Breakdown
        story.append(Paragraph("2. Category Risk Breakdown", h2_style))
        cat_breakdown = summary.get("category_breakdown", {})
        cat_rows = [
            [
                Paragraph("<b>Category</b>", body_style),
                Paragraph("<b>Clause Count</b>", body_style),
                Paragraph("<b>Avg Risk Score</b>", body_style),
                Paragraph("<b>Max Risk Tier</b>", body_style),
            ]
        ]

        if isinstance(cat_breakdown, dict) and cat_breakdown:
            for cat, stats in cat_breakdown.items():
                if isinstance(stats, dict):
                    c_count = str(stats.get("clause_count", 1))
                    c_avg = str(stats.get("avg_score", "-"))
                    c_max = str(stats.get("max_risk_level", stats.get("max_risk", "-")))
                    cat_rows.append([
                        Paragraph(html.escape(str(cat).replace("_", " ").title()), body_style),
                        Paragraph(c_count, body_style),
                        Paragraph(c_avg, body_style),
                        Paragraph(f"<b>{html.escape(c_max)}</b>", body_style),
                    ])
        if len(cat_rows) == 1:
            cat_rows.append([
                Paragraph("General Agreement", body_style),
                Paragraph(str(len(clauses)), body_style),
                Paragraph(str(score_val or "-"), body_style),
                Paragraph(f"<b>{risk_level}</b>", body_style),
            ])

        cat_table = Table(cat_rows, colWidths=[180, 108, 108, 108])
        cat_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(cat_table)
        story.append(Spacer(1, 10))

        # Section 3: Negotiation Priorities (if any)
        priorities = summary.get("negotiation_priorities", [])
        if priorities and isinstance(priorities, list):
            story.append(Paragraph("3. Top Negotiation Priorities", h2_style))
            for idx, p in enumerate(priorities, start=1):
                if isinstance(p, dict):
                    issue = html.escape(str(p.get("issue", "Disproportionate risk")))
                    change = html.escape(str(p.get("suggested_change", "Seek reciprocal terms")))
                    lvl = html.escape(str(p.get("risk_level", p.get("priority", "HIGH"))).upper())
                    p_color = risk_colors.get(lvl, "#f97316")
                    story.append(
                        Paragraph(
                            f"<b>{idx}.</b> <font color='{p_color}'><b>[{lvl}]</b></font> <b>{issue}</b><br/>"
                            f"&nbsp;&nbsp;&nbsp;&nbsp;<i>Recommended Adjustment:</i> {change}",
                            body_style,
                        )
                    )
                    story.append(Spacer(1, 3))
            story.append(Spacer(1, 8))

        # Section 4: Clause-by-Clause Risk Analysis
        story.append(Paragraph("4. Clause-by-Clause Risk Analysis", h2_style))
        story.append(
            Paragraph(
                "Every evaluated agreement provision with plain-English meaning, identified liabilities, grounded citations, and recommended balanced rewrites.",
                sub_title_style,
            )
        )

        for idx, c in enumerate(clauses, start=1):
            clause_items: list[Any] = []
            c_title = c.get("title") or f"Clause {c.get('clause_index', idx)}"
            c_risk = str(c.get("risk_level", "LOW")).upper()
            c_score = c.get("risk_score", 0)
            c_conf = c.get("confidence", 0.0)
            c_color = risk_colors.get(c_risk, "#64748b")

            clause_items.append(
                Paragraph(
                    f"<b>{html.escape(c_title)}</b> &nbsp;&nbsp;"
                    f"<font color='{c_color}'><b>[{c_risk} &bull; Score: {c_score}/100 &bull; Conf: {c_conf:.2f}]</b></font>",
                    h3_style,
                )
            )

            plain = c.get("plain_english")
            if plain:
                clause_items.append(Paragraph(f"<b>Plain English:</b> {html.escape(plain)}", body_style))

            reasons = c.get("risk_reasons") or []
            if reasons:
                reasons_html = "<br/>".join([f"&bull; {html.escape(str(r))}" for r in reasons])
                clause_items.append(Paragraph(f"<b>Key Concerns &amp; Liabilities:</b><br/>{reasons_html}", body_style))

            missing = c.get("missing_protections") or []
            if missing:
                missing_str = ", ".join([html.escape(str(m)) for m in missing])
                clause_items.append(Paragraph(f"<b>Missing Protections:</b> {missing_str}", body_style))

            rewrite = c.get("suggested_rewrite")
            if rewrite:
                rewrite_table = Table(
                    [[Paragraph(f"<b>Suggested Balanced Rewrite:</b><br/>{html.escape(rewrite)}", rewrite_style)]],
                    colWidths=[504],
                )
                rewrite_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#86efac")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ])
                )
                clause_items.append(rewrite_table)

            note = c.get("legal_review_note")
            if note:
                clause_items.append(Paragraph(f"<i>Legal Review Note: {html.escape(note)}</i>", disclaimer_style))

            clause_items.append(
                HRFlowable(
                    width="100%",
                    thickness=0.5,
                    color=colors.HexColor("#e2e8f0"),
                    spaceBefore=4,
                    spaceAfter=6,
                )
            )
            story.append(KeepTogether(clause_items))

        doc.build(story, canvasmaker=NumberedCanvas)
        return buf.getvalue()
