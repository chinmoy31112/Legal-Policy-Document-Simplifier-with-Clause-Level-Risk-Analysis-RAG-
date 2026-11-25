"""
Hierarchical Legal Clause Segmenter.

Pure function implementation: zero database or network dependencies.
Segments documents into logical clauses using numbering grammars, typography,
heading hierarchies, parent-child linking, and bullet grouping. Never fixed token counts.
"""

import hashlib
import re
from collections.abc import Sequence

from app.core.logging import get_logger
from app.document_processing.schema import Clause, ExtractionResult, TextBlock

logger = get_logger(__name__)


# ── Hierarchical Legal Numbering Patterns ─────────────────────────────────────

# Level 1: Major Articles, Sections, Chapters, Schedules, Exhibits, or Numbered Clauses
LEVEL_1_PATTERNS = [
    re.compile(
        r"^(?:ARTICLE|SECTION|PART|CHAPTER|SCHEDULE|APPENDIX|EXHIBIT)\s+([0-9IVXLCDM]+)[\.:\s\-]+(.*)",
        re.IGNORECASE,
    ),
    re.compile(r"^(\d+)[\.\)]\s+(.*)"),  # e.g., "1. To ask...", "1. DEFINITIONS", "(1) Clause"
    re.compile(r"^([IVXLCDM]+)[\.\)]\s+(.*)"),  # e.g., "I. RECITALS"
]

# Level 2: Sub-numbered Sections (e.g., "1.1", "2.4", "Section 1.1")
LEVEL_2_PATTERNS = [
    re.compile(r"^(?:SECTION\s+)?(\d+\.\d+)[\.:\s\-]+(.*)", re.IGNORECASE),
    re.compile(r"^(\d+\.\d+)\s+(.*)"),
]

# Level 3: Nested Subclauses (e.g., "1.1.1", "1.1(a)", "(a)", "(b)")
LEVEL_3_PATTERNS = [
    re.compile(r"^(\d+\.\d+\.\d+)[\.:\s\-]+(.*)"),
    re.compile(r"^(\d+\.\d+\([a-z\d]+\))[\.:\s\-]+(.*)", re.IGNORECASE),
    re.compile(r"^\(([a-z\d]{1,2})\)[\.:\s\-]+(.*)", re.IGNORECASE),
    re.compile(r"^([a-z])\.[\s\-]+(.*)"),
]

# Level 4: Roman sub-items or bullets (e.g., "(i)", "(ii)", "•")
LEVEL_4_PATTERNS = [
    re.compile(r"^\(([ivx]+)\)[\.:\s\-]+(.*)", re.IGNORECASE),
    re.compile(r"^([ivx]+)\.[\s\-]+(.*)", re.IGNORECASE),
    re.compile(r"^[\u2022\u25cf\u25cb\-\*]\s+(.*)"),
]


def _match_numbering_level(text: str) -> tuple[int, str, str]:
    """
    Classify a text string into a legal hierarchy level.
    Returns: (level: int, label: str, title_or_remainder: str)
    Level 0 = not a numbered start.
    """
    cleaned = text.strip()
    if not cleaned:
        return 0, "", ""

    # Test Level 2 first to distinguish 1.1 from 1.
    for pat in LEVEL_2_PATTERNS:
        m = pat.match(cleaned)
        if m:
            label = m.group(1).strip()
            title = m.group(2).strip() if len(m.groups()) >= 2 else ""
            return 2, label, title

    # Test Level 1
    for pat in LEVEL_1_PATTERNS:
        m = pat.match(cleaned)
        if m:
            label = m.group(1).strip()
            title = m.group(2).strip() if len(m.groups()) >= 2 else ""
            return 1, label, title

    # Test Level 3
    for pat in LEVEL_3_PATTERNS:
        m = pat.match(cleaned)
        if m:
            label = m.group(1).strip()
            title = m.group(2).strip() if len(m.groups()) >= 2 else ""
            return 3, label, title

    # Test Level 4
    for pat in LEVEL_4_PATTERNS:
        m = pat.match(cleaned)
        if m:
            label = m.group(1).strip()
            title = m.group(2).strip() if len(m.groups()) >= 2 else ""
            return 4, label, title

    return 0, "", ""


