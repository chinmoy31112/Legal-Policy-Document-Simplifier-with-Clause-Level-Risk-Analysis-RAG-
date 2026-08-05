"""
Document processing package.
"""

from app.document_processing.extractor import extract_pdf, ExtractionResult, TextBlock
from app.document_processing.formats import extract_document
from app.document_processing.segmenter import DocumentSegmenter, ClauseSegment

__all__ = [
    "extract_pdf",
    "extract_document",
    "ExtractionResult",
    "TextBlock",
    "DocumentSegmenter",
    "ClauseSegment",
]
