"""Build commands for FTreeKG.

Click subcommands for building the FileTreeKG knowledge graph:

    build   - filesystem tree -> SQLite + LanceDB
"""

from __future__ import annotations

from pathlib import Path

import click

from src.cli.main import cli
from src.cli.options import (
    db_option,
    exclude_option,
    include_option,
    lancedb_option,
    model_option,
    repo_option,
)
from src.config import load_exclude_dirs, load_include_dirs
from src.module import FileTreeKG


@cli.command("build")
@repo_option
@db_option
@lancedb_option
@model_option
@include_option
@exclude_option
@click.option("--wipe", is_flag=True, help="Delete existing graph first.")
def build(
    repo: str,
    db: str,
    lancedb: str,
    model: str,
    include_dir: tuple[str, ...],
    exclude_dir: tuple[str, ...],
    wipe: bool,
) -> None:
    """Extract a filesystem tree knowledge graph and build indices.

    Scans the filesystem tree, extracts nodes (files, directories, symlinks)
    with metadata, and builds both SQLite and LanceDB indices.

    Respects [tool.filetreekg] include/exclude directives in pyproject.toml.
    CLI options override pyproject.toml settings.
    """
    repo_root = Path(repo).resolve()
    db_path = Path(db)
    lancedb_path = Path(lancedb)

    # Merge CLI options with pyproject.toml config
    include_dirs = set(include_dir) or load_include_dirs(repo_root)
    exclude_dirs = set(exclude_dir) or load_exclude_dirs(repo_root)

    click.echo(f"🌳 Building FileTreeKG for {repo_root}")
    if wipe:
        click.echo("  Wiping existing indices...")
    if include_dirs:
        click.echo(f"  Including: {', '.join(sorted(include_dirs))}")
    if exclude_dirs:
        click.echo(f"  Excluding: {', '.join(sorted(exclude_dirs))}")

    try:
        kg = FileTreeKG(
            repo_root=repo_root,
            db_path=db_path,
            lancedb_path=lancedb_path,
        )
        kg.build(wipe=wipe)
        stats = kg.stats()

        click.echo("✅ Build complete")
        click.echo(f"   Nodes: {stats['total_nodes']}")
        click.echo(f"   Edges: {stats['total_edges']}")

        if stats.get("node_counts"):
            click.echo("   Node breakdown:")
            for kind, count in stats["node_counts"].items():
                click.echo(f"     - {kind}: {count}")

    except Exception as e:
        click.echo(f"❌ Build failed: {e}", err=True)
        raise
