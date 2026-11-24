"""
Document processing package.

Exports pure functional interfaces for text extraction, layout analysis,
and hierarchical clause segmentation.
"""

from app.document_processing.extractor import (
    CorruptDocumentError,
    DocumentProcessingError,
    EncryptedDocumentError,
    ScannedDocumentError,
    extract_pdf,
    is_scanned_pdf,
)
from app.document_processing.schema import (
    Clause,
    ExtractionResult,
    TextBlock,
    TextSpan,
)
from app.document_processing.segmenter import (
    DocumentSegmenter,
    segment_document,
)

extract_document = extract_pdf

__all__ = [
    "Clause",
    "ExtractionResult",
    "TextBlock",
    "TextSpan",
    "extract_pdf",
    "extract_document",
    "is_scanned_pdf",
    "segment_document",
    "DocumentSegmenter",
    "DocumentProcessingError",
    "ScannedDocumentError",
    "EncryptedDocumentError",
    "CorruptDocumentError",
]
