"""
ORM models package.

Import all models here so that SQLAlchemy's metadata registry
knows about every table. This is required for Alembic auto-generation.
"""

from app.models.user import User
from app.models.document import Document
from app.models.clause import Clause
from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.models.knowledge_base import KBDocument, KBClause
from app.models.audit_log import AuditLog

__all__ = [
    "User",
    "Document",
    "Clause",
    "AnalysisResult",
    "DocumentAnalysis",
    "KBDocument",
    "KBClause",
    "AuditLog",
]
