"""
Part D.5 Migration Proof Test.

Proves that `alembic upgrade head` ALONE (without Base.metadata.create_all) on a
completely empty PostgreSQL database creates every required table:
- users
- documents
- clauses
- analysis_results & document_analysis (results)
- jobs
- kb_documents & kb_clauses (knowledge base)
- reference_clauses
- audit_logs
- alembic_version
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import asyncpg
import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent

REQUIRED_TABLES = {
    "users",
    "documents",
    "clauses",
    "analysis_results",
    "document_analysis",
    "jobs",
    "kb_documents",
    "kb_clauses",
    "reference_clauses",
    "audit_logs",
    "alembic_version",
}

DOMAIN_TABLES = REQUIRED_TABLES - {"alembic_version"}


def _resolve_alembic_cmd() -> list[str]:
    for cand in (
        BACKEND_DIR / "venv" / "Scripts" / "alembic.exe",
        BACKEND_DIR / "venv" / "bin" / "alembic",
    ):
        if cand.exists():
            return [str(cand)]
    return [sys.executable, "-m", "alembic"]


@pytest.mark.asyncio
async def test_migrations_alone_create_every_table_on_empty_database():
    """Create an empty Postgres DB, run `alembic upgrade head`, and verify all tables exist."""
    from app.core.config import get_settings

    base_url = get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(base_url)
    admin_url = urlunparse(parsed._replace(path="/postgres"))
    temp_db = f"test_mig_{uuid.uuid4().hex[:12]}"
    temp_asyncpg_url = urlunparse(parsed._replace(path=f"/{temp_db}"))
    temp_sa_url = temp_asyncpg_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    admin_conn = await asyncpg.connect(admin_url)
    try:
        await admin_conn.execute(f'CREATE DATABASE "{temp_db}"')
    finally:
        await admin_conn.close()

    env = os.environ.copy()
    env["DATABASE_URL"] = temp_sa_url
    env["APP_ENV"] = "test"
    env["GOOGLE_API_KEY"] = ""
    alembic_cmd = _resolve_alembic_cmd()

    try:
        # 1. Verify database starts completely empty
        db_conn = await asyncpg.connect(temp_asyncpg_url)
        try:
            initial_tables = {
                r["tablename"]
                for r in await db_conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
            }
            assert initial_tables == set(), f"Expected empty DB, found {initial_tables}"
        finally:
            await db_conn.close()

        # 2. Run alembic upgrade head ONLY (no Base.metadata.create_all)
        up_res = subprocess.run(
            [*alembic_cmd, "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert up_res.returncode == 0, (
            f"alembic upgrade head failed:\n{up_res.stderr}\n{up_res.stdout}"
        )

        # 3. Inspect tables and critical columns created purely by migrations
        db_conn = await asyncpg.connect(temp_asyncpg_url)
        try:
            created_tables = {
                r["tablename"]
                for r in await db_conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
            }
            missing = REQUIRED_TABLES - created_tables
            assert not missing, f"Migrations failed to create required tables: {sorted(missing)}"

            job_cols = {
                r["column_name"]
                for r in await db_conn.fetch(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'jobs'"
                )
            }
            assert {
                "id",
                "document_id",
                "user_id",
                "arq_job_id",
                "status",
                "stage",
                "total_clauses",
                "completed_clauses",
                "cancel_requested",
            }.issubset(job_cols)

            ref_cols = {
                r["column_name"]
                for r in await db_conn.fetch(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'reference_clauses'"
                )
            }
            assert {"id", "title", "category", "document_type", "text"}.issubset(ref_cols)

            has_vector_type = await db_conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector')"
            )
            if has_vector_type:
                assert "embedding" in ref_cols

            score_nullable = await db_conn.fetchval(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'document_analysis' "
                "AND column_name = 'overall_risk_score'"
            )
            assert score_nullable == "YES"
        finally:
            await db_conn.close()

        # 4. Verify downgrade base cleanly removes domain tables and re-upgrade restores them
        down_res = subprocess.run(
            [*alembic_cmd, "downgrade", "base"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert down_res.returncode == 0, f"alembic downgrade base failed:\n{down_res.stderr}"

        db_conn = await asyncpg.connect(temp_asyncpg_url)
        try:
            remaining = {
                r["tablename"]
                for r in await db_conn.fetch(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                )
            }
            leftover = DOMAIN_TABLES & remaining
            assert not leftover, f"Tables left after downgrade base: {sorted(leftover)}"
        finally:
            await db_conn.close()

        up_again = subprocess.run(
            [*alembic_cmd, "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert up_again.returncode == 0, f"re-upgrade failed:\n{up_again.stderr}"
    finally:
        cleanup_conn = await asyncpg.connect(admin_url)
        try:
            await cleanup_conn.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = $1 AND pid <> pg_backend_pid()
                """,
                temp_db,
            )
            await cleanup_conn.execute(f'DROP DATABASE IF EXISTS "{temp_db}"')
        finally:
            await cleanup_conn.close()