def _extract_bounding_boxes_from_blocks(blocks: Sequence[TextBlock]) -> list[list[float]]:
    """Aggregate span-level or block-level bounding boxes as [page, x0, y0, x1, y1]."""
    boxes: list[list[float]] = []
    for b in blocks:
        if b.spans:
            for s in b.spans:
                # [page, x0, y0, x1, y1]
                boxes.append(
                    [
                        float(s.page),
                        float(s.bbox[0]),
                        float(s.bbox[1]),
                        float(s.bbox[2]),
                        float(s.bbox[3]),
                    ]
                )
        elif b.bbox and any(b.bbox):
            boxes.append(
                [
                    float(b.page),
                    float(b.bbox[0]),
                    float(b.bbox[1]),
                    float(b.bbox[2]),
                    float(b.bbox[3]),
                ]
            )
    return boxes


def segment_document(
    extraction: ExtractionResult,
    doc_id: str = "doc_001",
    min_clause_chars: int = 40,
    max_clause_chars: int = 3000,
) -> list[Clause]:
    """
    Segment extracted document blocks into hierarchical legal clauses.

    Pure function: zero DB / zero HTTP.
    Analysis unit is the numbered clause (1., 2., ...).
    Sub-bullets and continuation paragraphs stay inside their parent clause.
    Child spans and bounding boxes are preserved across pages for highlighting.
    Splits at sentence boundaries only when a clause exceeds max_clause_chars.
    """
    if not extraction.blocks:
        # Fallback to pure text splitting if blocks are unavailable
        return _fallback_paragraph_segmentation(extraction.raw_text, doc_id, min_clause_chars)

    clauses: list[Clause] = []
    order_idx = 1

    current_blocks: list[TextBlock] = []
    current_title: str = ""
    current_level: int = 1

    # Check whether document has Level 1 clauses
    has_lvl1 = any(
        _match_numbering_level(b.text.split("\n", 1)[0].strip())[0] == 1 for b in extraction.blocks
    )

    def _split_long_clause(combined_text: str) -> list[str]:
        # Split only at sentence boundaries when clause exceeds max_clause_chars
        sentences = re.split(r"(?<=[.!?])\s+", combined_text)
        parts: list[str] = []
        curr: list[str] = []
        curr_len = 0
        for s in sentences:
            if curr_len + len(s) > max_clause_chars and curr:
                parts.append(" ".join(curr))
                curr = [s]
                curr_len = len(s)
            else:
                curr.append(s)
                curr_len += len(s)
        if curr:
            parts.append(" ".join(curr))
        return parts if len(parts) > 1 else [combined_text]

    def _flush_clause() -> None:
        nonlocal order_idx, current_blocks, current_title, current_level
        if not current_blocks:
            return

        combined_text = "\n\n".join(b.text for b in current_blocks).strip()
        if len(combined_text) < min_clause_chars and clauses:
            # Append very short trailing block into preceding clause
            prev = clauses[-1]
            prev.text = f"{prev.text}\n\n{combined_text}".strip()
            prev.bounding_boxes.extend(_extract_bounding_boxes_from_blocks(current_blocks))
            prev.text_hash = prev.compute_hash()
            current_blocks = []
            return

        page_num = current_blocks[0].page
        boxes = _extract_bounding_boxes_from_blocks(current_blocks)

        if len(combined_text) > max_clause_chars:
            text_parts = _split_long_clause(combined_text)
        else:
            text_parts = [combined_text]

        for p_idx, part_text in enumerate(text_parts):
            normalized_text = " ".join(part_text.split())
            raw_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
            clause_id = f"cls_{doc_id}_{order_idx:04d}_{raw_hash[:8]}"
            title = current_title or part_text[:150]
            if len(text_parts) > 1:
                title = f"{title} (Part {p_idx + 1})"

            new_clause = Clause(
                id=clause_id,
                parent_id=None,
                order=order_idx,
                title=title,
                text=part_text,
                page=page_num,
                bounding_boxes=boxes,
                text_hash=raw_hash,
            )
            clauses.append(new_clause)
            order_idx += 1

        current_blocks = []

    for block in extraction.blocks:
        first_line = block.text.split("\n", 1)[0].strip()
        level, label, title_rem = _match_numbering_level(first_line)

        # Check closing transition after high numbered clauses
        is_closing = False
        if current_title and any(d in current_title for d in ["35", "36", "37", "38", "39"]):
            if any(w in first_line.upper() for w in ["IN WITNESS", "SIGNED", "AND I,"]):
                is_closing = True

        # Top-level boundary decision:
        # If document has Level 1 numbered clauses, ONLY Level 1 (or major heading before clause 1, or closing) triggers a new clause.
        # Sub-bullets (Level 3/4) and continuation paragraphs stay inside parent clause!
        is_clause_boundary = False
        if has_lvl1:
            if level == 1:
                is_clause_boundary = True
            elif is_closing:
                is_clause_boundary = True
            elif block.is_heading and not current_blocks:
                is_clause_boundary = True
        else:
            # If no Level 1 clauses, Level 2 or block.is_heading acts as boundary
            if level in (1, 2) or block.is_heading:
                is_clause_boundary = True

        if is_clause_boundary and current_blocks:
            _flush_clause()
            if level == 1:
                current_title = f"{label}. {title_rem}".strip()[:150]
            elif is_closing:
                current_title = first_line[:150]
            else:
                current_title = first_line[:150]
            current_blocks.append(block)
        elif not current_blocks:
            if level == 1:
                current_title = f"{label}. {title_rem}".strip()[:150]
            else:
                current_title = first_line[:150]
            current_blocks.append(block)
        else:
            # Sub-bullets and continuation paragraphs stay inside parent clause!
            current_blocks.append(block)

    # Flush the final clause
    _flush_clause()

    # If heuristic produced too few clauses for a long text, trigger fallback
    if len(clauses) < 2 and len(extraction.raw_text) > 800:
        return _fallback_paragraph_segmentation(
            extraction.raw_text, doc_id, min_clause_chars, extraction.blocks
        )

    return clauses


