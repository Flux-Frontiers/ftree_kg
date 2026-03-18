"""Query and pack commands for FTreeKG.

Click subcommands for querying the FileTreeKG knowledge graph:

    query   - semantic search over filesystem nodes
    pack    - get metadata snippets for query results
"""

from __future__ import annotations

from pathlib import Path

import click

from src.cli.main import cli
from src.cli.options import db_option, k_option, lancedb_option, repo_option
from src.module import FileTreeKG


@cli.command("query")
@repo_option
@db_option
@lancedb_option
@k_option
@click.argument("query")
def query(
    repo: str,
    db: str,
    lancedb: str,
    k: int,
    query: str,
) -> None:
    """Search the filesystem tree by semantic query.

    QUERY: Semantic query string (e.g., "Python files", "config directories")

    Returns the top-k matching nodes with their scores and metadata.
    """
    repo_root = Path(repo).resolve()
    db_path = Path(db)
    lancedb_path = Path(lancedb)

    try:
        kg = FileTreeKG(
            repo_root=repo_root,
            db_path=db_path,
            lancedb_path=lancedb_path,
        )
        result = kg.query(query, k=k)

        click.echo(f"📍 Query: {query}")
        click.echo(f"📊 Results: {len(result.nodes)} nodes\n")

        for i, node in enumerate(result.nodes, 1):
            score = node.get("score", 0.0)
            kind = node.get("kind", "unknown")
            qualname = node.get("qualname", "unknown")
            click.echo(f"{i}. [{kind}] {qualname}")
            click.echo(f"   Score: {score:.3f}")

            if node.get("docstring"):
                lines = node["docstring"].split("\n")[:2]
                for line in lines:
                    click.echo(f"   {line}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ Query failed: {e}", err=True)
        raise


@cli.command("pack")
@repo_option
@db_option
@lancedb_option
@k_option
@click.argument("query")
def pack(
    repo: str,
    db: str,
    lancedb: str,
    k: int,
    query: str,
) -> None:
    """Get filesystem metadata snippets for query results.

    QUERY: Semantic query string (e.g., "large files", "recent changes")

    Returns metadata (size, timestamps, permissions) for matching nodes.
    """
    repo_root = Path(repo).resolve()
    db_path = Path(db)
    lancedb_path = Path(lancedb)

    try:
        kg = FileTreeKG(
            repo_root=repo_root,
            db_path=db_path,
            lancedb_path=lancedb_path,
        )
        pack_result = kg.pack(query, k=k)

        click.echo(f"📦 Pack: {query}")
        click.echo(f"📄 Results: {len(pack_result.nodes)} nodes\n")

        for i, node in enumerate(pack_result.nodes, 1):
            kind = node.get("kind", "unknown")
            qualname = node.get("qualname", "unknown")
            click.echo(f"{i}. [{kind}] {qualname}")

            if node.get("docstring"):
                click.echo(node["docstring"])
            click.echo()

    except Exception as e:
        click.echo(f"❌ Pack failed: {e}", err=True)
        raise
