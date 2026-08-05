"""
Pydantic schemas for parsing LLM structured JSON responses.

These schemas ensure that the LLM output conforms to the expected structure
before it is saved to the database.
"""

from typing import Literal
from pydantic import BaseModel, Field


class LLMClauseAnalysis(BaseModel):
    """Expected JSON structure from the LLM for clause analysis."""
    
    plain_english_summary: str = Field(..., description="Clear explanation of the clause.")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score from 0 to 100.")
    risk_category: Literal[
        "standard", "slightly_unusual", "one_sided", "high_risk", "potentially_unenforceable"
    ]
    risk_reasons: list[str] = Field(default_factory=list)
    missing_protections: list[str] = Field(default_factory=list)
    suggested_rewrite: str | None = None
    potential_legal_concern: str | None = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class LLMDocumentSummary(BaseModel):
    """Expected JSON structure from the LLM for overall document summary."""
    
    overall_risk_score: int = Field(..., ge=0, le=100)
    overall_summary: str
    recommendations: list[str] = Field(default_factory=list)
