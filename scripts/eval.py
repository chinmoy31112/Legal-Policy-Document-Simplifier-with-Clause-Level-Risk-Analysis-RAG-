"""
Convenience launcher for the Evaluation Harness.

Usage:
    python scripts/eval.py --phase 1
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    cmd = [sys.executable, "-m", "backend.eval.runner"] + sys.argv[1:]
    res = subprocess.run(cmd, check=False, cwd=str(ROOT))
    sys.exit(res.returncode)
