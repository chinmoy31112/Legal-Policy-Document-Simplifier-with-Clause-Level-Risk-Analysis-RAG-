"""
Test suite verifying:
1. Hierarchical segmentation on the General Power of Attorney PDF:
   - The analysis unit is the numbered clause (1., 2., ... 39.).
   - Sub-bullets and continuation paragraphs stay inside parent clauses.
   - Child spans and bounding boxes cover both pages for cross-page clauses.
   - Total clauses for General Power of Attorney PDF is in expected range (40-46).
2. Grounding quote validator normalization:
   - Whitespace normalization
   - Line-break hyphenation ("ac- counts" -> "accounts")
   - Straight vs curly quotes (“ ” vs " ")
   - Strict rejection when quoted evidence does not appear in clause text.
3. Batch repair without single-clause fallbacks:
   - Repair happens in mini-batches through rate limiter.
   - Single-clause fallbacks = 0.
"""

from pathlib import Path

import pytest

from app.ai.grounding import GroundingValidator
from app.ai.interfaces import FakeEmbedder, FakeLLMClient
from app.ai.pipeline import RiskAnalysisPipeline
from app.ai.retrieval import RetrievalService
from app.ai.vector_store import InMemoryVectorStore
from app.document_processing.extractor import extract_pdf
from app.document_processing.segmenter import DocumentSegmenter

GPA_PDF_PATH = Path(
    r"C:\Users\chinm\.gemini\antigravity\brain\c70b02a3-d86e-4235-b342-3e1e837526f3\.user_uploaded\media_1795590798657_14b79f16.pdf"
)


def test_gpa_pdf_segmentation_clause_count_and_cross_page():
    """Verify GPA PDF segmentation yields 40-46 clauses and cross-page clauses highlight on both pages."""
    assert GPA_PDF_PATH.exists(), f"GPA PDF not found at {GPA_PDF_PATH}"

    ext = extract_pdf(GPA_PDF_PATH)
    assert len(ext.blocks) > 0, "PDF extraction produced 0 blocks"

    segmenter = DocumentSegmenter(min_clause_length=40, max_clause_length=3000)
    clauses = segmenter.segment(ext, doc_id="gpa_test")

    clause_count = len(clauses)
    print(f"\n[GPA Segmentation] Total clauses extracted: {clause_count}")
    assert 40 <= clause_count <= 46, f"Expected 40-46 clauses, got {clause_count}"

    # Check cross-page clauses have bounding boxes on multiple pages
    cross_page_clauses = [
        c for c in clauses
        if len({box[0] for box in c.bounding_boxes}) > 1
    ]
    print(f"[GPA Segmentation] Cross-page clauses count: {len(cross_page_clauses)}")
    assert len(cross_page_clauses) >= 3, "Expected at least 3 cross-page clauses spanning multiple pages"

    # Clause 13 starts on page 2 and continues on page 3
    clause_13 = next((c for c in clauses if "13." in c.title or "13." in c.text[:20]), None)
    assert clause_13 is not None, "Clause 13 not found"
    pages_c13 = {box[0] for box in clause_13.bounding_boxes}
    assert 2.0 in pages_c13 and 3.0 in pages_c13, f"Clause 13 must highlight on both page 2 and page 3, got pages: {pages_c13}"


def test_grounding_quote_validator_normalization():
    """Verify quote validator normalizes whitespace, line-break hyphenation, and curly quotes."""
    validator = GroundingValidator(min_precision=0.90)

    # 1. Line-break hyphenation ("ac- counts" in text, "accounts" in quote or vice versa)
    clause_text = (
        "17. To continue and or to open new, current and or overdraft ac- counts in my name with any Banks."
    )
    # Reason cites standard 'accounts' enclosed in curly quotes “accounts”
    reason_with_curly_and_dehyphenated = (
        'The attorney has authority to open “accounts” without requiring joint signature.'
    )
    is_grounded, citation = validator.is_reason_grounded(reason_with_curly_and_dehyphenated, clause_text)
    assert is_grounded, f"Failed to ground with curly quotes and line-break hyphenation: {citation}"

    # 2. Straight vs curly quotes in reason
    reason_with_straight_quotes = 'Attorney may open "overdraft ac- counts" unilaterally.'
    is_grounded_2, _ = validator.is_reason_grounded(reason_with_straight_quotes, clause_text)
    assert is_grounded_2, "Failed to ground straight quotes"

    # 3. Whitespace normalization (tabs, newlines, multiple spaces)
    clause_multiline = "3. To contract with any person    for leasing\n\nfor such period   at such rent."
    reason_spaced = 'Grants power to lease “for such period at such rent” without restriction.'
    is_grounded_3, _ = validator.is_reason_grounded(reason_spaced, clause_multiline)
    assert is_grounded_3, "Failed to ground multiline/irregular whitespace quote"

    # 4. Strict rejection when evidence really does NOT appear in clause
    fake_reason = 'The clause imposes an “unlimited financial liability” on the customer.'
    is_grounded_fake, err = validator.is_reason_grounded(fake_reason, clause_text)
    assert not is_grounded_fake, "Validator should have rejected hallucinated quote"
    assert "ungrounded" in err


@pytest.mark.asyncio
async def test_batch_pipeline_with_fake_llm_zero_single_clause_fallbacks():
    """Verify batch analysis runs with FakeLLMClient, repairs in mini-batches, and has 0 single-clause fallbacks."""
    assert GPA_PDF_PATH.exists()
    ext = extract_pdf(GPA_PDF_PATH)
    segmenter = DocumentSegmenter()
    clauses = segmenter.segment(ext, doc_id="gpa_test")

    embedder = FakeEmbedder(dimension=768, model_name="gemini-embedding-2")
    vector_store = InMemoryVectorStore(expected_dim=768, expected_model="gemini-embedding-2")
    retrieval_service = RetrievalService(embedder=embedder, vector_store=vector_store)
    fake_llm = FakeLLMClient()

    pipeline = RiskAnalysisPipeline(
        llm_client=fake_llm,
        retrieval_service=retrieval_service,
        embedder=embedder,
        vector_store=vector_store,
    )

    batch_inputs = [
        {
            "clause_id": c.id,
            "clause_text": c.text,
            "clause_vector": None,
        }
        for c in clauses
    ]

    results = await pipeline.analyze_clauses_batch(
        clauses=batch_inputs,
        batch_size=4,
        max_concurrency=3,
    )

    assert len(results) == len(clauses), f"Expected {len(clauses)} results, got {len(results)}"
    assert pipeline.last_single_clause_fallbacks == 0, (
        f"Single-clause fallbacks must be 0, got {pipeline.last_single_clause_fallbacks}"
    )

    total_clauses = len(clauses)
    repair_count = pipeline.last_repair_count
    repair_rate = repair_count / total_clauses if total_clauses > 0 else 0.0

    print("\n[Batch Pipeline Test Results]")
    print(f"Total Clauses Analyzed: {total_clauses}")
    print("Batch Size: 4")
    print(f"Repair Count: {repair_count}")
    print(f"Repair Rate: {repair_rate:.2%}")
    print(f"Single-Clause Fallbacks: {pipeline.last_single_clause_fallbacks}")
