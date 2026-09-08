"""snapshots.py — FileTreeKG Temporal Snapshots (thin layer over kg_utils.snapshots)

``Snapshot``, ``SnapshotManifest`` and ``PruneResult`` are re-exported from
``kg_utils.snapshots`` unchanged.  A snapshot's ``metrics``, ``vs_previous``
and ``vs_baseline`` are plain dicts, which is what the shared manager reads
and writes.

This module adds:

  - ``SnapshotMetrics`` / ``SnapshotDelta`` — domain dataclasses, used as
    converters by callers that want attribute access.  Convert with
    ``metrics_from_dict`` / ``metrics_to_dict`` and ``delta_from_dict`` /
    ``delta_to_dict``; a ``Snapshot`` never holds one.
  - ``FtreeSnapshotManager``, which defaults ``package_name`` to ``"ftree-kg"``
    (falling back to ``"filetreekg"``), still accepts the legacy ``stats_dict``
    keyword via ``capture_aliases``, adds ``total_files``, ``total_dirs`` and
    ``dir_node_counts`` to the metrics, adds ``files_delta`` and ``dirs_delta``
    to deltas, and extends a diff with ``dir_node_counts_delta``.

The name ``SnapshotManager`` is re-exported as an alias for
``FtreeSnapshotManager`` so that ``from ftree_kg.snapshots import SnapshotManager``
continues to work unchanged.

Do not hydrate a ``Snapshot``'s structured fields into these dataclasses.  This
module used to overwrite ``metrics``, ``vs_previous`` and ``vs_baseline`` with
dataclass instances after every load and convert them back before every save,
which meant ``load_snapshot``, ``save_snapshot`` and ``diff_snapshots`` all
needed overrides.  In the sibling repos the equivalent ``save_snapshot``
override dropped ``snapshot_key``, ``subject`` and ``tool`` on the way to disk.

Usage
-----
>>> from ftree_kg.snapshots import SnapshotManager, metrics_from_dict
>>> mgr = SnapshotManager(".filetreekg/snapshots", db_path=".filetreekg/graph.sqlite")
>>> snapshot = mgr.capture(version="0.15.0", key="v0.15.0", subject="repo:ftree-kg")
>>> mgr.save_snapshot(snapshot)
>>> metrics_from_dict(snapshot.metrics).total_files
0

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

import importlib.metadata
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Re-export shared models for backwards compatibility
# ---------------------------------------------------------------------------
from kg_utils.snapshots import (
    PruneResult,  # noqa: F401  re-exported
    Snapshot,
    SnapshotManifest,
)
from kg_utils.snapshots import SnapshotManager as _BaseSnapshotManager

__all__ = [
    "Snapshot",
    "SnapshotManifest",
    "SnapshotManager",
    "SnapshotMetrics",
    "SnapshotDelta",
    "PruneResult",
    "metrics_to_dict",
    "metrics_from_dict",
    "delta_to_dict",
    "delta_from_dict",
]


# ---------------------------------------------------------------------------
# Domain-specific dataclasses (used by cmd_snapshot.py and tests)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def metrics_to_dict(m: SnapshotMetrics) -> dict[str, Any]:
    """Convert a SnapshotMetrics dataclass to a plain dict (for storage)."""
    return {
        "total_nodes": m.total_nodes,
        "total_edges": m.total_edges,
        "node_counts": m.node_counts,
        "edge_counts": m.edge_counts,
        "total_files": m.total_files,
        "total_dirs": m.total_dirs,
        "dir_node_counts": m.dir_node_counts,
    }


def metrics_from_dict(d: dict[str, Any]) -> SnapshotMetrics:
    """Reconstruct a SnapshotMetrics dataclass from a plain dict.

    Back-fills fields that were added in later versions so that legacy
    snapshot JSON continues to load correctly.
    """
    node_counts: dict[str, int] = d.get("node_counts", {})
    d = dict(d)  # don't mutate caller's dict
    d.setdefault("total_files", node_counts.get("file", 0))
    d.setdefault("total_dirs", node_counts.get("directory", 0))
    d.setdefault("dir_node_counts", {})
    return SnapshotMetrics(
        total_nodes=d.get("total_nodes", 0),
        total_edges=d.get("total_edges", 0),
        node_counts=node_counts,
        edge_counts=d.get("edge_counts", {}),
        total_files=d["total_files"],
        total_dirs=d["total_dirs"],
        dir_node_counts=d["dir_node_counts"],
    )


def delta_to_dict(delta: SnapshotDelta) -> dict[str, Any]:
    """Convert a SnapshotDelta dataclass to a plain dict."""
    return {
        "nodes": delta.nodes,
        "edges": delta.edges,
        "files_delta": delta.files_delta,
        "dirs_delta": delta.dirs_delta,
    }


def delta_from_dict(d: dict[str, Any] | None) -> SnapshotDelta | None:
    """Reconstruct a SnapshotDelta from a plain dict, or return None."""
    if d is None:
        return None
    return SnapshotDelta(
        nodes=d.get("nodes", 0),
        edges=d.get("edges", 0),
        files_delta=d.get("files_delta", 0),
        dirs_delta=d.get("dirs_delta", 0),
    )


# ---------------------------------------------------------------------------
# FileTreeKG-specific SnapshotManager
# ---------------------------------------------------------------------------


class FtreeSnapshotManager(_BaseSnapshotManager):
    """FileTreeKG snapshot manager.

    Extends the shared SnapshotManager with:

    - Default package name "ftree-kg" (fallback "filetreekg").
    - The legacy ``stats_dict`` keyword, declared in ``capture_aliases`` and
      routed to the base class's ``graph_stats_dict`` with a
      ``DeprecationWarning``. It was a named parameter on a ``capture()``
      override until 0.16.0; that override is gone.
    - ``total_files``, ``total_dirs`` and ``dir_node_counts`` in the metrics,
      collected by ``_domain_metrics()``.
    - ``files_delta`` and ``dirs_delta`` in delta computation.
    - ``dir_node_counts_delta`` in a diff, via the ``dict_metric_deltas``
      class attribute.
    - Per-directory node counts via ``_collect_dir_node_counts()``.

    Everything else -- saving, loading, listing, pruning, key handling -- is
    inherited unchanged.  Overriding those to hydrate and dehydrate the domain
    dataclasses is what this module used to do, and it is the same pattern
    that dropped the snapshot key in two sibling repos.
    """

    #: ``diff_snapshots`` emits ``dir_node_counts_delta`` from this, holding
    #: only the top-level directories whose node count actually changed.
    #: Replaces a hand-rolled loop over the same dict.
    dict_metric_deltas = ("dir_node_counts",)

    #: ``stats_dict`` is this repo's own legacy alias for ``graph_stats_dict``.
    #: It used to be a named parameter on a ``capture()`` override; that
    #: override is gone. Declared here so the old keyword still routes to the
    #: graph stats and warns, rather than being silently recorded as a metric
    #: named "stats_dict" while the stats themselves go missing.
    capture_aliases = {"stats_dict": "graph_stats_dict"}

    def __init__(
        self,
        snapshots_dir: Path | str,
        db_path: Path | str | None = None,
        *,
        package_name: str = "ftree-kg",
    ) -> None:
        """Initialise.

        :param snapshots_dir: Directory for snapshot JSON files and manifest.
        :param db_path: Optional path to the SQLite graph database.
        :param package_name: Package name for version detection; falls back to
            "filetreekg" if "ftree-kg" is not installed.
        """
        # Resolve the best available package name at construction time.
        resolved_name = package_name
        try:
            importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            try:
                importlib.metadata.version("filetreekg")
                resolved_name = "filetreekg"
            except importlib.metadata.PackageNotFoundError:
                pass  # keep the requested name; _package_version returns 'unknown'

        super().__init__(snapshots_dir, package_name=resolved_name, db_path=db_path)

    # ------------------------------------------------------------------
    # capture — accept legacy stats_dict kwarg, add filesystem metrics
    # ------------------------------------------------------------------

    def _domain_metrics(self, stats: dict[str, Any]) -> dict[str, Any]:
        """Derive the filesystem metrics and collect per-directory counts.

        Called by the inherited ``capture()``. Overriding this rather than
        ``capture()`` is deliberate: a ``capture()`` override has to restate the
        base signature, and restating it is how an unnamed ``key=`` fell into
        ``**extra_metrics`` and shipped sibling packages keyed on a tree hash.

        :param stats: Graph stats passed to ``capture()``.
        :return: ``total_files`` and ``total_dirs`` read off the node counts,
                 plus per-directory node counts from SQLite.
        """
        node_counts: dict[str, int] = stats.get("node_counts", {})
        return {
            "total_files": node_counts.get("file", 0),
            "total_dirs": node_counts.get("directory", 0),
            "dir_node_counts": self._collect_dir_node_counts(),
        }

    # ------------------------------------------------------------------
    # Delta computation — add files_delta and dirs_delta
    # ------------------------------------------------------------------

    def _compute_delta_from_metrics(
        self, new_m: dict[str, Any], old_m: dict[str, Any]
    ) -> dict[str, Any]:
        """Extend base delta with filesystem-specific delta fields."""
        base: dict[str, Any] = super()._compute_delta_from_metrics(new_m, old_m)
        base["files_delta"] = new_m.get("total_files", 0) - old_m.get("total_files", 0)
        base["dirs_delta"] = new_m.get("total_dirs", 0) - old_m.get("total_dirs", 0)
        return base

    # ------------------------------------------------------------------
    # Per-directory node counts (SQLite query)
    # ------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Public alias — keeps ``from ftree_kg.snapshots import SnapshotManager`` working
# ---------------------------------------------------------------------------

SnapshotManager = FtreeSnapshotManager
