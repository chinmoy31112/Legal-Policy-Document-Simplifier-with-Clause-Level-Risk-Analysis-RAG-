"""
ORM models package.

Import all models here so that SQLAlchemy's metadata registry
knows about every table. This is required for Alembic auto-generation.
"""

from app.models.analysis import AnalysisResult, DocumentAnalysis
from app.models.audit_log import AuditLog
from app.models.clause import Clause
from app.models.document import Document
from app.models.job import JOB_STATES, Job
from app.models.knowledge_base import KBClause, KBDocument, ReferenceClause
from app.models.user import User

__all__ = [
    "User",
    "Document",
    "Clause",
    "AnalysisResult",
    "DocumentAnalysis",
    "KBDocument",
    "KBClause",
    "ReferenceClause",
    "Job",
    "JOB_STATES",
    "AuditLog",
]
