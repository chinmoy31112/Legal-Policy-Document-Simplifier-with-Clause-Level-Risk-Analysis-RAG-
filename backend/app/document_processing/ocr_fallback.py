"""
OCR fallback for scanned PDFs using pytesseract.

When PyMuPDF detects a scanned PDF (image-only pages), this module
renders each page as an image and runs Tesseract OCR to extract text.
"""

from pathlib import Path
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)

# Lazy imports — these dependencies may not be installed
_fitz = None
_pytesseract = None
_pil_image = None


def _lazy_imports():
    """Import heavy dependencies only when needed."""
    global _fitz, _pytesseract, _pil_image
    if _fitz is None:
        try:
            import fitz
            _fitz = fitz
        except ImportError:
            logger.warning("pymupdf_not_installed")
    if _pytesseract is None:
        try:
            import pytesseract
            _pytesseract = pytesseract
        except ImportError:
            logger.warning("pytesseract_not_installed")
    if _pil_image is None:
        try:
            from PIL import Image
            _pil_image = Image
        except ImportError:
            logger.warning("pillow_not_installed")


@dataclass
class OCRResult:
    """Result of OCR processing."""
    raw_text: str
    page_texts: list[str] = field(default_factory=list)
    page_count: int = 0
    confidence: float = 0.0
    errors: list[str] = field(default_factory=list)


def is_ocr_available() -> bool:
    """Check if OCR dependencies are installed and Tesseract is accessible."""
    _lazy_imports()
    if _pytesseract is None:
        return False
    try:
        _pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def ocr_pdf(file_path: str | Path, dpi: int = 300, lang: str = "eng") -> OCRResult:
    """
    Extract text from a scanned PDF using OCR.

    Renders each page as an image at the specified DPI and runs
    Tesseract OCR on each image.

    Args:
        file_path: Path to the scanned PDF file.
        dpi: Resolution for rendering pages (higher = better quality, slower).
        lang: Tesseract language code (e.g., 'eng', 'fra', 'deu').

    Returns:
        OCRResult with extracted text and per-page results.
    """
    _lazy_imports()

    if _fitz is None:
        return OCRResult(
            raw_text="",
            errors=["PyMuPDF is not installed. Cannot render PDF pages for OCR."],
        )

    if _pytesseract is None:
        return OCRResult(
            raw_text="",
            errors=[
                "pytesseract is not installed. OCR is unavailable. "
                "Install with: pip install pytesseract Pillow"
            ],
        )

    if not is_ocr_available():
        return OCRResult(
            raw_text="",
            errors=[
                "Tesseract OCR is not installed or not in PATH. "
                "Download from: https://github.com/tesseract-ocr/tesseract"
            ],
        )

    file_path = Path(file_path)
    if not file_path.exists():
        return OCRResult(raw_text="", errors=[f"File not found: {file_path}"])

    try:
        doc = _fitz.open(str(file_path))
    except Exception as e:
        return OCRResult(raw_text="", errors=[f"Failed to open PDF: {e}"])

    page_texts: list[str] = []
    errors: list[str] = []

    for page_idx in range(doc.page_count):
        try:
            page = doc[page_idx]
            # Render page as a pixmap (image)
            zoom = dpi / 72  # 72 is the default PDF resolution
            matrix = _fitz.Matrix(zoom, zoom)
            pixmap = page.get_pixmap(matrix=matrix)

            # Convert pixmap to PIL Image
            img_data = pixmap.tobytes("png")
            import io
            img = _pil_image.open(io.BytesIO(img_data))

            # Run OCR
            text = _pytesseract.image_to_string(img, lang=lang)
            page_texts.append(text.strip())

        except Exception as e:
            error_msg = f"OCR failed on page {page_idx + 1}: {e}"
            logger.warning("ocr_page_error", page=page_idx + 1, error=str(e))
            errors.append(error_msg)
            page_texts.append("")

    doc.close()

    raw_text = "\n\n".join(page_texts)

    logger.info(
        "ocr_completed",
        path=str(file_path),
        pages=len(page_texts),
        chars=len(raw_text),
        errors=len(errors),
    )

    return OCRResult(
        raw_text=raw_text,
        page_texts=page_texts,
        page_count=len(page_texts),
        errors=errors,
    )
