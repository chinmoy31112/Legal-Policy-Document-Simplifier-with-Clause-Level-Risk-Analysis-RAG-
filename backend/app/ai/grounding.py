"""
Grounding Validator for Clause Risk Reasons.

Enforces Non-Negotiable Rule 2:
Every risk reason must cite either an exact quote from the clause or a retrieved reference clause ID.
A validator rejects ungrounded claims and computes grounding precision.
"""

import re
from dataclasses import dataclass, field


@dataclass
class GroundingValidationResult:
    """Outcome of validating grounding citations for risk reasons."""
    is_valid: bool
    grounding_precision: float
    total_reasons: int
    grounded_reasons: int
    ungrounded_reasons: list[str] = field(default_factory=list)
    rejection_details: list[dict[str, str]] = field(default_factory=list)
    error_message: str | None = None


class GroundingValidator:
    """
    Validates that every risk reason is strictly grounded in:
    1. An exact verbatim quote from the clause text (enclosed in quotes or substring match).
    2. A retrieved reference clause ID (e.g. REF-LIAB-001).
    """

    def __init__(self, min_precision: float = 0.90):
        self.min_precision = min_precision

    def _normalize(self, text: str) -> str:
        """Normalize whitespace and lowercase for resilient matching."""
        return " ".join(text.lower().split())

    def is_reason_grounded(
        self,
        reason: str,
        clause_text: str,
        allowed_ref_ids: set[str] | list[str] | None = None,
    ) -> tuple[bool, str]:
        """
        Check if a single risk reason cites an exact quote or reference clause ID.

        Returns:
            (is_grounded, citation_type_or_error)
        """
        norm_clause = self._normalize(clause_text)
        norm_reason = self._normalize(reason)
        allowed_refs = {r.upper() for r in (allowed_ref_ids or [])}

        # 1. Check for Reference ID citation (e.g. REF-LIAB-001 or [REF-LIAB-001])
        ref_matches = re.findall(r"\b(REF-[A-Z0-9_-]+)\b", reason.upper())
        for ref_id in ref_matches:
            if not allowed_refs or ref_id in allowed_refs:
                return True, f"reference_id:{ref_id}"

        # 2. Check for explicit quotes enclosed in quotation marks
        quotes = re.findall(r'["\']([^"\']{4,})["\']', reason)
        for quote in quotes:
            norm_q = self._normalize(quote)
            if norm_q in norm_clause:
                return True, f"quote:{quote[:30]}"

        # 3. Check for verbatim 4+ word phrase overlaps from the clause
        clause_words = norm_clause.split()
        if len(clause_words) >= 4:
            for i in range(len(clause_words) - 3):
                quad = " ".join(clause_words[i : i + 4])
                if quad in norm_reason:
                    return True, f"verbatim_quad:{quad}"

        # 4. Check for key legal monetary / duration terms explicitly quoted
        specific_terms = re.findall(r"\b(\$\d+|\d+\s*months?|\d+\s*days?|100%|as is|sole remedy)\b", norm_clause)
        for term in specific_terms:
            if term in norm_reason:
                return True, f"specific_term:{term}"

        return False, "ungrounded: missing verbatim quote or valid reference ID citation"

    def validate(
        self,
        risk_reasons: list[str],
        clause_text: str,
        allowed_ref_ids: set[str] | list[str] | None = None,
    ) -> GroundingValidationResult:
        """
        Validate all risk reasons for a clause.
        Calculates grounding precision and returns validation result.
        """
        if not risk_reasons:
            return GroundingValidationResult(
                is_valid=True,
                grounding_precision=1.0,
                total_reasons=0,
                grounded_reasons=0,
            )

        grounded_count = 0
        ungrounded: list[str] = []
        details: list[dict[str, str]] = []

        for r in risk_reasons:
            is_gr, info = self.is_reason_grounded(r, clause_text, allowed_ref_ids)
            if is_gr:
                grounded_count += 1
            else:
                ungrounded.append(r)
                details.append({"reason": r, "cause": info})

        precision = round(grounded_count / len(risk_reasons), 4)
        is_valid = precision >= self.min_precision

        error_msg = None
        if not is_valid:
            error_msg = (
                f"Grounding validation failed: {len(ungrounded)} of {len(risk_reasons)} reasons "
                f"lack exact clause quotes or reference IDs. Precision: {precision:.2f} < {self.min_precision:.2f}. "
                f"Ungrounded: {ungrounded}"
            )

        return GroundingValidationResult(
            is_valid=is_valid,
            grounding_precision=precision,
            total_reasons=len(risk_reasons),
            grounded_reasons=grounded_count,
            ungrounded_reasons=ungrounded,
            rejection_details=details,
            error_message=error_msg,
        )

