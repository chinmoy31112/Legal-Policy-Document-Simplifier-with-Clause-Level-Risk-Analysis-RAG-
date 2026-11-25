"""
PyMuPDF span-level text and layout extractor.

Pure functions: zero database access, zero network calls.
Extracts font size, weight, line bounding boxes, and detects scanned/corrupt/encrypted files.
"""

import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.document_processing.schema import ExtractionResult, TextBlock, TextSpan

logger = get_logger(__name__)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    logger.warning("pymupdf_missing", message="PyMuPDF not installed.")

# Minimum average characters per page to consider a document machine-readable text
MIN_TEXT_CHARS_PER_PAGE = 25


class DocumentProcessingError(Exception):
    """Base exception for document extraction failures."""

    pass


class ScannedDocumentError(DocumentProcessingError):
    """Raised or flagged when an uploaded PDF is an image-only scan."""

    pass


class EncryptedDocumentError(DocumentProcessingError):
    """Raised or flagged when an uploaded PDF is password-protected."""

    pass


class CorruptDocumentError(DocumentProcessingError):
    """Raised or flagged when an uploaded file cannot be parsed or is empty."""

    pass


def is_scanned_pdf(doc: Any) -> bool:
    """
    Determine if a PyMuPDF Document is a scanned raster document with no text layer.
    """
    if doc.page_count == 0:
        return False

    pages_to_sample = min(5, doc.page_count)
    total_chars = 0
    total_images = 0

    for i in range(pages_to_sample):
        page = doc[i]
        text = page.get_text("text").strip()
        total_chars += len(text)
        total_images += len(page.get_images())

    avg_chars = total_chars / pages_to_sample
    # Scanned: has image streams but virtually zero extractable characters
    if avg_chars < MIN_TEXT_CHARS_PER_PAGE and total_images > 0:
        return True
    if total_chars == 0 and total_images > 0:
        return True
    return False


def _detect_heading(
    text: str,
    font_size: float,
    is_bold: bool,
    body_font_size: float,
) -> bool:
    """
    Heuristically identify whether a block is a legal heading or title.
    """
    cleaned = text.strip()
    if not cleaned or len(cleaned) > 200:
        return False

    # Heading legal patterns
    heading_regexes = [
        r"^(?:ARTICLE|SECTION|CLAUSE|PART|SCHEDULE|APPENDIX|EXHIBIT)\s+[\dIVXLCDM]+",
        r"^\d+(\.\d+)*\.?\s+[A-Z]",
        r"^\([a-z\d]+\)\s+[A-Z]",
        r"^(?:RECITALS|DEFINITIONS|INDEMNIFICATION|LIMITATION OF LIABILITY|TERMINATION|GOVERNING LAW|CONFIDENTIALITY|MISCELLANEOUS)\b",
    ]
    for pattern in heading_regexes:
        if re.match(pattern, cleaned, re.IGNORECASE):
            return True

    # Typography signals
    if body_font_size > 0 and font_size >= body_font_size * 1.15:
        return True
    if is_bold and len(cleaned) < 120 and (cleaned.isupper() or cleaned.istitle()):
        return True

    return False


