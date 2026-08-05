"""
Clause ORM model.

Represents an individual legal clause extracted from a document.
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDMixin, TimestampMixin


class Clause(Base, UUIDMixin, TimestampMixin):
    """A single legal clause extracted from a document."""

    __tablename__ = "clauses"

    document_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    clause_index: Mapped[int] = mapped_column(Integer, nullable=False)
    clause_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    start_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_char: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # Relationships
    document = relationship("Document", back_populates="clauses")
    analysis_result = relationship(
        "AnalysisResult", back_populates="clause", uselist=False,
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Clause(id={self.id}, index={self.clause_index}, title={self.title})>"
