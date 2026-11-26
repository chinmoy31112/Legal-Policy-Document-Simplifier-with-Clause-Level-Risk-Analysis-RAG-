"""
Cross-platform CI runner executed by `make ci` and pre-push hooks.

Runs the exact steps configured in `.github/workflows/ci.yml`:
1. ruff check backend
2. ruff format --check backend
3. mypy --config-file backend/pyproject.toml backend/app
4. alembic upgrade head against an empty PostgreSQL database
5. pytest backend/tests -v (fake/offline LLM, APP_ENV=test)
6. evaluation harness (python -m backend.eval.runner --phase 7)
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse, urlunparse

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


def _resolve_tool(name: str) -> list[str]:
    """Resolve CLI tool from backend venv first, then PATH."""
    candidates = [
        BACKEND_DIR / "venv" / "Scripts" / f"{name}.exe",
        BACKEND_DIR / "venv" / "Scripts" / name,
        BACKEND_DIR / "venv" / "bin" / name,
    ]
    for path in candidates:
        if path.exists():
            return [str(path)]
    found = shutil.which(name)
    if found:
        return [found]
    # Fallback to python -m for python tools
    return [_resolve_python(), "-m", name]


def _resolve_python() -> str:
    """Resolve the backend virtualenv Python interpreter if present."""
    candidates = [
        BACKEND_DIR / "venv" / "Scripts" / "python.exe",
        BACKEND_DIR / "venv" / "bin" / "python",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return sys.executable


def _run_step(title: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> None:
    """Run one CI step streaming output and aborting on non-zero exit."""
    print(f"\n=== CI STEP: {title} ===", flush=True)
    print(f"$ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, check=False)
    if proc.returncode != 0:
        print(f"\nFAILED: {title} (exit code {proc.returncode})", file=sys.stderr, flush=True)
        sys.exit(proc.returncode)


async def _recreate_empty_database(target_db_url: str) -> None:
    """Drop and recreate the target CI database so migrations always start empty."""
    import asyncpg

    # Normalize SQLAlchemy driver URL (postgresql+asyncpg:// -> postgresql://)
    pg_url = target_db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(pg_url)
    db_name = parsed.path.lstrip("/") or "legal_simplifier_ci"
    if not db_name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe database name for CI reset: {db_name!r}")

    admin_url = urlunparse(parsed._replace(path="/postgres"))
    conn = await asyncpg.connect(admin_url)
    try:
        await conn.execute(
            """
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = $1 AND pid <> pg_backend_pid()
            """,
            db_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        await conn.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await conn.close()


def main() -> None:
    python_exe = _resolve_python()

    # Determine target CI database URL (never touch dev DB unless explicitly requested)
    default_ci_db_url = "postgresql+asyncpg://postgres:postgres@localhost:5432/legal_simplifier_ci"
    ci_db_url = os.environ.get("CI_DATABASE_URL") or default_ci_db_url
    redis_url = os.environ.get("CI_REDIS_URL") or "redis://localhost:6379/1"
    skip_db_reset = os.environ.get("CI_SKIP_DB_RESET", "").lower() in ("1", "true", "yes")

    env = os.environ.copy()
    env["DATABASE_URL"] = ci_db_url
    env["REDIS_URL"] = redis_url
    env["APP_ENV"] = "test"
    env["GOOGLE_API_KEY"] = ""

    # 1. Ruff lint check
    _run_step(
        "ruff check",
        [*_resolve_tool("ruff"), "check", "backend"],
        cwd=ROOT_DIR,
        env=env,
    )

    # 2. Ruff format check
    _run_step(
        "ruff format --check",
        [*_resolve_tool("ruff"), "format", "--check", "backend"],
        cwd=ROOT_DIR,
        env=env,
    )

    # 3. Mypy static type check
    _run_step(
        "mypy",
        [
            *_resolve_tool("mypy"),
            "--config-file",
            "backend/pyproject.toml",
            "backend/app",
        ],
        cwd=ROOT_DIR,
        env=env,
    )

    # 4. Empty database + alembic upgrade head
    if not skip_db_reset:
        print("\n=== CI STEP: reset empty CI database ===", flush=True)
        print(f"Target CI database: {ci_db_url}", flush=True)
        asyncio.run(_recreate_empty_database(ci_db_url))

    _run_step(
        "alembic upgrade head (empty database)",
        [*_resolve_tool("alembic"), "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=env,
    )

    # 5. Pytest full backend test suite
    _run_step(
        "pytest",
        [*_resolve_tool("pytest"), "backend/tests", "-v"],
        cwd=ROOT_DIR,
        env=env,
    )

    # 6. Evaluation harness (writes report to temp directory to keep working tree clean)
    with tempfile.TemporaryDirectory(prefix="ci_eval_") as tmp_dir:
        report_path = Path(tmp_dir) / "phase-7-report.md"
        _run_step(
            "evaluation harness (phase 7)",
            [
                python_exe,
                "-m",
                "backend.eval.runner",
                "--phase",
                "7",
                "--output",
                str(report_path),
            ],
            cwd=ROOT_DIR,
            env=env,
        )

    print("\n=== ALL CI CHECKS PASSED ===", flush=True)


if __name__ == "__main__":
    main()
