"""
Analysis schemas.

Pydantic models for clause-level and document-level risk analysis results.
"""

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RiskCategory(StrEnum):
    """Risk classification categories."""
    STANDARD = "standard"
    SLIGHTLY_UNUSUAL = "slightly_unusual"
    ONE_SIDED = "one_sided"
    HIGH_RISK = "high_risk"
    POTENTIALLY_UNENFORCEABLE = "potentially_unenforceable"


class RetrievedClause(BaseModel):
    """A reference clause retrieved from the knowledge base."""
    clause_id: str
    title: str | None = None
    content: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    source_document: str | None = None
    document_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClauseAnalysisResponse(BaseModel):
    """Full analysis result for a single clause."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    clause_id: UUID
    document_id: UUID
    plain_english_summary: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_category: RiskCategory
    risk_reasons: list[str] = Field(default_factory=list)
    retrieved_clauses: list[RetrievedClause] = Field(default_factory=list)
    missing_protections: list[str] = Field(default_factory=list)
    suggested_rewrite: str | None = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    potential_legal_concern: str | None = None


class RiskDistribution(BaseModel):
    """Count of clauses per risk category."""
    standard: int = 0
    slightly_unusual: int = 0
    one_sided: int = 0
    high_risk: int = 0
    potentially_unenforceable: int = 0


class DocumentAnalysisResponse(BaseModel):
    """Document-level aggregate analysis."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    overall_risk_score: int = Field(..., ge=0, le=100)
    overall_summary: str
    top_risky_clauses: list[dict[str, Any]] = Field(default_factory=list)
    clause_statistics: dict[str, Any] = Field(default_factory=dict)
    risk_distribution: RiskDistribution
    recommendations: list[str] = Field(default_factory=list)


class AnalysisStatusResponse(BaseModel):
    """Real-time analysis progress status."""
    document_id: UUID
    status: str
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress 0.0 to 1.0")
    current_step: str | None = None
    total_clauses: int = 0
    analyzed_clauses: int = 0
    message: str | None = None
