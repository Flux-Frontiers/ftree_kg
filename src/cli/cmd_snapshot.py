"""Snapshot commands for FTreeKG.

Click subcommands for managing filesystem tree snapshots:

    snapshot   - save, list, show, and diff snapshots
"""

from __future__ import annotations

from pathlib import Path

import click

from src.cli.main import cli
from src.cli.options import db_option, lancedb_option, repo_option
from src.module import FileTreeKG


@cli.command("snapshot")
@repo_option
@db_option
@lancedb_option
@click.option("--list", is_flag=True, help="List saved snapshots.")
@click.option("--show", type=str, help="Show specific snapshot details (key or 'latest').")
@click.option("--save", type=str, help="Save a snapshot with version label.")
@click.option("--diff", nargs=2, type=str, help="Compare two snapshots by key.")
def snapshot(
    repo: str,
    db: str,
    lancedb: str,
    list: bool,
    show: str | None,
    save: str | None,
    diff: tuple[str, str] | None,
) -> None:
    """Manage and analyze filesystem tree snapshots.

    Snapshots track the state of the file tree over time, enabling:
    - Historical analysis of filesystem changes
    - Tracking file structure evolution
    - Comparing snapshots to see growth patterns
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

        if list:
            click.echo("📸 Filesystem Tree Snapshots")
            click.echo("(snapshot functionality via store.snapshot_list())")
            click.echo("Not yet implemented for filesystem trees")

        elif show:
            click.echo(f"📸 Snapshot: {show}")
            click.echo("(snapshot functionality via store.snapshot_show())")
            click.echo("Not yet implemented for filesystem trees")

        elif save:
            click.echo(f"💾 Saving snapshot: {save}")
            stats = kg.stats()
            click.echo(f"   Nodes: {stats['total_nodes']}")
            click.echo(f"   Edges: {stats['total_edges']}")
            click.echo("(snapshot save via store.snapshot_save())")
            click.echo("Not yet implemented for filesystem trees")

        elif diff:
            key_a, key_b = diff
            click.echo(f"🔄 Comparing snapshots: {key_a} vs {key_b}")
            click.echo("(snapshot diff functionality via store.snapshot_diff())")
            click.echo("Not yet implemented for filesystem trees")

        else:
            click.echo("📸 Snapshot Management")
            click.echo("\nUsage:")
            click.echo("  ftreekg-snapshot --list              # list all snapshots")
            click.echo("  ftreekg-snapshot --show latest       # show latest snapshot")
            click.echo("  ftreekg-snapshot --save v1.0         # save snapshot as v1.0")
            click.echo("  ftreekg-snapshot --diff key1 key2    # compare two snapshots")

    except Exception as e:
        click.echo(f"❌ Snapshot failed: {e}", err=True)
        raise
