"""Add jobs and reference_clauses tables

Revision ID: a1b2c3d4e5f6
Revises: 893ae15964be
Create Date: 2026-11-26 09:40:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "893ae15964be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create persistent jobs table
    op.create_table(
        "jobs",
        sa.Column("document_id", sa.UUID(), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("arq_job_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=True),
        sa.Column("total_clauses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_clauses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs_document_id"), "jobs", ["document_id"], unique=False)
    op.create_index(op.f("ix_jobs_user_id"), "jobs", ["user_id"], unique=False)
    op.create_index(op.f("ix_jobs_arq_job_id"), "jobs", ["arq_job_id"], unique=False)
    op.create_index(op.f("ix_jobs_status"), "jobs", ["status"], unique=False)
    op.create_index(op.f("ix_jobs_cancel_requested"), "jobs", ["cancel_requested"], unique=False)

    # Create reference_clauses table (supports pgvector when extension is available)
    op.create_table(
        "reference_clauses",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("document_type", sa.String(length=100), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("why_standard_or_risky", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reference_clauses")),
    )
    op.create_index(
        op.f("ix_reference_clauses_category"), "reference_clauses", ["category"], unique=False
    )

    # Add pgvector embedding column if vector type is installed
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
                ALTER TABLE reference_clauses ADD COLUMN IF NOT EXISTS embedding vector(768);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_reference_clauses_category"), table_name="reference_clauses")
    op.drop_table("reference_clauses")
    op.drop_index(op.f("ix_jobs_cancel_requested"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_status"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_arq_job_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_user_id"), table_name="jobs")
    op.drop_index(op.f("ix_jobs_document_id"), table_name="jobs")
    op.drop_table("jobs")
