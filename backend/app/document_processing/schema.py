"""
Schema definitions for document extraction and clause segmentation.

Pure data structures without database or network dependencies.
"""

import hashlib
from typing import Any

from pydantic import BaseModel, Field


class TextSpan(BaseModel):
    """Represents a discrete text span extracted with font styling and bounding box."""

    text: str
    font: str = ""
    size: float = 0.0
    is_bold: bool = False
    is_italic: bool = False
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # (x0, y0, x1, y1)
    page: int = 1


class TextBlock(BaseModel):
    """A logical text block containing spans on a specific document page."""

    text: str
    page: int
    block_index: int
    spans: list[TextSpan] = Field(default_factory=list)
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    is_heading: bool = False
    font_size: float = 0.0
    is_bold: bool = False


class ExtractionResult(BaseModel):
    """Normalized document extraction result from PyMuPDF or alternate readers."""

    raw_text: str
    blocks: list[TextBlock] = Field(default_factory=list)
    page_count: int = 0
    is_scanned: bool = False
    is_encrypted: bool = False
    is_corrupt: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class Clause(BaseModel):
    """
    Standard Clause schema per Phase 2 deliverables:
    id, parent_id, order, title, text, page, bounding_boxes, text_hash.
    """

    id: str
    parent_id: str | None = None
    order: int
    title: str = ""
    text: str
    page: int = 1
    # Bounding boxes represented as [page, x0, y0, x1, y1] coordinates
    bounding_boxes: list[list[float]] = Field(default_factory=list)
    text_hash: str = ""

    @property
    def content(self) -> str:
        """Alias for text for backward compatibility."""
        return self.text

    @property
    def clause_number(self) -> str:
        """Alias for clause numbering parsed from title."""
        return self.title.split()[0] if self.title else ""

    @property
    def category(self) -> str:
        """Default category."""
        return "general"

    def compute_hash(self) -> str:
        """Compute deterministic SHA-256 hash of normalized clause text."""
        normalized = " ".join(self.text.split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        """Automatically ensure text_hash is set if missing."""
        if not self.text_hash and self.text:
            self.text_hash = self.compute_hash()
