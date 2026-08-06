"""
Multi-format document text extraction.

Supports: PDF, DOCX, TXT, Markdown, JSON.
Dispatches to the appropriate extractor based on file extension.
"""

import json
from pathlib import Path

from app.core.logging import get_logger
from app.document_processing.extractor import ExtractionResult, extract_pdf
from app.document_processing.ocr_fallback import ocr_pdf, is_ocr_available

logger = get_logger(__name__)


def extract_docx(file_path: str | Path) -> ExtractionResult:
    """
    Extract text from a DOCX file using python-docx.

    Preserves paragraph structure and detects headings from styles.
    """
    from app.document_processing.extractor import TextBlock

    file_path = Path(file_path)
    if not file_path.exists():
        return ExtractionResult(
            raw_text="", errors=[f"File not found: {file_path}"]
        )

    try:
        from docx import Document as DocxDocument
    except ImportError:
        return ExtractionResult(
            raw_text="",
            errors=["python-docx is not installed. Cannot extract DOCX text."],
        )

    try:
        doc = DocxDocument(str(file_path))
    except Exception as e:
        return ExtractionResult(raw_text="", errors=[f"Failed to open DOCX: {e}"])

    blocks: list[TextBlock] = []
    all_text_parts: list[str] = []

    for idx, paragraph in enumerate(doc.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue

        # Detect headings from paragraph styles
        style_name = paragraph.style.name if paragraph.style else ""
        is_heading = style_name.lower().startswith("heading") or style_name.lower().startswith("title")

        # Check for bold runs
        is_bold = any(run.bold for run in paragraph.runs if run.bold is not None)

        block = TextBlock(
            text=text,
            page_number=1,  # DOCX doesn't have page numbers directly
            block_index=idx,
            is_heading=is_heading,
            is_bold=is_bold,
        )
        blocks.append(block)
        all_text_parts.append(text)

    raw_text = "\n\n".join(all_text_parts)

    # Extract metadata
    core_properties = doc.core_properties
    metadata = {
        "title": core_properties.title or "",
        "author": core_properties.author or "",
        "subject": core_properties.subject or "",
    }

    logger.info(
        "docx_extracted",
        path=str(file_path),
        paragraphs=len(blocks),
        chars=len(raw_text),
    )

    return ExtractionResult(
        raw_text=raw_text,
        blocks=blocks,
        page_count=1,
        metadata=metadata,
    )


def extract_text_file(file_path: str | Path) -> ExtractionResult:
    """Extract text from a plain text or markdown file."""
    from app.document_processing.extractor import TextBlock

    file_path = Path(file_path)
    if not file_path.exists():
        return ExtractionResult(
            raw_text="", errors=[f"File not found: {file_path}"]
        )

    try:
        raw_text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw_text = file_path.read_text(encoding="latin-1")
        except Exception as e:
            return ExtractionResult(raw_text="", errors=[f"Failed to read file: {e}"])

    # Split into paragraphs
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    blocks = [
        TextBlock(
            text=para,
            page_number=1,
            block_index=idx,
            is_heading=para.startswith("#") or para.isupper(),
        )
        for idx, para in enumerate(paragraphs)
    ]

    logger.info(
        "text_extracted",
        path=str(file_path),
        paragraphs=len(blocks),
        chars=len(raw_text),
    )

    return ExtractionResult(
        raw_text=raw_text,
        blocks=blocks,
        page_count=1,
    )


def extract_json_file(file_path: str | Path) -> ExtractionResult:
    """
    Extract text from a JSON file (knowledge base format).

    Expects the JSON to contain a 'clauses' or 'content' field.
    """
    from app.document_processing.extractor import TextBlock

    file_path = Path(file_path)
    if not file_path.exists():
        return ExtractionResult(
            raw_text="", errors=[f"File not found: {file_path}"]
        )

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        return ExtractionResult(raw_text="", errors=[f"Failed to parse JSON: {e}"])

    blocks: list[TextBlock] = []
    all_text_parts: list[str] = []

    if isinstance(data, dict):
        # Handle knowledge base format with 'clauses' array
        clauses = data.get("clauses", data.get("sections", []))
        if isinstance(clauses, list):
            for idx, clause in enumerate(clauses):
                if isinstance(clause, dict):
                    title = clause.get("title", clause.get("heading", ""))
                    content = clause.get("content", clause.get("text", ""))
                    text = f"{title}\n{content}" if title else content
                else:
                    text = str(clause)

                if text.strip():
                    block = TextBlock(
                        text=text.strip(),
                        page_number=1,
                        block_index=idx,
                        is_heading=False,
                    )
                    blocks.append(block)
                    all_text_parts.append(text.strip())
        elif "content" in data:
            all_text_parts.append(str(data["content"]))
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            text = str(item) if not isinstance(item, dict) else json.dumps(item)
            if text.strip():
                blocks.append(TextBlock(text=text.strip(), page_number=1, block_index=idx))
                all_text_parts.append(text.strip())

    raw_text = "\n\n".join(all_text_parts)
    metadata = {"format": "json"}
    if isinstance(data, dict):
        metadata["title"] = data.get("title", data.get("document_type", ""))
        metadata["document_type"] = data.get("document_type", "")

    return ExtractionResult(
        raw_text=raw_text,
        blocks=blocks,
        page_count=1,
        metadata=metadata,
    )


def extract_document(file_path: str | Path) -> ExtractionResult:
    """
    Extract text from a document file based on its extension.

    Dispatches to the appropriate extractor. For PDFs detected as scanned,
    falls back to OCR if available.

    Args:
        file_path: Path to the document file.

    Returns:
        ExtractionResult with extracted text and metadata.
    """
    file_path = Path(file_path)
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        result = extract_pdf(file_path)

        # If the PDF has very little text (whether scanned or vector outlines), try OCR
        if len(result.raw_text.strip()) < 100:
            if is_ocr_available():
                logger.info("ocr_fallback_triggered", path=str(file_path))
                ocr_result = ocr_pdf(file_path)
                if ocr_result.raw_text.strip():
                    result.raw_text = ocr_result.raw_text
                    result.errors.extend(ocr_result.errors)
                else:
                    result.errors.append(
                        "OCR produced no text. The document may be damaged or unreadable."
                    )
            else:
                result.errors.append(
                    "Unreadable PDF detected (likely scanned or vector paths) but OCR is not available. "
                    "Install Tesseract OCR to process this document."
                )

        return result

    elif ext == ".docx":
        return extract_docx(file_path)

    elif ext in (".txt", ".md"):
        return extract_text_file(file_path)

    elif ext == ".json":
        return extract_json_file(file_path)

    else:
        return ExtractionResult(
            raw_text="",
            errors=[f"Unsupported file format: {ext}"],
        )
