"""
Clause segmentation module.

Segments extracted text blocks into distinct legal clauses based on
document structure, headings, numbering, and heuristics.
"""

import re
from dataclasses import dataclass
from typing import Iterator

from app.core.logging import get_logger
from app.document_processing.extractor import ExtractionResult, TextBlock

logger = get_logger(__name__)


@dataclass
class ClauseSegment:
    """A segmented clause extracted from a document."""
    index: int
    content: str
    title: str = ""
    clause_number: str = ""
    category: str = "general"
    start_page: int = 0
    end_page: int = 0


class DocumentSegmenter:
    """Segments document text blocks into distinct legal clauses."""

    # Regex patterns for detecting legal clause numbering
    NUMBERING_PATTERNS = [
        r"^(\d+\.\d+\.\d+)\s",       # e.g., 1.1.1
        r"^(\d+\.\d+)\s",           # e.g., 1.1
        r"^(\d+)\.\s",              # e.g., 1.
        r"^\(([a-z])\)\s",          # e.g., (a)
        r"^\(([ivx]+)\)\s",         # e.g., (iv)
        r"^([A-Z])\.\s",            # e.g., A.
        r"^Article\s(\d+)\.?\s",    # e.g., Article 1
        r"^Section\s(\d+)\.?\s",    # e.g., Section 1
        r"^Clause\s(\d+)\.?\s",     # e.g., Clause 1
    ]

    def __init__(self, min_clause_length: int = 50):
        self.min_clause_length = min_clause_length
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.NUMBERING_PATTERNS]

    def _extract_numbering(self, text: str) -> tuple[str, str]:
        """
        Attempt to extract a clause number and title from text.
        Returns (number, remaining_text).
        """
        for pattern in self._compiled_patterns:
            match = pattern.match(text)
            if match:
                number = match.group(1)
                remaining = text[match.end():].strip()
                return number, remaining
        return "", text

    def _is_list_item(self, text: str) -> bool:
        """Detect if the text is a bullet point or list item."""
        return bool(re.match(r"^[\u2022\u25cf\u25cb\-\*]\s", text))

    def segment(self, extraction_result: ExtractionResult) -> list[ClauseSegment]:
        """
        Segment the extracted text blocks into distinct clauses.
        """
        if not extraction_result.blocks:
            # Fallback to paragraph splitting if no blocks available
            return self._fallback_segmentation(extraction_result.raw_text)

        clauses: list[ClauseSegment] = []
        current_clause_blocks: list[TextBlock] = []
        current_title = ""
        current_number = ""
        clause_index = 0

        def _save_current_clause():
            nonlocal clause_index, current_clause_blocks, current_title, current_number
            if not current_clause_blocks:
                return

            text = "\n\n".join(b.text for b in current_clause_blocks).strip()
            if len(text) >= self.min_clause_length:
                start_page = current_clause_blocks[0].page_number
                end_page = current_clause_blocks[-1].page_number
                
                clause = ClauseSegment(
                    index=clause_index,
                    title=current_title,
                    clause_number=current_number,
                    content=text,
                    start_page=start_page,
                    end_page=end_page,
                )
                clauses.append(clause)
                clause_index += 1

            current_clause_blocks = []

        for block in extraction_result.blocks:
            text = block.text.strip()
            if not text:
                continue

            # Check if block is a heading
            if block.is_heading:
                _save_current_clause()
                number, clean_title = self._extract_numbering(text)
                current_title = clean_title if len(clean_title) < 200 else ""
                current_number = number
                
                # If the heading has substantial text itself, include it
                if len(clean_title) >= self.min_clause_length:
                     current_clause_blocks.append(block)
                continue

            # Check for numbering that might indicate a new clause without heading styling
            number, remaining = self._extract_numbering(text)
            if number and not self._is_list_item(text):
                # Only treat as a new clause boundary if we've accumulated enough text
                # to avoid splitting e.g. "1.1 Definitions" and its immediately following text
                text_so_far = "\n\n".join(b.text for b in current_clause_blocks).strip()
                if len(text_so_far) > 100:
                    _save_current_clause()
                    current_number = number
                    # We don't have a title, just the number
                    current_title = ""

            current_clause_blocks.append(block)

        # Save the final clause
        _save_current_clause()

        # If we couldn't segment effectively, fallback
        if len(clauses) < 3 and len(extraction_result.raw_text) > 1000:
            logger.warning("heuristic_segmentation_failed", blocks=len(extraction_result.blocks))
            return self._fallback_segmentation(extraction_result.raw_text)

        logger.info("segmentation_completed", clauses=len(clauses))
        return clauses

    def _fallback_segmentation(self, text: str) -> list[ClauseSegment]:
        """
        Fallback segmentation based purely on paragraphs.
        Used when PDF structure extraction fails or text is unstructured.
        """
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        clauses = []
        current_chunk = []
        current_length = 0
        clause_index = 0

        for para in paragraphs:
            current_chunk.append(para)
            current_length += len(para)

            # Split approximately every 1000 characters to form a reasonable clause size
            # while keeping paragraphs intact
            if current_length > 1000 or len(current_chunk) > 5:
                content = "\n\n".join(current_chunk)
                clauses.append(ClauseSegment(
                    index=clause_index,
                    content=content,
                    title=f"Section {clause_index + 1}",
                ))
                clause_index += 1
                current_chunk = []
                current_length = 0

        if current_chunk:
            content = "\n\n".join(current_chunk)
            if clauses and len(content) < 200:
                # Merge small trailing chunk into last clause
                clauses[-1].content += f"\n\n{content}"
            else:
                clauses.append(ClauseSegment(
                    index=clause_index,
                    content=content,
                    title=f"Section {clause_index + 1}",
                ))

        logger.info("fallback_segmentation_used", clauses=len(clauses))
        return clauses
