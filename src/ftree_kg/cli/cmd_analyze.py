"""Analysis commands for FTreeKG.

Click subcommands for analyzing the FileTreeKG knowledge graph:

    analyze   - generate full analysis report

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

from __future__ import annotations

from pathlib import Path

import click

from ftree_kg.cli.group import cli
from ftree_kg.cli.options import db_option, lancedb_option, repo_option
from ftree_kg.module import FileTreeKG


@cli.command("analyze")
@repo_option
@db_option
@lancedb_option
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Write report to file. Defaults to analysis/filetreekg_analysis.md.",
)
def analyze(
    repo: str,
    db: str,
    lancedb: str,
    output: str | None,
) -> None:
    """Generate a full analysis report of the filesystem tree.

    Reports include node/edge counts, breakdown by kind, and structural metrics.
    """
    repo_root = Path(repo).resolve()
    db_path = Path(db) if db else repo_root / ".filetreekg" / "graph.sqlite"
    lancedb_path = Path(lancedb) if lancedb else repo_root / ".filetreekg" / "lancedb"

    try:
        kg = FileTreeKG(
            repo_root=repo_root,
            db_path=db_path,
            lancedb_path=lancedb_path,
        )
        report = kg.analyze()

        if output is None:
            output_path = repo_root / "analysis" / "filetreekg_analysis.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)
            click.echo(f"✅ Analysis written to {output_path.relative_to(repo_root)}")
        else:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report)
            click.echo(f"✅ Analysis written to {output_path}")

    except Exception as e:
        click.echo(f"❌ Analysis failed: {e}", err=True)
        raise
