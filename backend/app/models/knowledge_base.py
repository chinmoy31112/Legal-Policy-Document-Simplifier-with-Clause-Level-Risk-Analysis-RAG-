"""
Knowledge Base ORM models.

KBDocument: reference legal documents in the knowledge base.
KBClause: individual reference clauses from knowledge base documents.
"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDMixin, TimestampMixin


class KBDocument(Base, UUIDMixin, TimestampMixin):
    """Knowledge base reference document."""

    __tablename__ = "kb_documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # Relationships
    clauses = relationship(
        "KBClause", back_populates="kb_document", lazy="selectin",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<KBDocument(id={self.id}, title={self.title})>"


class KBClause(Base, UUIDMixin, TimestampMixin):
    """Individual reference clause from a knowledge base document."""

    __tablename__ = "kb_clauses"

    kb_document_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("kb_documents.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    clause_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chromadb_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # Relationships
    kb_document = relationship("KBDocument", back_populates="clauses")

    def __repr__(self) -> str:
        return f"<KBClause(id={self.id}, title={self.title})>"