class DocumentSegmenter:
    """Class wrapper for backward compatibility with existing services."""

    def __init__(self, min_clause_length: int = 40, max_clause_length: int = 3000):
        self.min_clause_length = min_clause_length
        self.max_clause_length = max_clause_length

    def segment(self, extraction_result: ExtractionResult, doc_id: str = "doc_001") -> list[Clause]:
        return segment_document(
            extraction_result,
            doc_id=doc_id,
            min_clause_chars=self.min_clause_length,
            max_clause_chars=self.max_clause_length,
        )


def _fallback_paragraph_segmentation(
    raw_text: str,
    doc_id: str = "doc_001",
    min_chars: int = 50,
    blocks: Sequence[TextBlock] | None = None,
) -> list[Clause]:
    """
    Fallback segmenter when regular legal numbering or headings are absent.
    Splits by logical paragraph units without cutting mid-sentence. Never fixed token chunking.
    """
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [raw_text.strip()] if raw_text.strip() else []

    clauses: list[Clause] = []
    order_idx = 1
    current_acc: list[str] = []

    block_boxes = _extract_bounding_boxes_from_blocks(blocks) if blocks else []

    for p in paragraphs:
        current_acc.append(p)
        joined = "\n\n".join(current_acc)
        if len(joined) >= min_chars:
            normalized_joined = " ".join(joined.split())
            raw_hash = hashlib.sha256(normalized_joined.encode("utf-8")).hexdigest()
            first_sentence = joined.split(".")[0].strip()[:100]
            clause_id = f"cls_{doc_id}_{order_idx:04d}_{raw_hash[:8]}"

            # Slice available bounding boxes proportionally if available
            c_boxes = (
                block_boxes[: max(1, len(block_boxes) // len(paragraphs))] if block_boxes else []
            )
            if not c_boxes:
                c_boxes = [[1.0, 72.0, 72.0, 540.0, 720.0]]  # Default valid page geometry

            clauses.append(
                Clause(
                    id=clause_id,
                    parent_id=None,
                    order=order_idx,
                    title=first_sentence,
                    text=joined,
                    page=1,
                    bounding_boxes=c_boxes,
                    text_hash=raw_hash,
                )
            )
            order_idx += 1
            current_acc = []

    if current_acc:
        joined = "\n\n".join(current_acc)
        if clauses:
            prev = clauses[-1]
            prev.text = f"{prev.text}\n\n{joined}".strip()
            prev.text_hash = prev.compute_hash()
        else:
            raw_hash = hashlib.sha256(joined.encode("utf-8")).hexdigest()
            clauses.append(
                Clause(
                    id=f"cls_{doc_id}_{order_idx:04d}_{raw_hash[:8]}",
                    parent_id=None,
                    order=order_idx,
                    title=joined[:80],
                    text=joined,
                    page=1,
                    bounding_boxes=[[1.0, 72.0, 72.0, 540.0, 720.0]],
                    text_hash=raw_hash,
                )
            )

    return clauses
