"""
PDF and document text extraction using PyMuPDF.

Extracts structured text from PDF documents with heading detection,
paragraph awareness, and scanned-PDF detection.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logger.warning("pymupdf_not_installed", message="PyMuPDF is not installed. PDF extraction unavailable.")


@dataclass
class TextBlock:
    """A block of text extracted from a document page."""
    text: str
    page_number: int
    block_index: int
    is_heading: bool = False
    is_bold: bool = False
    font_size: float = 0.0
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)


@dataclass
class ExtractionResult:
    """Result of text extraction from a document."""
    raw_text: str
    blocks: list[TextBlock] = field(default_factory=list)
    page_count: int = 0
    is_scanned: bool = False
    metadata: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _detect_scanned_pdf(doc) -> bool:
    """
    Heuristic to detect if a PDF is scanned (image-only).

    Checks the first few pages: if they have images but very little
    extractable text, the PDF is likely scanned.
    """
    if doc.page_count == 0:
        return False

    pages_to_check = min(3, doc.page_count)
    text_chars = 0
    image_count = 0

    for page_idx in range(pages_to_check):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        text_chars += len(text)
        image_count += len(page.get_images(full=True))

    # If we have images but almost no text, it's likely scanned
    avg_chars = text_chars / pages_to_check
    if image_count > 0 and avg_chars < 50:
        return True
    return False


def _is_heading_block(block_dict: dict, median_font_size: float) -> bool:
    """
    Determine if a text block is a heading based on font properties.

    Heuristic: block is a heading if:
    - Font size is significantly larger than the median
    - Text is all uppercase
    - Text is bold
    - Text matches common legal heading patterns
    """
    text = block_dict.get("text", "").strip()
    if not text or len(text) > 200:
        return False

    # Check for common legal heading patterns
    heading_patterns = [
        r"^(?:ARTICLE|SECTION|CLAUSE|PART|CHAPTER|SCHEDULE|APPENDIX|EXHIBIT)\s",
        r"^(?:DEFINITIONS|TERMINATION|INDEMNIFICATION|GOVERNING LAW|DISPUTE RESOLUTION)",
        r"^\d+\.\s+[A-Z][A-Z\s]+$",  # "1. DEFINITIONS"
        r"^[IVXLCDM]+\.\s+",  # Roman numerals
    ]
    for pattern in heading_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True

    # Check font size (> 1.2x median = likely heading)
    font_size = block_dict.get("font_size", 0)
    if median_font_size > 0 and font_size > median_font_size * 1.2:
        return True

    # All-caps short text is likely a heading
    if text.isupper() and len(text) < 100:
        return True

    return False


def extract_pdf(file_path: str | Path) -> ExtractionResult:
    """
    Extract text and structure from a PDF file using PyMuPDF.

    Args:
        file_path: Path to the PDF file.

    Returns:
        ExtractionResult with extracted text, blocks, and metadata.
    """
    if fitz is None:
        return ExtractionResult(
            raw_text="",
            errors=["PyMuPDF is not installed. Cannot extract PDF text."],
        )

    file_path = Path(file_path)
    if not file_path.exists():
        return ExtractionResult(
            raw_text="",
            errors=[f"File not found: {file_path}"],
        )

    try:
        doc = fitz.open(str(file_path))
    except Exception as e:
        logger.error("pdf_open_error", error=str(e), path=str(file_path))
        return ExtractionResult(
            raw_text="",
            errors=[f"Failed to open PDF: {e}"],
        )

    is_scanned = _detect_scanned_pdf(doc)
    blocks: list[TextBlock] = []
    all_text_parts: list[str] = []
    all_font_sizes: list[float] = []

    # First pass: collect font sizes for median calculation
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:  # Skip image blocks
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = span.get("size", 0)
                    if size > 0:
                        all_font_sizes.append(size)

    median_font_size = sorted(all_font_sizes)[len(all_font_sizes) // 2] if all_font_sizes else 12.0

    # Second pass: extract text blocks with structure
    for page_idx in range(doc.page_count):
        page = doc[page_idx]
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

        for block_idx, block in enumerate(page_dict.get("blocks", [])):
            if block.get("type") != 0:  # Skip image blocks
                continue

            block_text_parts = []
            block_font_sizes = []
            is_bold = False

            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    line_text += text
                    block_font_sizes.append(span.get("size", 0))
                    flags = span.get("flags", 0)
                    if flags & 2**4:  # Bold flag
                        is_bold = True
                block_text_parts.append(line_text)

            block_text = "\n".join(block_text_parts).strip()
            if not block_text:
                continue

            avg_font_size = (
                sum(block_font_sizes) / len(block_font_sizes)
                if block_font_sizes
                else median_font_size
            )

            block_info = {
                "text": block_text,
                "font_size": avg_font_size,
                "is_bold": is_bold,
            }
            is_heading = _is_heading_block(block_info, median_font_size)

            bbox = block.get("bbox", (0, 0, 0, 0))
            text_block = TextBlock(
                text=block_text,
                page_number=page_idx + 1,
                block_index=block_idx,
                is_heading=is_heading,
                is_bold=is_bold,
                font_size=avg_font_size,
                bbox=tuple(bbox),
            )
            blocks.append(text_block)
            all_text_parts.append(block_text)

    raw_text = "\n\n".join(all_text_parts)

    # Extract document metadata
    doc_metadata = doc.metadata or {}
    metadata = {
        "title": doc_metadata.get("title", ""),
        "author": doc_metadata.get("author", ""),
        "subject": doc_metadata.get("subject", ""),
        "creator": doc_metadata.get("creator", ""),
        "producer": doc_metadata.get("producer", ""),
        "page_count": doc.page_count,
    }

    doc.close()

    logger.info(
        "pdf_extracted",
        path=str(file_path),
        pages=doc.page_count if hasattr(doc, 'page_count') else metadata["page_count"],
        blocks=len(blocks),
        chars=len(raw_text),
        is_scanned=is_scanned,
    )

    return ExtractionResult(
        raw_text=raw_text,
        blocks=blocks,
        page_count=metadata["page_count"],
        is_scanned=is_scanned,
        metadata=metadata,
    )
