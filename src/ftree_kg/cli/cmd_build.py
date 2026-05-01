"""Build commands for FTreeKG.

Click subcommands for building the FileTreeKG knowledge graph:

    build   - filesystem tree -> SQLite + LanceDB

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

from __future__ import annotations

from pathlib import Path

import click

from ftree_kg.cli.group import cli
from ftree_kg.cli.options import (
    db_option,
    exclude_option,
    include_option,
    lancedb_option,
    model_option,
    repo_option,
)
from ftree_kg.config import load_exclude_dirs, load_include_dirs
from ftree_kg.module import FileTreeKG


@cli.command("build")
@repo_option
@db_option
@lancedb_option
@model_option
@include_option
@exclude_option
@click.option(
    "--no-wipe", is_flag=True, default=False, help="Keep existing graph instead of rebuilding."
)
def build(
    repo: str,
    db: str,
    lancedb: str,
    model: str,
    include_dir: tuple[str, ...],
    exclude_dir: tuple[str, ...],
    no_wipe: bool,
) -> None:
    """Extract a filesystem tree knowledge graph and build indices.

    Scans the filesystem tree, extracts nodes (files, directories, symlinks)
    with metadata, and builds both SQLite and LanceDB indices.

    Respects [tool.filetreekg] include/exclude directives in pyproject.toml.
    CLI options override pyproject.toml settings.
    """
    repo_root = Path(repo).resolve()
    db_path = Path(db) if db else repo_root / ".filetreekg" / "graph.sqlite"
    lancedb_path = Path(lancedb) if lancedb else repo_root / ".filetreekg" / "lancedb"

    # Merge CLI options with pyproject.toml config
    include_dirs = set(include_dir) or load_include_dirs(repo_root)
    exclude_dirs = set(exclude_dir) or load_exclude_dirs(repo_root)

    click.echo(f"🌳 Building FileTreeKG for {repo_root}")
    if no_wipe:
        click.echo("  Keeping existing indices (--no-wipe)...")
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
        kg.build(wipe=not no_wipe)
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
