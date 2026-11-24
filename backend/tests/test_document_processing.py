"""
Unit tests for Document Processing (PyMuPDF Extraction and Clause Segmentation).

Tests span extraction, bounding boxes, scanned-PDF detection, corrupted/encrypted
file handling, hierarchical parent-child clause segmentation, and fallback mechanisms.
"""

from pathlib import Path

import pytest

from app.document_processing import (
    Clause,
    CorruptDocumentError,
    EncryptedDocumentError,
    ExtractionResult,
    ScannedDocumentError,
    TextBlock,
    extract_pdf,
    segment_document,
)

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent / "tests" / "eval_data" / "segmentation_set"
)
CORRUPT_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "eval_data" / "corrupt_set"


def test_extract_valid_pdf_with_spans_and_bboxes():
    """Verify PyMuPDF extraction captures text, fonts, headings, and bounding boxes."""
    pdf_path = FIXTURES_DIR / "doc_tos.pdf"
    assert pdf_path.exists(), "Test fixture doc_tos.pdf must exist"

    result = extract_pdf(pdf_path)

    assert result.is_scanned is False
    assert result.is_encrypted is False
    assert result.is_corrupt is False
    assert result.page_count == 1
    assert "TERMS OF SERVICE" in result.raw_text
    assert len(result.blocks) > 0

    # Verify blocks have valid bounding boxes and spans
    for block in result.blocks:
        assert block.page == 1
        assert len(block.bbox) == 4
        assert block.bbox[2] > block.bbox[0]  # x1 > x0
        assert block.bbox[3] > block.bbox[1]  # y1 > y0
        assert len(block.spans) > 0
        for span in block.spans:
            assert span.page == 1
            assert span.size > 0


def test_segment_document_creates_valid_clauses():
    """Verify clause segmentation produces well-formed Clause objects with bboxes and hashes."""
    pdf_path = FIXTURES_DIR / "doc_tos.pdf"
    extraction = extract_pdf(pdf_path)
    clauses = segment_document(extraction, doc_id="tos_001")

    # Should detect 5 numbered clauses
    assert len(clauses) >= 4, f"Expected at least 4 clauses, got {len(clauses)}"

    # Check bounding box validity: >= 98% must have non-empty bounding boxes
    valid_bbox_count = sum(1 for c in clauses if c.bounding_boxes and len(c.bounding_boxes) > 0)
    bbox_ratio = valid_bbox_count / len(clauses)
    assert bbox_ratio >= 0.98, f"Bounding box ratio {bbox_ratio} was below 0.98"

    for c in clauses:
        assert isinstance(c, Clause)
        assert c.id.startswith("cls_tos_001_")
        assert c.order > 0
        assert len(c.text.strip()) > 0
        assert c.page == 1
        assert len(c.text_hash) == 64  # SHA-256 length
        assert c.text_hash == c.compute_hash()


def test_hierarchical_parent_child_linking():
    """Verify nested clauses (1.1 -> 1.1(a)) correctly link parent_id."""
    # Synthesize structured blocks with hierarchy
    blocks = [
        TextBlock(
            text="Section 1. Core Obligations and Services",
            page=1,
            block_index=0,
            is_heading=True,
            font_size=14.0,
            bbox=(72.0, 100.0, 500.0, 120.0),
        ),
        TextBlock(
            text="1.1 Service Level Guarantee\nVendor shall maintain 99.9% uptime across all regions.",
            page=1,
            block_index=1,
            is_heading=True,
            font_size=12.0,
            bbox=(72.0, 130.0, 500.0, 160.0),
        ),
        TextBlock(
            text="(a) Downtime Credits\nIf uptime falls below 99.9%, Customer receives a 10% credit.",
            page=1,
            block_index=2,
            is_heading=False,
            font_size=10.0,
            bbox=(72.0, 170.0, 500.0, 200.0),
        ),
    ]

    extraction = ExtractionResult(
        raw_text="\n\n".join(b.text for b in blocks),
        blocks=blocks,
        page_count=1,
    )

    clauses = segment_document(extraction, doc_id="hier_001")
    assert len(clauses) == 3

    # Section 1 (Level 1)
    c1 = clauses[0]
    assert c1.parent_id is None

    # Section 1.1 (Level 2) -> parent is Section 1
    c2 = clauses[1]
    assert c2.parent_id == c1.id

    # (a) Downtime Credits (Level 3) -> parent is Section 1.1
    c3 = clauses[2]
    assert c3.parent_id == c2.id


def test_scanned_pdf_detection_and_rejection():
    """Verify image-only scanned PDFs are flagged or rejected cleanly."""
    scanned_path = CORRUPT_DIR / "scanned_image.pdf"
    assert scanned_path.exists()

    result = extract_pdf(scanned_path, raise_on_error=False)
    assert result.is_scanned is True
    assert len(result.errors) > 0
    assert "Scanned PDF detected" in result.errors[0]

    with pytest.raises(ScannedDocumentError):
        extract_pdf(scanned_path, raise_on_error=True)


def test_encrypted_pdf_handling():
    """Verify encrypted password-locked PDFs are rejected with clean error."""
    enc_path = CORRUPT_DIR / "encrypted_file.pdf"
    assert enc_path.exists()

    result = extract_pdf(enc_path, raise_on_error=False)
    assert result.is_encrypted is True
    assert len(result.errors) > 0

    with pytest.raises(EncryptedDocumentError):
        extract_pdf(enc_path, raise_on_error=True)


def test_empty_and_corrupt_file_handling():
    """Verify empty and corrupt PDFs result in zero unhandled exceptions."""
    empty_path = CORRUPT_DIR / "empty_file.pdf"
    corrupt_path = CORRUPT_DIR / "corrupt_file.pdf"

    # Empty file
    res_empty = extract_pdf(empty_path, raise_on_error=False)
    assert res_empty.is_corrupt is True
    with pytest.raises(CorruptDocumentError):
        extract_pdf(empty_path, raise_on_error=True)

    # Corrupt file
    res_corrupt = extract_pdf(corrupt_path, raise_on_error=False)
    assert res_corrupt.is_corrupt is True
    with pytest.raises(CorruptDocumentError):
        extract_pdf(corrupt_path, raise_on_error=True)


def test_fallback_segmentation_on_unnumbered_text():
    """Verify fallback segmenter correctly chunks plain unnumbered paragraphs."""
    plain_text = (
        "This agreement is entered into between Party A and Party B on this day.\n\n"
        "Party A shall deliver the consulting services described in the schedule.\n\n"
        "All fees shall be paid within thirty calendar days of invoice receipt.\n\n"
        "Either party may terminate this agreement upon thirty days written notice."
    )
    extraction = ExtractionResult(raw_text=plain_text, blocks=[], page_count=1)
    clauses = segment_document(extraction, doc_id="plain_001")

    assert len(clauses) >= 3
    for c in clauses:
        assert c.order > 0
        assert len(c.text_hash) == 64
        assert len(c.bounding_boxes) > 0
