"""
Analysis ORM models.

AnalysisResult: per-clause analysis output from the RAG pipeline.
DocumentAnalysis: document-level aggregated risk assessment.
"""

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDMixin, TimestampMixin


class AnalysisResult(Base, UUIDMixin, TimestampMixin):
    """Per-clause analysis result from the RAG pipeline."""

    __tablename__ = "analysis_results"

    clause_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    document_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    plain_english_summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_category: Mapped[str] = mapped_column(
        String(50), nullable=False, default="standard"
    )
    risk_reasons: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    retrieved_clauses: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    missing_protections: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    suggested_rewrite: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    potential_legal_concern: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_llm_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    clause = relationship("Clause", back_populates="analysis_result")
    document = relationship("Document", back_populates="analysis_results")

    def __repr__(self) -> str:
        return f"<AnalysisResult(id={self.id}, risk_score={self.risk_score}, category={self.risk_category})>"


class DocumentAnalysis(Base, UUIDMixin, TimestampMixin):
    """Document-level aggregated risk assessment."""

    __tablename__ = "document_analysis"

    document_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    overall_risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_risky_clauses: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    clause_statistics: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    risk_distribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)

    # Relationships
    document = relationship("Document", back_populates="document_analysis")

    def __repr__(self) -> str:
        return f"<DocumentAnalysis(id={self.id}, risk_score={self.overall_risk_score})>"
