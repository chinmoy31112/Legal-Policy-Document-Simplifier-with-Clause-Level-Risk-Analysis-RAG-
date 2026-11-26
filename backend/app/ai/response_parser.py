"""
Pydantic schemas for parsing and validating LLM structured JSON responses.

Adheres to:
- Rule 2: Grounding (reasons must cite quotes or reference IDs).
- Rule 3: Structured output validated against Pydantic schema with repair retries.
- Rule 4: Honest uncertainty (4 risk levels, indicative score/confidence, no "unenforceable").
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class GroundedReason(BaseModel):
    """Specific risk reason with explicit citation grounding."""

    reason: str = Field(..., description="Explanation of why the clause poses risk or imbalance.")
    quote: str | None = Field(None, description="Exact verbatim quote from the target clause.")
    reference_id: str | None = Field(
        None, description="Retrieved reference clause ID (e.g. REF-LIAB-001)."
    )


class LLMClauseAnalysis(BaseModel):
    """
    Structured clause risk analysis and plain English simplification.
    Validated schema for Gemini structured output.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    plain_english: str = Field(
        ...,
        alias="plain_english_summary",
        description="Clear, non-lawyer explanation of what this clause means and what rights it affects.",
    )
    risk_level: RiskLevel = Field(
        ...,
        alias="risk_category",
        description="Primary risk tier: LOW, MEDIUM, HIGH, or CRITICAL.",
    )
    risk_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Indicative risk score from 0 (completely standard/safe) to 100 (draconian/extreme).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        alias="confidence_score",
        description="Indicative confidence value from 0.0 to 1.0.",
    )
    risk_reasons: list[str] = Field(
        default_factory=list,
        description="List of specific risk reasons. Each reason must quote the clause or cite a reference ID.",
    )
    missing_protections: list[str] = Field(
        default_factory=list,
        description="Standard balanced protections or guardrails absent from this clause.",
    )
    suggested_rewrite: str | None = Field(
        None,
        description="Balanced, reciprocal alternative rewrite suitable for negotiation.",
    )
    legal_review_note: str | None = Field(
        None,
        alias="potential_legal_concern",
        description="Factual notice such as 'may warrant review by a qualified lawyer'. Never state 'unenforceable'.",
    )
    no_reference_used: bool = Field(
        False,
        description="True if evaluated under baseline fairness when no retrieved reference cleared threshold.",
    )

    # Backward compatibility properties
    @property
    def summary(self) -> str:
        return self.plain_english

    @property
    def plain_english_summary(self) -> str:
        return self.plain_english

    @property
    def risk_category(self) -> str:
        return self.risk_level

    @property
    def confidence_score(self) -> float:
        return self.confidence

    @property
    def potential_legal_concern(self) -> str | None:
        return self.legal_review_note


class LLMBatchClauseAnalysis(BaseModel):
    """Batch clause risk analysis result containing an array of clause analyses."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    items: list[LLMClauseAnalysis] = Field(
        ...,
        description="List of structured clause analyses matching the input batch order.",
    )


class DocumentRiskAnalysis(BaseModel):
    """Document-level aggregated risk assessment."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    overall_risk_score: int = Field(
        ..., ge=0, le=100, description="Indicative holistic risk score 0-100."
    )
    overall_risk_level: RiskLevel = Field(
        ..., description="Overall document risk tier (LOW, MEDIUM, HIGH, CRITICAL)."
    )
    executive_summary: str = Field(
        ...,
        alias="overall_summary",
        description="2-3 paragraph objective executive summary of document fairness and major concerns.",
    )
    key_risks: list[str] = Field(
        default_factory=list,
        description="Key contract-level red flags identified across all clauses.",
    )
    category_breakdown: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-category analysis summary (counts, avg scores, max risk level).",
    )
    negotiation_priorities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Top 3-5 clauses prioritized for negotiation or counsel review.",
    )
    disclaimer: str = Field(
        default="This analysis provides informational document simplification and risk assessment only. It does not constitute legal advice. Review by a qualified attorney is recommended before executing legal agreements.",
        description="Mandatory legal disclaimer required on all outputs.",
    )

    # Backward compatibility properties
    @property
    def overall_summary(self) -> str:
        return self.executive_summary

    @property
    def recommendations(self) -> list[str]:
        return self.key_risks


# Backward compatibility alias
LLMDocumentSummary = DocumentRiskAnalysis


class DocumentClassification(BaseModel):
    """Result of classifying whether an uploaded file is a legal/policy document."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    is_legal_document: bool = Field(
        ...,
        description="True if document is a contract, terms of service, privacy policy, NDA, or legal policy.",
    )
    document_type_detected: str = Field(
        default="General Contract",
        description="The identified type of document (e.g. 'Setup Guide', 'Terms of Service', 'Privacy Policy').",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Classification confidence score.",
    )
    reason: str = Field(
        default="",
        description="Brief explanation of classification.",
    )
