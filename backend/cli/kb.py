"""
Knowledge Base Management CLI.

Phase 3 Deliverable:
Commands:
    kb index   - Index reference documents (PDF, DOCX, TXT, JSON, MD)
    kb update  - Re-index and update reference documents
    kb list    - List indexed reference clauses with metadata
    kb stats   - Display knowledge base and embedding vector statistics
    kb delete  - Delete reference clauses or documents

Usage:
    python -m backend.cli.kb index backend/knowledge_base/reference_clauses.json
    python -m backend.cli.kb stats
    python -m backend.cli.kb list --limit 10
    python -m backend.cli.kb delete REF-LIAB-001
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

# Ensure project root is in path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.knowledge_base_service import KnowledgeBaseService

console = Console()


async def cmd_index(args: argparse.Namespace, service: KnowledgeBaseService) -> None:
    """Index files or directory into the knowledge base."""
    target_path = Path(args.path)
    if not target_path.exists():
        console.print(f"[bold red]Error:[/bold red] Target path does not exist: {target_path}")
        sys.exit(1)

    files_to_process: list[Path] = []
    if target_path.is_file():
        files_to_process.append(target_path)
    else:
        for ext in ("*.json", "*.pdf", "*.docx", "*.txt", "*.md", "*.markdown"):
            files_to_process.extend(target_path.glob(ext))

    if not files_to_process:
        console.print(f"[yellow]No supported documents found at {target_path}[/yellow]")
        return

    console.print(
        Panel.fit(
            f"[bold cyan]Knowledge Base Ingestion[/bold cyan]\n"
            f"Files to process: [bold]{len(files_to_process)}[/bold]\n"
            f"Dry Run: [bold]{args.dry_run}[/bold]",
            border_style="cyan",
        )
    )

    results: list[dict[str, Any]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} files"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Ingesting documents...", total=len(files_to_process))

        for file_p in files_to_process:
            progress.update(task, description=f"[cyan]Processing {file_p.name}...")
            try:
                res = await service.ingest_file(
                    file_path=file_p,
                    document_type=args.type,
                    jurisdiction=args.jurisdiction,
                    dry_run=args.dry_run,
                )
                results.append(res)
            except Exception as exc:
                results.append({"file": file_p.name, "error": str(exc)})
            progress.advance(task)

    # Display results table
    table = Table(title="Ingestion Summary", header_style="bold magenta")
    table.add_column("File / Source", style="cyan")
    table.add_column("Extracted", justify="right")
    table.add_column("Indexed (New)", justify="right", style="green")
    table.add_column("Skipped (Idempotent)", justify="right", style="yellow")
    table.add_column("Status", style="bold")

    for r in results:
        if "error" in r:
            table.add_row(
                r.get("file", "unknown"), "-", "-", "-", f"[red]ERROR: {r['error']}[/red]"
            )
        elif "file" in r:
            table.add_row(
                r["file"],
                str(r.get("clauses_extracted", "-")),
                str(r.get("clauses_indexed", r.get("clauses_to_index", 0))),
                str(r.get("clauses_skipped", 0)),
                "[yellow]DRY RUN[/yellow]" if r.get("dry_run") else "[green]SUCCESS[/green]",
            )
        else:
            table.add_row(
                target_path.name,
                str(r.get("total", "-")),
                str(r.get("indexed", 0)),
                str(r.get("skipped", 0)),
                "[yellow]DRY RUN[/yellow]" if r.get("dry_run") else "[green]SUCCESS[/green]",
            )

    console.print(table)


async def cmd_update(args: argparse.Namespace, service: KnowledgeBaseService) -> None:
    """Re-index or update existing files."""
    console.print(f"[bold cyan]Updating Knowledge Base from:[/bold cyan] {args.path}")
    await cmd_index(args, service)


async def cmd_list(args: argparse.Namespace, service: KnowledgeBaseService) -> None:
    """List indexed reference clauses with metadata."""
    clauses = await service.list_clauses(category=args.category, limit=args.limit)

    if not clauses:
        console.print("[yellow]No reference clauses found matching criteria.[/yellow]")
        return

    table = Table(title=f"Indexed Reference Clauses (Top {len(clauses)})", header_style="bold cyan")
    table.add_column("ID", style="bold green", no_wrap=True)
    table.add_column("Title", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Document Type", style="blue")
    table.add_column("Preview", style="dim")

    for c in clauses:
        table.add_row(
            c["id"],
            c["title"],
            c["category"],
            c["document_type"],
            c["text_preview"],
        )

    console.print(table)


async def cmd_stats(args: argparse.Namespace, service: KnowledgeBaseService) -> None:
    """Display Knowledge Base statistics."""
    stats = await service.get_stats()

    info_table = Table(title="Knowledge Base System Stats", header_style="bold green")
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="bold white")

    info_table.add_row("Embedding Model", stats["embedding_model"])
    info_table.add_row("Vector Dimension", str(stats["embedding_dimension"]))
    info_table.add_row("Vector Store Type", stats["vector_store_type"])
    info_table.add_row("Total Indexed Vectors", str(stats["total_vectors"]))

    console.print(info_table)

    if stats.get("categories"):
        cat_table = Table(title="Category Breakdown", header_style="bold magenta")
        cat_table.add_column("Category", style="magenta")
        cat_table.add_column("Clauses Count", justify="right", style="bold green")

        for cat, cnt in sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True):
            cat_table.add_row(cat, str(cnt))

        console.print(cat_table)


async def cmd_delete(args: argparse.Namespace, service: KnowledgeBaseService) -> None:
    """Delete a clause from the knowledge base."""
    target_id = args.id
    success = await service.delete_clause(target_id)
    if success:
        console.print(f"[bold green]Deleted vector record:[/bold green] {target_id}")
    else:
        console.print(f"[bold red]Failed to delete vector record:[/bold red] {target_id}")


async def async_main() -> None:
    parser = argparse.ArgumentParser(description="Legal Knowledge Base CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # kb index
    index_parser = subparsers.add_parser("index", help="Index reference documents")
    index_parser.add_argument("path", help="Path to file or directory to index")
    index_parser.add_argument("--type", "-t", default=None, help="Document type")
    index_parser.add_argument("--jurisdiction", "-j", default=None, help="Jurisdiction")
    index_parser.add_argument(
        "--dry-run", action="store_true", help="Preview indexing without storing"
    )

    # kb update
    update_parser = subparsers.add_parser("update", help="Update/re-index documents")
    update_parser.add_argument("path", help="Path to file or directory to update")
    update_parser.add_argument("--type", "-t", default=None, help="Document type")
    update_parser.add_argument("--jurisdiction", "-j", default=None, help="Jurisdiction")
    update_parser.add_argument(
        "--dry-run", action="store_true", help="Preview update without storing"
    )

    # kb list
    list_parser = subparsers.add_parser("list", help="List reference clauses")
    list_parser.add_argument("--category", "-c", default=None, help="Filter by category")
    list_parser.add_argument("--limit", "-n", type=int, default=20, help="Max records to list")

    # kb stats
    subparsers.add_parser("stats", help="Display KB and embedding stats")

    # kb delete
    del_parser = subparsers.add_parser("delete", help="Delete a clause by ID")
    del_parser.add_argument("id", help="Clause ID to delete")

    args = parser.parse_args()

    service = KnowledgeBaseService()

    if args.command == "index":
        await cmd_index(args, service)
    elif args.command == "update":
        await cmd_update(args, service)
    elif args.command == "list":
        await cmd_list(args, service)
    elif args.command == "stats":
        await cmd_stats(args, service)
    elif args.command == "delete":
        await cmd_delete(args, service)


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
