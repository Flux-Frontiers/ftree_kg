"""kg_utils/snapshots/models.py — Snapshot data models.

Every snapshot is keyed by git tree hash and contains:
  - Timestamp and branch metadata
  - Metrics dict (domain-flexible: total_nodes, total_edges, node_counts, ...)
  - Hotspots list and issues list
  - Deltas vs. previous and baseline snapshots
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Snapshot:
    """A temporal snapshot of KG metrics.

    ``metrics`` is a free-form dict so that each domain can store whatever
    fields it needs (docstring_coverage, total_files, etc.) without requiring
    changes to this shared data model.  The only required keys are
    ``total_nodes`` and ``total_edges`` -- the manager uses these for delta
    computation.

    ``vs_previous`` and ``vs_baseline`` are also free-form dicts so that
    domain-specific delta fields (coverage_delta, files_delta, ...) can be
    stored alongside the universal ``nodes`` and ``edges`` deltas.
    """

    branch: str
    timestamp: str  # ISO 8601 UTC
    metrics: dict[str, Any]
    version: str = ""
    hotspots: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    vs_previous: dict[str, Any] | None = None
    vs_baseline: dict[str, Any] | None = None
    tree_hash: str = ""

    @property
    def key(self) -> str:
        """Stable file key: git tree hash."""
        return self.tree_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "key": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "version": self.version,
            "metrics": self.metrics,
            "hotspots": self.hotspots,
            "issues": self.issues,
            "vs_previous": self.vs_previous,
            "vs_baseline": self.vs_baseline,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Snapshot:
        """Reconstruct a Snapshot from a dictionary loaded from JSON."""
        raw = dict(data)  # shallow copy to avoid mutating caller's data

        metrics = raw.pop("metrics", {})
        vs_prev = raw.pop("vs_previous", None)
        vs_base = raw.pop("vs_baseline", None)

        # Normalise legacy 'tree_hash' field -> 'key'
        if "key" not in raw and "tree_hash" in raw:
            raw["key"] = raw.pop("tree_hash")
        else:
            raw.pop("tree_hash", None)

        key = raw.pop("key", "")
        raw.pop("commit", None)  # drop legacy field
        raw.setdefault("version", "")

        return Snapshot(
            tree_hash=key,
            metrics=metrics,
            vs_previous=vs_prev,
            vs_baseline=vs_base,
            branch=raw.pop("branch", ""),
            timestamp=raw.pop("timestamp", ""),
            version=raw.pop("version", ""),
            hotspots=raw.pop("hotspots", []),
            issues=raw.pop("issues", []),
        )


@dataclass
class PruneResult:
    """Summary of a :meth:`SnapshotManager.prune_snapshots` operation.

    :param removed: Keys of snapshots pruned as metric-duplicates.
    :param orphaned_files: Filenames of JSON files deleted from disk because
        they were not referenced by the manifest.
    :param broken_entries: Keys of manifest entries whose JSON file was missing.
    :param dry_run: ``True`` when the call was a dry run (nothing deleted).
    """

    removed: list[str]
    orphaned_files: list[str]
    broken_entries: list[str]
    dry_run: bool

    @property
    def total_cleaned(self) -> int:
        """Total number of items removed (or that *would* be removed in dry-run)."""
        return len(self.removed) + len(self.orphaned_files) + len(self.broken_entries)


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
