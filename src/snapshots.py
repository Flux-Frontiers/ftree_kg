"""snapshots.py — Temporal Snapshots of FileTreeKG Metrics

Provides infrastructure for capturing, storing, and comparing metrics snapshots.
Each snapshot is keyed by git tree hash and contains:
  - Timestamp and branch metadata
  - Full stats() output (node/edge counts by kind)
  - Filesystem-specific metrics (total files, dirs, top-level dir breakdown)
  - Deltas vs. previous and baseline snapshots

Snapshots are stored in .filetreekg/snapshots/ as JSON blobs, with a manifest
index (manifest.json) tracking all snapshots and their metadata.

Usage
-----
>>> from src.snapshots import SnapshotManager
>>> mgr = SnapshotManager(".filetreekg/snapshots", db_path=".filetreekg/graph.sqlite")
>>> snapshot = mgr.capture(version="v0.1.0", branch="main", stats_dict=kg.stats())
>>> mgr.save_snapshot(snapshot)
>>> prev = mgr.get_previous(tree_hash)
"""

from __future__ import annotations

import importlib.metadata
import json
import sqlite3
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _package_version() -> str:
    """Return the installed ftree-kg package version, or 'unknown'."""
    try:
        return importlib.metadata.version("ftree-kg")
    except importlib.metadata.PackageNotFoundError:
        try:
            return importlib.metadata.version("filetreekg")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"


@dataclass
class SnapshotMetrics:
    """Core metrics captured in a FileTreeKG snapshot."""

    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]  # by kind: file, directory, symlink
    edge_counts: dict[str, int]  # by relation: CONTAINS, CHILD_OF, PARENT_OF
    total_files: int  # node_counts.get("file", 0)
    total_dirs: int  # node_counts.get("directory", 0)
    dir_node_counts: dict[str, int] = field(default_factory=dict)  # nodes per top-level dir


@dataclass
class SnapshotDelta:
    """Deltas comparing this snapshot to a baseline or previous snapshot."""

    nodes: int = 0
    edges: int = 0
    files_delta: int = 0
    dirs_delta: int = 0


@dataclass
class Snapshot:
    """A temporal snapshot of FileTreeKG metrics."""

    branch: str  # git branch name
    timestamp: str  # ISO 8601 UTC
    metrics: SnapshotMetrics
    version: str = ""  # e.g., "0.1.0"; auto-detected from package if not supplied
    vs_previous: SnapshotDelta | None = None
    vs_baseline: SnapshotDelta | None = None
    tree_hash: str = ""  # git tree hash; stable file key

    @property
    def key(self) -> str:
        """Stable file key: tree hash."""
        return self.tree_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "key": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "version": self.version,
            "metrics": asdict(self.metrics),
            "vs_previous": asdict(self.vs_previous) if self.vs_previous else None,
            "vs_baseline": asdict(self.vs_baseline) if self.vs_baseline else None,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Snapshot:
        """Reconstruct from dict loaded from JSON."""
        raw = dict(data)

        metrics_data = raw.pop("metrics")
        # Back-fill fields added in later versions
        metrics_data.setdefault("total_files", metrics_data.get("node_counts", {}).get("file", 0))
        metrics_data.setdefault(
            "total_dirs", metrics_data.get("node_counts", {}).get("directory", 0)
        )
        metrics_data.setdefault("dir_node_counts", {})
        metrics = SnapshotMetrics(**metrics_data)

        vs_prev_data = raw.pop("vs_previous", None)
        vs_prev = SnapshotDelta(**vs_prev_data) if vs_prev_data else None

        vs_base_data = raw.pop("vs_baseline", None)
        vs_base = SnapshotDelta(**vs_base_data) if vs_base_data else None

        # Normalise key field (legacy snapshots may use 'tree_hash')
        if "key" not in raw and "tree_hash" in raw:
            raw["key"] = raw.pop("tree_hash")
        else:
            raw.pop("tree_hash", None)

        key = raw.pop("key", "")
        raw.setdefault("version", "")

        return Snapshot(
            tree_hash=key,
            metrics=metrics,
            vs_previous=vs_prev,
            vs_baseline=vs_base,
            **raw,
        )


