"""Snapshot commands for FTreeKG.

Click subcommands for managing temporal snapshots of filesystem tree metrics:

    snapshot save   — capture current metrics and save snapshot
    snapshot list   — show all snapshots with key metrics
    snapshot show   — display full snapshot details
    snapshot diff   — compare two snapshots side-by-side
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from typing import cast

from ftree_kg.cli.group import cli
from ftree_kg.cli.options import db_option, lancedb_option, repo_option
from ftree_kg.module import FileTreeKG
from ftree_kg.snapshots import SnapshotDelta, SnapshotManager, SnapshotMetrics


@cli.group("snapshot")
def snapshot() -> None:
    """Manage temporal snapshots of FileTreeKG metrics."""


@snapshot.command("save")
@click.argument("version", metavar="VERSION", default="", required=False)
@repo_option
@db_option
@lancedb_option
@click.option(
    "--snapshots-dir",
    default=None,
    type=click.Path(),
    help="Snapshots directory (default: .filetreekg/snapshots).",
)
@click.option(
    "--branch",
    default=None,
    type=str,
    help="Branch name; auto-detected if not provided.",
)
@click.option(
    "--tree-hash",
    default="",
    type=str,
    help="Git tree hash; auto-detected if not provided.",
)
def save_snapshot(
    version: str,
    repo: str,
    db: str,
    lancedb: str,
    snapshots_dir: str | None,
    branch: str | None,
    tree_hash: str,
) -> None:
    """Capture current FileTreeKG metrics and save as a temporal snapshot.

    Reads node/edge statistics from the SQLite graph, then saves a snapshot
    tagged with the given VERSION. The tree hash is auto-detected from git
    when not provided.

    Snapshots are stored in .filetreekg/snapshots/{tree_hash}.json, with a
    manifest.json tracking all snapshots and their metrics.

    Example:
        ftreekg snapshot save 0.1.0 --repo .
    """
    repo_root = Path(repo).resolve()
    db_path = Path(db) if db else repo_root / ".filetreekg" / "graph.sqlite"
    lancedb_path = Path(lancedb) if lancedb else repo_root / ".filetreekg" / "lancedb"
    snapshots_path = (
        Path(snapshots_dir).resolve() if snapshots_dir else repo_root / ".filetreekg" / "snapshots"
    )

    kg = FileTreeKG(repo_root=repo_root, db_path=db_path, lancedb_path=lancedb_path)
    try:
        stats = kg.stats()
    finally:
        kg.close()

    snap_mgr = SnapshotManager(snapshots_path, db_path=db_path)
    snapshot_obj = snap_mgr.capture(
        version=version or None,
        branch=branch,
        stats_dict=stats,
        tree_hash=tree_hash,
    )

    snapshot_file = snap_mgr.save_snapshot(snapshot_obj)
    click.echo(f"OK Snapshot saved: {snapshot_file or '(skipped, unchanged)'}")
    click.echo(f"  Key:     {snapshot_obj.key}")
    click.echo(f"  Version: {snapshot_obj.version}")
    m = cast(SnapshotMetrics, snapshot_obj.metrics)
    click.echo(f"  Nodes:   {m.total_nodes}")
    click.echo(f"  Edges:   {m.total_edges}")
    click.echo(f"  Files:   {m.total_files}")
    click.echo(f"  Dirs:    {m.total_dirs}")


@snapshot.command("list")
@click.option(
    "--snapshots-dir",
    default=None,
    type=click.Path(exists=True),
    help="Snapshots directory (default: .filetreekg/snapshots).",
)
@click.option("--limit", type=int, default=None, help="Max snapshots to show.")
@click.option("--branch", default=None, type=str, help="Filter by branch name.")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
def list_snapshots(
    snapshots_dir: str | None,
    limit: int | None,
    branch: str | None,
    output_json: bool,
) -> None:
    """List all temporal snapshots in reverse chronological order.

    Shows key, timestamp, version, and key metrics (nodes, edges, files, dirs)
    for each snapshot.
    """
    snapshots_path = (
        Path(snapshots_dir).resolve() if snapshots_dir else Path.cwd() / ".filetreekg" / "snapshots"
    )
    mgr = SnapshotManager(snapshots_path)
    snapshots = mgr.list_snapshots(limit=limit, branch=branch)

    if not snapshots:
        click.echo("No snapshots found.")
        return

    if output_json:
        click.echo(json.dumps(snapshots, indent=2))
    else:
        click.echo(
            f"{'Key':<12} {'Timestamp':<20} {'Branch':<12} {'Version':<8} "
            f"{'Nodes':<6} {'Edges':<6} {'Files':<6} {'Dirs':<6}"
        )
        click.echo("-" * 90)
        for snap in snapshots:
            key = snap["key"][:12]
            ts = snap.get("timestamp", "")
            ts_display = ts[:16].replace("T", " ") if ts else "unknown"
            branch_val = snap.get("branch", "")[:12]
            ver = snap.get("version", "")[:8]
            nodes = snap["metrics"]["total_nodes"]
            edges = snap["metrics"]["total_edges"]
            files = snap["metrics"].get("total_files", 0)
            dirs = snap["metrics"].get("total_dirs", 0)
            click.echo(
                f"{key:<12} {ts_display:<20} {branch_val:<12} {ver:<8} "
                f"{nodes:<6} {edges:<6} {files:<6} {dirs:<6}"
            )


@snapshot.command("show")
@click.argument("key", metavar="KEY")
@click.option(
    "--snapshots-dir",
    default=None,
    type=click.Path(exists=True),
    help="Snapshots directory (default: .filetreekg/snapshots).",
)
def show_snapshot(key: str, snapshots_dir: str | None) -> None:
    """Display full details for a single snapshot by key (tree hash) or 'latest'.

    Shows all metrics, node/edge breakdown, top-level dir counts, and deltas
    vs. previous and baseline snapshots.
    """
    snapshots_path = (
        Path(snapshots_dir).resolve() if snapshots_dir else Path.cwd() / ".filetreekg" / "snapshots"
    )
    mgr = SnapshotManager(snapshots_path)
    snap = mgr.load_snapshot(key)

    if not snap:
        click.echo(f"Snapshot not found: {key}", err=True)
        raise click.Abort()

    click.echo(f"Key:       {snap.key}")
    click.echo(f"Branch:    {snap.branch}")
    click.echo(f"Timestamp: {snap.timestamp}")
    click.echo(f"Version:   {snap.version}")
    click.echo()

    m = cast(SnapshotMetrics, snap.metrics)
    click.echo("Metrics:")
    click.echo(f"  Total Nodes:  {m.total_nodes}")
    click.echo(f"  Total Edges:  {m.total_edges}")
    click.echo(f"  Files:        {m.total_files}")
    click.echo(f"  Directories:  {m.total_dirs}")
    click.echo()

    if m.node_counts:
        click.echo("Node Breakdown:")
        for kind, count in sorted(m.node_counts.items()):
            click.echo(f"  {kind}: {count}")
        click.echo()

    if m.edge_counts:
        click.echo("Edge Breakdown:")
        for rel, count in sorted(m.edge_counts.items()):
            click.echo(f"  {rel}: {count}")
        click.echo()

    if m.dir_node_counts:
        click.echo("Top-Level Directory Breakdown:")
        for dir_name, count in sorted(m.dir_node_counts.items(), key=lambda x: x[1], reverse=True)[
            :10
        ]:
            click.echo(f"  {dir_name}: {count}")
        click.echo()

    if snap.vs_previous:
        click.echo("Delta vs. Previous:")
        d = cast(SnapshotDelta, snap.vs_previous)
        click.echo(f"  Nodes:  {d.nodes:+d}")
        click.echo(f"  Edges:  {d.edges:+d}")
        click.echo(f"  Files:  {d.files_delta:+d}")
        click.echo(f"  Dirs:   {d.dirs_delta:+d}")
        click.echo()

    if snap.vs_baseline:
        click.echo("Delta vs. Baseline:")
        d = cast(SnapshotDelta, snap.vs_baseline)
        click.echo(f"  Nodes:  {d.nodes:+d}")
        click.echo(f"  Edges:  {d.edges:+d}")
        click.echo(f"  Files:  {d.files_delta:+d}")
        click.echo(f"  Dirs:   {d.dirs_delta:+d}")


@snapshot.command("prune")
@click.option(
    "--snapshots-dir",
    default=None,
    type=click.Path(),
    help="Snapshots directory (default: .filetreekg/snapshots).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without deleting anything.",
)
def prune_snapshots(snapshots_dir: str | None, dry_run: bool) -> None:
    """
    Remove vestigial snapshots that carry no new metric information.

    Cleans up three categories:

    \b
    1. Metric-duplicates — interior snapshots with unchanged metrics.
    2. Broken entries — manifest entries whose JSON file is missing.
    3. Orphaned files — JSON files on disk not referenced by the manifest.

    The oldest (baseline) and newest (latest) snapshots are always kept.

    Example:
        ftreekg snapshot prune --dry-run
        ftreekg snapshot prune
    """
    snapshots_path = (
        Path(snapshots_dir).resolve() if snapshots_dir else Path.cwd() / ".filetreekg" / "snapshots"
    )
    mgr = SnapshotManager(snapshots_path)
    result = mgr.prune_snapshots(dry_run=dry_run)

    prefix = "[dry-run] " if dry_run else ""
    if result.total_cleaned == 0:
        click.echo("Nothing to prune.")
        return

    if result.removed:
        click.echo(f"{prefix}Metric-duplicates removed: {len(result.removed)}")
        for key in result.removed:
            click.echo(f"  - {key}")
    if result.broken_entries:
        click.echo(f"{prefix}Broken manifest entries removed: {len(result.broken_entries)}")
        for key in result.broken_entries:
            click.echo(f"  - {key}")
    if result.orphaned_files:
        click.echo(f"{prefix}Orphaned JSON files removed: {len(result.orphaned_files)}")
        for fname in result.orphaned_files:
            click.echo(f"  - {fname}")

    action = "would be" if dry_run else "were"
    click.echo(f"\nTotal: {result.total_cleaned} item(s) {action} cleaned.")


@snapshot.command("diff")
@click.argument("key_a", metavar="KEY_A")
@click.argument("key_b", metavar="KEY_B")
@click.option(
    "--snapshots-dir",
    default=None,
    type=click.Path(exists=True),
    help="Snapshots directory (default: .filetreekg/snapshots).",
)
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
def diff_snapshots(
    key_a: str,
    key_b: str,
    snapshots_dir: str | None,
    output_json: bool,
) -> None:
    """Compare two snapshots side-by-side (B − A).

    Shows metrics from both snapshots and computed deltas.

    Example:
        ftreekg snapshot diff 660e4f0a 3487ed5b
    """
    snapshots_path = (
        Path(snapshots_dir).resolve() if snapshots_dir else Path.cwd() / ".filetreekg" / "snapshots"
    )
    mgr = SnapshotManager(snapshots_path)
    result = mgr.diff_snapshots(key_a, key_b)

    if "error" in result:
        click.echo(f"Error: {result['error']}", err=True)
        raise click.Abort()

    if output_json:
        click.echo(json.dumps(result, indent=2))
    else:
        a = result["a"]
        b = result["b"]
        click.echo(f"Comparing {a['key'][:10]} vs {b['key'][:10]}")
        click.echo()
        click.echo(f"{'Metric':<20} {'A':<12} {'B':<12} {'Δ':<12}")
        click.echo("-" * 56)

        for key in ["total_nodes", "total_edges", "total_files", "total_dirs"]:
            val_a = a["metrics"].get(key, 0)
            val_b = b["metrics"].get(key, 0)
            click.echo(f"{key:<20} {val_a:<12} {val_b:<12} {val_b - val_a:+d}")

        dir_delta = result.get("dir_node_counts_delta", {})
        if dir_delta:
            click.echo()
            click.echo("Changed Directories:")
            for dir_name, delta in sorted(dir_delta.items(), key=lambda x: abs(x[1]), reverse=True)[
                :10
            ]:
                click.echo(f"  {dir_name}: {delta:+d}")
