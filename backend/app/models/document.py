"""
Document ORM model.

Represents uploaded legal documents with metadata and processing status.
"""

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, UUIDMixin, TimestampMixin


class Document(Base, UUIDMixin, TimestampMixin):
    """Uploaded legal document."""

    __tablename__ = "documents"

    user_id: Mapped["UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="other"
    )
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="uploaded", index=True
    )
    jurisdiction: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    # Relationships
    user = relationship("User", back_populates="documents")
    clauses = relationship(
        "Clause", back_populates="document", lazy="selectin",
        cascade="all, delete-orphan"
    )
    document_analysis = relationship(
        "DocumentAnalysis", back_populates="document", uselist=False,
        cascade="all, delete-orphan"
    )
    analysis_results = relationship(
        "AnalysisResult", back_populates="document",
        cascade="all, delete-orphan", lazy="selectin",
        foreign_keys="AnalysisResult.document_id"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename={self.original_filename}, status={self.status})>"