@dataclass
class SnapshotManifest:
    """Index of all snapshots, with fast lookup by tree hash."""

    format_version: str = "1.0"
    last_update: str = ""
    snapshots: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "format": self.format_version,
            "last_update": self.last_update,
            "snapshots": self.snapshots,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SnapshotManifest:
        """Reconstruct from dict."""
        return SnapshotManifest(
            format_version=data.get("format", "1.0"),
            last_update=data.get("last_update", ""),
            snapshots=data.get("snapshots", []),
        )


class SnapshotManager:
    """Manages FileTreeKG snapshot storage, retrieval, and comparison."""

    def __init__(
        self,
        snapshots_dir: Path | str,
        db_path: Path | str | None = None,
    ) -> None:
        """Initialize snapshot manager.

        :param snapshots_dir: Directory to store snapshot JSON files and manifest.
        :param db_path: Optional path to the SQLite graph database. When provided,
                        ``capture()`` will query per-directory node counts automatically.
        """
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.snapshots_dir / "manifest.json"
        self.db_path = Path(db_path) if db_path else None

    def capture(
        self,
        version: str | None = None,
        branch: str | None = None,
        stats_dict: dict[str, Any] | None = None,
        tree_hash: str = "",
    ) -> Snapshot:
        """Capture a snapshot from current FileTreeKG state.

        :param version: Version string (e.g., "0.1.0"); auto-detected if None.
        :param branch: Git branch name; auto-detected if None.
        :param stats_dict: Output from ``kg.stats()``.
        :param tree_hash: Git tree hash; auto-detected if not provided.
        :return: New Snapshot instance.
        """
        if not version:
            version = _package_version()
        if branch is None:
            branch = self._get_current_branch()
        if not tree_hash:
            tree_hash = self._get_current_tree_hash()
        if stats_dict is None:
            stats_dict = {}

        timestamp = datetime.now(UTC).isoformat()
        node_counts: dict[str, int] = stats_dict.get("node_counts", {})
        edge_counts: dict[str, int] = stats_dict.get("edge_counts", {})

        metrics = SnapshotMetrics(
            total_nodes=stats_dict.get("total_nodes", 0),
            total_edges=stats_dict.get("total_edges", 0),
            node_counts=node_counts,
            edge_counts=edge_counts,
            total_files=node_counts.get("file", 0),
            total_dirs=node_counts.get("directory", 0),
            dir_node_counts=self._collect_dir_node_counts(),
        )

        snapshot = Snapshot(
            branch=branch,
            timestamp=timestamp,
            version=version,
            metrics=metrics,
            tree_hash=tree_hash,
        )

        prev = self.get_previous(tree_hash)
        if prev:
            snapshot.vs_previous = self._compute_delta(snapshot, prev)

        baseline = self.get_baseline()
        if baseline:
            snapshot.vs_baseline = self._compute_delta(snapshot, baseline)

        return snapshot

    def save_snapshot(self, snapshot: Snapshot) -> Path:
        """Save snapshot to .filetreekg/snapshots/{key}.json and update manifest.

        Snapshots with zero nodes are rejected — they represent an unbuilt index.

        :param snapshot: Snapshot to save.
        :return: Path to saved snapshot file.
        :raises ValueError: If the snapshot has zero nodes.
        """
        if snapshot.metrics.total_nodes == 0:
            raise ValueError(
                "Refusing to save degenerate snapshot with 0 nodes. "
                "Run 'ftreekg build' before capturing a snapshot."
            )

        snapshot_file = self.snapshots_dir / f"{snapshot.key}.json"
        with open(snapshot_file, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

        # Update manifest
        manifest = self.load_manifest()
        existing_idx = next(
            (i for i, s in enumerate(manifest.snapshots) if s.get("key") == snapshot.key),
            None,
        )
        manifest_entry: dict[str, Any] = {
            "key": snapshot.key,
            "branch": snapshot.branch,
            "timestamp": snapshot.timestamp,
            "version": snapshot.version,
            "file": snapshot_file.name,
            "metrics": asdict(snapshot.metrics),
            "deltas": {
                "vs_previous": asdict(snapshot.vs_previous) if snapshot.vs_previous else None,
                "vs_baseline": asdict(snapshot.vs_baseline) if snapshot.vs_baseline else None,
            },
        }

        if existing_idx is not None:
            manifest.snapshots[existing_idx] = manifest_entry
        else:
            manifest.snapshots.append(manifest_entry)

        manifest.last_update = datetime.now(UTC).isoformat()
        self._save_manifest(manifest)

        return snapshot_file

    def load_manifest(self) -> SnapshotManifest:
        """Load manifest.json; return empty manifest if it does not exist."""
        if not self.manifest_path.exists():
            return SnapshotManifest()
        with open(self.manifest_path) as f:
            manifest = SnapshotManifest.from_dict(json.load(f))
        # Normalise legacy 'tree_hash' → 'key'
        for entry in manifest.snapshots:
            if "key" not in entry and "tree_hash" in entry:
                entry["key"] = entry.pop("tree_hash")
        return manifest

    def _save_manifest(self, manifest: SnapshotManifest) -> None:
        """Write manifest.json."""
        with open(self.manifest_path, "w") as f:
            json.dump(manifest.to_dict(), f, indent=2)

    def load_snapshot(self, key: str) -> Snapshot | None:
        """Load a snapshot by key (tree hash), or 'latest'."""
        if key == "latest":
            manifest = self.load_manifest()
            if not manifest.snapshots:
                return None
            entry = max(manifest.snapshots, key=lambda x: x.get("timestamp", ""))
            key = entry["key"]

        snapshot_file = self.snapshots_dir / f"{key}.json"
        if not snapshot_file.exists():
            return None
        with open(snapshot_file) as f:
            snap = Snapshot.from_dict(json.load(f))

        # Back-fill deltas for legacy snapshots that predate persisted deltas
        if snap.vs_previous is None or snap.vs_baseline is None:
            manifest = self.load_manifest()
            entries = sorted(manifest.snapshots, key=lambda x: x.get("timestamp", ""), reverse=True)
            idx = next((i for i, s in enumerate(entries) if s.get("key") == snap.key), None)

            if idx is not None:
                if snap.vs_previous is None and idx + 1 < len(entries):
                    prev_m = entries[idx + 1].get("metrics", {})
                    snap.vs_previous = SnapshotDelta(
                        nodes=snap.metrics.total_nodes - prev_m.get("total_nodes", 0),
                        edges=snap.metrics.total_edges - prev_m.get("total_edges", 0),
                        files_delta=snap.metrics.total_files - prev_m.get("total_files", 0),
                        dirs_delta=snap.metrics.total_dirs - prev_m.get("total_dirs", 0),
                    )
                if snap.vs_baseline is None and entries:
                    base_m = entries[-1].get("metrics", {})
                    snap.vs_baseline = SnapshotDelta(
                        nodes=snap.metrics.total_nodes - base_m.get("total_nodes", 0),
                        edges=snap.metrics.total_edges - base_m.get("total_edges", 0),
                        files_delta=snap.metrics.total_files - base_m.get("total_files", 0),
                        dirs_delta=snap.metrics.total_dirs - base_m.get("total_dirs", 0),
                    )
        return snap

    def get_previous(self, key: str) -> Snapshot | None:
        """Get the snapshot immediately before this one (by timestamp)."""
        manifest = self.load_manifest()
        current_ts = next((s["timestamp"] for s in manifest.snapshots if s.get("key") == key), None)
        if not current_ts:
            return None
        prev_entry = None
        for s in sorted(manifest.snapshots, key=lambda x: x["timestamp"], reverse=True):
            if s["timestamp"] < current_ts:
                prev_entry = s
                break
        return self.load_snapshot(prev_entry["key"]) if prev_entry else None

    def get_baseline(self) -> Snapshot | None:
        """Get the oldest snapshot (baseline for comparison)."""
        manifest = self.load_manifest()
        if not manifest.snapshots:
            return None
        baseline_entry = min(manifest.snapshots, key=lambda x: x["timestamp"])
        return self.load_snapshot(baseline_entry["key"])

    def list_snapshots(
        self,
        limit: int | None = None,
        branch: str | None = None,
    ) -> list[dict[str, Any]]:
        """List all snapshots in reverse chronological order.

        Missing ``vs_previous`` deltas are computed on-the-fly from adjacent manifest
        entries so that every entry (except the oldest) carries a delta.

        :param limit: Max number to return; ``None`` = all.
        :param branch: If provided, only return snapshots from this branch.
        :return: List of snapshot metadata dicts.
        """
        manifest = self.load_manifest()
        all_snaps = sorted(manifest.snapshots, key=lambda x: x["timestamp"], reverse=True)

        if branch is not None:
            all_snaps = [s for s in all_snaps if s.get("branch") == branch]

        for i, snap in enumerate(all_snaps):
            if snap.get("deltas", {}).get("vs_previous") is None and i + 1 < len(all_snaps):
                prev = all_snaps[i + 1]
                snap.setdefault("deltas", {})["vs_previous"] = {
                    "nodes": snap["metrics"]["total_nodes"] - prev["metrics"]["total_nodes"],
                    "edges": snap["metrics"]["total_edges"] - prev["metrics"]["total_edges"],
                    "files_delta": snap["metrics"].get("total_files", 0)
                    - prev["metrics"].get("total_files", 0),
                    "dirs_delta": snap["metrics"].get("total_dirs", 0)
                    - prev["metrics"].get("total_dirs", 0),
                }

        return all_snaps[:limit] if limit else all_snaps

    def diff_snapshots(self, key_a: str, key_b: str) -> dict[str, Any]:
        """Compare two snapshots side-by-side.

        :param key_a: First snapshot key (tree hash).
        :param key_b: Second snapshot key (tree hash).
        :return: Dict with metrics from both and computed deltas.
        """
        snap_a = self.load_snapshot(key_a)
        snap_b = self.load_snapshot(key_b)

        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}

        all_node_kinds = set(snap_a.metrics.node_counts) | set(snap_b.metrics.node_counts)
        all_edge_rels = set(snap_a.metrics.edge_counts) | set(snap_b.metrics.edge_counts)

        node_counts_delta = {
            k: snap_b.metrics.node_counts.get(k, 0) - snap_a.metrics.node_counts.get(k, 0)
            for k in all_node_kinds
        }
        edge_counts_delta = {
            k: snap_b.metrics.edge_counts.get(k, 0) - snap_a.metrics.edge_counts.get(k, 0)
            for k in all_edge_rels
        }

        all_dirs = set(snap_a.metrics.dir_node_counts) | set(snap_b.metrics.dir_node_counts)
        dir_node_counts_delta = {
            d: snap_b.metrics.dir_node_counts.get(d, 0) - snap_a.metrics.dir_node_counts.get(d, 0)
            for d in all_dirs
            if snap_b.metrics.dir_node_counts.get(d, 0) != snap_a.metrics.dir_node_counts.get(d, 0)
        }

        return {
            "a": {"key": snap_a.key, "metrics": asdict(snap_a.metrics)},
            "b": {"key": snap_b.key, "metrics": asdict(snap_b.metrics)},
            "delta": asdict(self._compute_delta(snap_b, snap_a)),
            "node_counts_delta": node_counts_delta,
            "edge_counts_delta": edge_counts_delta,
            "dir_node_counts_delta": dir_node_counts_delta,
        }

    @staticmethod
    def _compute_delta(snap_new: Snapshot, snap_old: Snapshot) -> SnapshotDelta:
        """Compute metrics delta (new − old)."""
        return SnapshotDelta(
            nodes=snap_new.metrics.total_nodes - snap_old.metrics.total_nodes,
            edges=snap_new.metrics.total_edges - snap_old.metrics.total_edges,
            files_delta=snap_new.metrics.total_files - snap_old.metrics.total_files,
            dirs_delta=snap_new.metrics.total_dirs - snap_old.metrics.total_dirs,
        )

    def _collect_dir_node_counts(self) -> dict[str, int]:
        """Query SQLite for node counts grouped by top-level directory.

        :return: Dict mapping top-level dir name to node count, or empty dict
                 if the DB is unavailable or the query fails.
        """
        if not self.db_path or not self.db_path.exists():
            return {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT source_path, COUNT(*) FROM nodes GROUP BY source_path"
                ).fetchall()
            counts: dict[str, int] = {}
            for source_path, count in rows:
                if not source_path:
                    continue
                top = source_path.split("/")[0] if "/" in source_path else source_path
                counts[top] = counts.get(top, 0) + count
            return counts
        except sqlite3.Error:
            return {}

    @staticmethod
    def _get_current_tree_hash() -> str:
        """Get current git tree hash (HEAD^{tree})."""
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    @staticmethod
    def _get_current_branch() -> str:
        """Get current git branch name."""
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"
