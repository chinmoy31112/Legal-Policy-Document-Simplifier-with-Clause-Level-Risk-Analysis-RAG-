"""Make document_analysis.overall_risk_score nullable for non-legal documents

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-26 10:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "document_analysis",
        "overall_risk_score",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE document_analysis SET overall_risk_score = 0 WHERE overall_risk_score IS NULL")
    op.alter_column(
        "document_analysis",
        "overall_risk_score",
        existing_type=sa.Integer(),
        nullable=False,
    )