def extract_pdf(
    file_input: str | Path | bytes,
    raise_on_error: bool = False,
) -> ExtractionResult:
    """
    Extract structured text blocks, spans, and bounding boxes from a PDF.

    Args:
        file_input: File path (str/Path) or raw PDF bytes.
        raise_on_error: If True, raises custom exceptions; if False, returns ExtractionResult with flags.

    Returns:
        ExtractionResult populated with blocks, metadata, and error flags.
    """
    if fitz is None:
        err = "PyMuPDF (fitz) is not installed."
        if raise_on_error:
            raise DocumentProcessingError(err)
        return ExtractionResult(raw_text="", errors=[err], is_corrupt=True)

    # Validate file presence or byte length
    if isinstance(file_input, (str, Path)):
        path = Path(file_input)
        if not path.exists() or path.stat().st_size == 0:
            err = f"File is empty or not found: {path}"
            if raise_on_error:
                raise CorruptDocumentError(err)
            return ExtractionResult(raw_text="", errors=[err], is_corrupt=True)
        try:
            doc = fitz.open(str(path))
        except Exception as exc:
            err = f"Corrupt PDF file: {exc}"
            if raise_on_error:
                raise CorruptDocumentError(err) from exc
            return ExtractionResult(raw_text="", errors=[err], is_corrupt=True)
    elif isinstance(file_input, (bytes, bytearray)):
        if len(file_input) == 0:
            err = "Supplied PDF byte array is empty."
            if raise_on_error:
                raise CorruptDocumentError(err)
            return ExtractionResult(raw_text="", errors=[err], is_corrupt=True)
        try:
            doc = fitz.open(stream=file_input, filetype="pdf")
        except Exception as exc:
            err = f"Corrupt PDF byte stream: {exc}"
            if raise_on_error:
                raise CorruptDocumentError(err) from exc
            return ExtractionResult(raw_text="", errors=[err], is_corrupt=True)
    else:
        err = f"Unsupported input type: {type(file_input)}"
        if raise_on_error:
            raise DocumentProcessingError(err)
        return ExtractionResult(raw_text="", errors=[err], is_corrupt=True)

    # 1. Check for encrypted / password-protected document
    if doc.is_encrypted or doc.needs_pass:
        doc.close()
        err = "PDF document is encrypted or requires a password."
        if raise_on_error:
            raise EncryptedDocumentError(err)
        return ExtractionResult(raw_text="", is_encrypted=True, errors=[err])

    # 2. Check for empty document
    if doc.page_count == 0:
        doc.close()
        err = "PDF document contains 0 pages."
        if raise_on_error:
            raise CorruptDocumentError(err)
        return ExtractionResult(raw_text="", page_count=0, is_corrupt=True, errors=[err])

    # 3. Check for scanned / raster image PDF
    if is_scanned_pdf(doc):
        page_cnt = doc.page_count
        doc.close()
        err = "Scanned PDF detected. This system requires digital text-based PDFs with selectable text."
        if raise_on_error:
            raise ScannedDocumentError(err)
        return ExtractionResult(
            raw_text="",
            page_count=page_cnt,
            is_scanned=True,
            errors=[err],
        )

    # 4. Extract spans and calculate font distributions
    raw_blocks: list[TextBlock] = []
    font_sizes: list[float] = []
    all_raw_paragraphs: list[str] = []

    block_global_idx = 0
    for page_idx in range(doc.page_count):
        page_num = page_idx + 1
        page = doc[page_idx]

        # Extract structured layout dictionary
        page_dict = page.get_text("dict", flags=fitz.TEXTFLAGS_SEARCH)
        for b in page_dict.get("blocks", []):
            if b.get("type") != 0:  # Type 0 is text block, 1 is image
                continue

            block_bbox = tuple(round(coord, 2) for coord in b.get("bbox", (0, 0, 0, 0)))
            block_spans: list[TextSpan] = []
            block_lines_text: list[str] = []
            block_font_sizes: list[float] = []
            block_bold_count = 0

            for line in b.get("lines", []):
                line_spans_text: list[str] = []
                line_parts: list[str] = []
                prev_span_bbox = None
                for s in line.get("spans", []):
                    span_text = s.get("text", "")
                    if not span_text:
                        continue

                    span_size = round(s.get("size", 10.0), 2)
                    span_font = s.get("font", "")
                    flags = s.get("flags", 0)

                    # Bold: bit 4 or font name contains bold / black / heavy
                    is_bold = bool(
                        (flags & (1 << 4))
                        or any(w in span_font.lower() for w in ("bold", "black", "heavy"))
                    )
                    # Italic: bit 1 or font name contains italic / oblique
                    is_italic = bool(
                        (flags & (1 << 1))
                        or any(w in span_font.lower() for w in ("italic", "oblique"))
                    )

                    span_bbox = tuple(round(coord, 2) for coord in s.get("bbox", (0, 0, 0, 0)))
                    if prev_span_bbox is not None and line_parts:
                        gap = span_bbox[0] - prev_span_bbox[2]
                        if (
                            gap > span_size * 0.25
                            and not line_parts[-1].endswith(" ")
                            and not span_text.startswith(" ")
                        ):
                            line_parts.append(" ")
                    line_parts.append(span_text)
                    prev_span_bbox = span_bbox

                    block_spans.append(
                        TextSpan(
                            text=span_text,
                            font=span_font,
                            size=span_size,
                            is_bold=is_bold,
                            is_italic=is_italic,
                            bbox=span_bbox,  # type: ignore[arg-type]
                            page=page_num,
                        )
                    )
                    line_spans_text.append(span_text)
                    block_font_sizes.append(span_size)
                    font_sizes.append(span_size)
                    if is_bold:
                        block_bold_count += 1

                if line_parts:
                    block_lines_text.append("".join(line_parts).strip())

            full_block_text = "\n".join(block_lines_text).strip()
            if not full_block_text:
                continue

            avg_font_size = (
                sum(block_font_sizes) / len(block_font_sizes) if block_font_sizes else 10.0
            )
            is_majority_bold = (block_bold_count / len(block_spans)) > 0.5 if block_spans else False

            raw_blocks.append(
                TextBlock(
                    text=full_block_text,
                    page=page_num,
                    block_index=block_global_idx,
                    spans=block_spans,
                    bbox=block_bbox,  # type: ignore[arg-type]
                    font_size=avg_font_size,
                    is_bold=is_majority_bold,
                )
            )
            all_raw_paragraphs.append(full_block_text)
            block_global_idx += 1

    # Compute body font size (most common font size)
    body_font_size = Counter(font_sizes).most_common(1)[0][0] if font_sizes else 10.0

    # Classify headings
    for block in raw_blocks:
        block.is_heading = _detect_heading(
            block.text,
            block.font_size,
            block.is_bold,
            body_font_size,
        )

    meta = {
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
        "page_count": doc.page_count,
        "body_font_size": body_font_size,
    }
    page_count = doc.page_count
    doc.close()

    return ExtractionResult(
        raw_text="\n\n".join(all_raw_paragraphs),
        blocks=raw_blocks,
        page_count=page_count,
        is_scanned=False,
        is_encrypted=False,
        is_corrupt=False,
        metadata=meta,
    )
