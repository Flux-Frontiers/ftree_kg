"""cmd_status.py

Click subcommand for displaying live FTreeKG graph status:

  status  — show node/edge counts, filesystem size, index paths, and config

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

from __future__ import annotations

import importlib.metadata
from datetime import UTC, datetime
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.rule import Rule
from rich.table import Table

from ftree_kg.cli.group import cli
from ftree_kg.cli.options import db_option, repo_option
from ftree_kg.config import DEFAULT_SKIP_DIRS, load_exclude_dirs, load_include_dirs
from ftree_kg.module import FileTreeKG, _fmt_size, _size_bar

_console = Console()

_NODE_KINDS_ORDER = ("file", "directory", "symlink", "module")


def _build_node_table(nc: dict[str, int], total_nodes: int) -> Table:
    table = Table(title="Nodes", show_header=True, header_style="bold")
    table.add_column("Kind", style="cyan")
    table.add_column("Count", justify="right")
    for kind in _NODE_KINDS_ORDER:
        count = nc.get(kind, 0)
        if count:
            table.add_row(kind, f"{count:,}")
    for kind, count in sorted(nc.items()):
        if kind not in _NODE_KINDS_ORDER and count:
            table.add_row(kind, f"{count:,}")
    table.add_section()
    table.add_row("[bold]total[/bold]", f"[bold]{total_nodes:,}[/bold]")
    return table


def _build_edge_table(ec: dict[str, int], total_edges: int) -> Table:
    table = Table(title="Edges", show_header=True, header_style="bold")
    table.add_column("Relation", style="cyan")
    table.add_column("Count", justify="right")
    for rel, count in sorted(ec.items(), key=lambda x: -x[1]):
        table.add_row(rel, f"{count:,}")
    table.add_section()
    table.add_row("[bold]total[/bold]", f"[bold]{total_edges:,}[/bold]")
    return table


@cli.command("status")
@repo_option
@db_option
def status(repo: str, db: str) -> None:
    """Show live node/edge counts, filesystem size, and index metadata."""
    repo_root = Path(repo).resolve()
    db_path = Path(db) if db else repo_root / ".filetreekg" / "graph.sqlite"
    lancedb_path = db_path.parent / "lancedb"

    if not db_path.exists():
        _console.print(f"[red]Graph store not found:[/red] {db_path}")
        _console.print("[dim]Run [bold]ftreekg build[/bold] to create it.[/dim]")
        raise SystemExit(1)

    version = importlib.metadata.version("ftree-kg")
    db_size_mb = round(db_path.stat().st_size / 1_048_576, 3)
    built_at = datetime.fromtimestamp(db_path.stat().st_mtime, tz=UTC).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    lancedb_ok = (lancedb_path / "kg_nodes.lance").exists()
    lance_label = (
        "[green]present[/green]"
        if lancedb_ok
        else "[yellow]missing[/yellow] (run ftreekg build --vector)"
    )

    kg = FileTreeKG(repo_root=repo_root, db_path=db_path, lancedb_path=lancedb_path)
    s = kg.stats()
    kg.close()

    nc: dict[str, int] = s.get("node_counts", {})
    ec: dict[str, int] = s.get("edge_counts", {})
    total_nodes: int = s.get("total_nodes", 0)
    total_edges: int = s.get("total_edges", 0)
    total_size: int = s.get("total_size_bytes", 0)
    size_by_dir: dict[str, int] = s.get("size_by_top_dir", {})

    include_dirs = load_include_dirs(repo_root)
    exclude_dirs = load_exclude_dirs(repo_root)

    _console.print(Rule(f"FTreeKG Status — {repo_root}", style="bold blue"))
    _console.print(f"  Version  : ftree-kg {version}")
    _console.print(f"  Built at : {built_at}")
    _console.print(f"  DB path  : {db_path}  ({db_size_mb} MB)")
    _console.print(f"  LanceDB  : {lance_label}")
    _console.print()

    # Config section
    include_str = (
        ", ".join(sorted(include_dirs)) if include_dirs else "[dim]all (none specified)[/dim]"
    )
    skip_str = ", ".join(sorted(DEFAULT_SKIP_DIRS | exclude_dirs))
    _console.print(f"  Include dirs  : {include_str}")
    _console.print(f"  Exclude dirs  : {skip_str}")
    _console.print()

    node_table = _build_node_table(nc, total_nodes)
    edge_table = _build_edge_table(ec, total_edges)
    _console.print(Columns([node_table, edge_table]))
    _console.print()

    # Filesystem size summary
    _console.print(f"  Total indexed size : [bold]{_fmt_size(total_size)}[/bold]")
    _console.print()

    if size_by_dir:
        size_table = Table(
            title="Size by top-level directory", show_header=True, header_style="bold"
        )
        size_table.add_column("Directory", style="cyan")
        size_table.add_column("Bar", no_wrap=True)
        size_table.add_column("Size", justify="right")

        max_size = max(size_by_dir.values()) or 1
        for top_dir, size in size_by_dir.items():
            size_table.add_row(top_dir, _size_bar(size, max_size, width=16), _fmt_size(size))

        _console.print(size_table)
