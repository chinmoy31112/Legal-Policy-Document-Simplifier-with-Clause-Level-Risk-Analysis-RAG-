"""
CLI entry point for Gemini Call Ledger.

Usage:
    python backend/cli/ledger.py --today
    python -m backend.cli.ledger --today
    python -m backend.cli.ledger --doc <document_id>
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ai.ledger import get_call_ledger


def main() -> None:
    parser = argparse.ArgumentParser(description="Query Gemini Outbound Call Ledger")
    parser.add_argument("--today", action="store_true", help="Display today's calls by purpose")
    parser.add_argument("--date", type=str, default=None, help="Specific date YYYY-MM-DD")
    parser.add_argument("--doc", type=str, default=None, help="Document ID for specific summary")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    ledger = get_call_ledger()

    if args.doc:
        doc_summary = ledger.get_document_summary(args.doc)
        if args.json:
            print(json.dumps(doc_summary, indent=2))
        else:
            print(f"=== Document Summary [{args.doc}] ===")
            print(f"Total Calls: {doc_summary['total_calls']} / Budget: {doc_summary['budget']}")
            print(f"Calls by Purpose: {doc_summary['calls_by_purpose']}")
            print(f"Retries: {doc_summary['retries']}, Repairs: {doc_summary['repairs']}")
            print(
                f"Latency: {doc_summary['total_latency_seconds']}s, Tokens: {doc_summary['total_tokens']}"
            )
    else:
        if args.json:
            print(json.dumps(ledger.get_today_summary(args.date), indent=2))
        else:
            print(ledger.format_today_table(args.date))


if __name__ == "__main__":
    main()
