"""
Orchestrates full-stack Playwright E2E tests against real FastAPI + ARQ Worker + Next.js
using LatencySimulatingFakeLLM (zero real Gemini quota consumed).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def _resolve_python() -> str:
    for cand in (
        BACKEND_DIR / "venv" / "Scripts" / "python.exe",
        BACKEND_DIR / "venv" / "bin" / "python",
    ):
        if cand.exists():
            return str(cand)
    return sys.executable


def _wait_for_http(url: str, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2.0) as resp:
                if 200 <= resp.status < 500:
                    return
        except Exception:
            time.sleep(0.5)
    raise TimeoutError(f"Service did not become ready at {url} within {timeout}s")


def main() -> None:
    python_exe = _resolve_python()
    api_port = int(os.environ.get("E2E_API_PORT", "18000"))
    fe_port = int(os.environ.get("E2E_FRONTEND_PORT", "13000"))
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/legal_simplifier_ci",
    )
    redis_url = os.environ.get("E2E_REDIS_URL") or "redis://localhost:6379/2"

    backend_env = os.environ.copy()
    backend_env["DATABASE_URL"] = db_url
    backend_env["REDIS_URL"] = redis_url
    backend_env["APP_ENV"] = "test"
    backend_env["GOOGLE_API_KEY"] = ""
    backend_env["USE_LATENCY_FAKE"] = "true"
    backend_env["LATENCY_FAKE_MIN_SECONDS"] = os.environ.get(
        "LATENCY_FAKE_MIN_SECONDS", "10.0"
    )
    backend_env["LATENCY_FAKE_MAX_SECONDS"] = os.environ.get(
        "LATENCY_FAKE_MAX_SECONDS", "11.0"
    )
    backend_env["ALLOWED_ORIGINS"] = (
        f'["http://127.0.0.1:{fe_port}","http://localhost:{fe_port}"]'
    )

    fe_env = os.environ.copy()
    fe_env["NEXT_PUBLIC_API_URL"] = f"http://127.0.0.1:{api_port}/api/v1"
    fe_env["E2E_API_URL"] = f"http://127.0.0.1:{api_port}/api/v1"
    fe_env["E2E_FRONTEND_URL"] = f"http://127.0.0.1:{fe_port}"
    fe_env["PYTHON_BIN"] = python_exe
    fe_env["REDIS_URL"] = redis_url

    # Clear any residual rate-limit/quota injection keys and stale CI test rows before starting worker/API
    try:
        subprocess.run(
            [
                python_exe,
                "-c",
                (
                    "import asyncio, asyncpg, os, redis; "
                    "r = redis.from_url(os.environ['REDIS_URL']); "
                    "keys = ['test:inject_daily_quota'] + [k for p in "
                    "('ratelimit:*', 'test:inject_daily_quota:*', 'arq:*', 'job:*') "
                    "for k in r.keys(p)]; r.delete(*keys) if keys else None; "
                    "db = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://', 1); "
                    "\nasync def clean_ci():\n"
                    "    conn = await asyncpg.connect(db)\n"
                    "    try:\n"
                    "        for tbl in ('jobs', 'analysis_results', 'document_analysis', 'clauses', 'documents', 'users'):\n"
                    "            await conn.execute(f'DELETE FROM {tbl}')\n"
                    "    finally:\n"
                    "        await conn.close()\n"
                    "\nif 'legal_simplifier_ci' in db:\n"
                    "    asyncio.run(clean_ci())"
                ),
            ],
            env={**backend_env, "REDIS_URL": redis_url, "DATABASE_URL": db_url},
            check=False,
        )
    except Exception:
        pass

    procs: list[subprocess.Popen[bytes]] = []
    try:
        print("Starting FastAPI backend...", flush=True)
        api_proc = subprocess.Popen(
            [
                python_exe,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
            ],
            cwd=str(BACKEND_DIR),
            env=backend_env,
        )
        procs.append(api_proc)

        print(
            "Starting ARQ background worker (LatencySimulatingFakeLLM)...", flush=True
        )
        worker_proc = subprocess.Popen(
            [python_exe, "-m", "app.workers.main"],
            cwd=str(BACKEND_DIR),
            env=backend_env,
        )
        procs.append(worker_proc)

        print("Starting Next.js frontend...", flush=True)
        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        fe_proc = subprocess.Popen(
            [npx_cmd, "next", "dev", "-p", str(fe_port), "--hostname", "127.0.0.1"],
            cwd=str(FRONTEND_DIR),
            env=fe_env,
        )
        procs.append(fe_proc)

        _wait_for_http(f"http://127.0.0.1:{api_port}/health/live", timeout=45.0)
        _wait_for_http(f"http://127.0.0.1:{fe_port}/login", timeout=90.0)
        print(
            "Backend API and Next.js frontend ready. Running Playwright suite...",
            flush=True,
        )

        pw_res = subprocess.run(
            [npx_cmd, "playwright", "test", "--reporter=list"],
            cwd=str(FRONTEND_DIR),
            env=fe_env,
            check=False,
        )
        sys.exit(pw_res.returncode)
    finally:
        for p in reversed(procs):
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
