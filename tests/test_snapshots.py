"""tests/test_snapshots.py

Tests for FileTreeKG temporal snapshots:
  SnapshotMetrics, SnapshotDelta, FtreeSnapshotManager
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

pytest.importorskip("kg_utils.snapshots", reason="kg_utils required for snapshot tests")

from ftree_kg.module import FileTreeKG  # noqa: E402
from ftree_kg.snapshots import (  # noqa: E402
    Snapshot,
    SnapshotDelta,
    SnapshotManager,
    SnapshotMetrics,
    delta_from_dict,
    delta_to_dict,
    metrics_from_dict,
    metrics_to_dict,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kg(tmp_path: Path) -> FileTreeKG:
    """Build a small FileTreeKG (no embeddings) over a fixture filesystem."""
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").touch()
    (tmp_path / "dir2").mkdir()
    (tmp_path / "file2.txt").touch()

    instance = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / ".filetreekg" / "graph.sqlite",
        vectors_path=tmp_path / ".filetreekg" / "vectors.sqlite",
    )
    instance.build(wipe=True, embed=False)
    return instance


@pytest.fixture
def snapshots_dir(tmp_path: Path) -> Path:
    """Temporary snapshots directory."""
    d = tmp_path / ".filetreekg" / "snapshots"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def sample_metrics() -> SnapshotMetrics:
    return SnapshotMetrics(
        total_nodes=10,
        total_edges=12,
        node_counts={"file": 6, "directory": 4},
        edge_counts={"CONTAINS": 12},
        total_files=6,
        total_dirs=4,
        dir_node_counts={"src": 5, "tests": 5},
    )


# ---------------------------------------------------------------------------
# SnapshotMetrics
# ---------------------------------------------------------------------------


def test_snapshot_metrics_fields(sample_metrics: SnapshotMetrics) -> None:
    assert sample_metrics.total_nodes == 10
    assert sample_metrics.total_edges == 12
    assert sample_metrics.total_files == 6
    assert sample_metrics.total_dirs == 4
    assert sample_metrics.node_counts["file"] == 6
    assert sample_metrics.edge_counts["CONTAINS"] == 12
    assert sample_metrics.dir_node_counts["src"] == 5


def test_snapshot_metrics_dir_node_counts_default() -> None:
    m = SnapshotMetrics(
        total_nodes=1,
        total_edges=0,
        node_counts={},
        edge_counts={},
        total_files=0,
        total_dirs=0,
    )
    assert m.dir_node_counts == {}


def test_metrics_to_from_dict_round_trip(sample_metrics: SnapshotMetrics) -> None:
    restored = metrics_from_dict(metrics_to_dict(sample_metrics))
    assert restored == sample_metrics


# ---------------------------------------------------------------------------
# SnapshotDelta
# ---------------------------------------------------------------------------


def test_snapshot_delta_defaults() -> None:
    d = SnapshotDelta()
    assert d.nodes == 0
    assert d.edges == 0
    assert d.files_delta == 0
    assert d.dirs_delta == 0


def test_delta_to_from_dict_round_trip() -> None:
    d = SnapshotDelta(nodes=3, edges=5, files_delta=2, dirs_delta=1)
    assert delta_from_dict(delta_to_dict(d)) == d


def test_delta_from_dict_none_returns_none() -> None:
    assert delta_from_dict(None) is None


# ---------------------------------------------------------------------------
# SnapshotManager — capture / save / load
# ---------------------------------------------------------------------------


def test_capture_hydrates_metrics_as_dataclass(
    kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path
) -> None:
    """capture() must return Snapshot.metrics as a SnapshotMetrics instance."""
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", stats_dict=kg.stats())

    assert isinstance(snap.metrics, SnapshotMetrics)
    m = cast(SnapshotMetrics, snap.metrics)
    assert m.total_nodes > 0
    assert m.total_files >= 0
    assert m.total_dirs >= 0


def test_capture_accepts_legacy_stats_dict_kwarg(
    kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path
) -> None:
    """``stats_dict`` is the FileTreeKG-specific legacy alias for ``graph_stats_dict``."""
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="v", branch="b", stats_dict=kg.stats())
    m = cast(SnapshotMetrics, snap.metrics)
    assert m.total_nodes == kg.stats()["total_nodes"]


def test_save_and_load_round_trip(kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", stats_dict=kg.stats())
    saved = mgr.save_snapshot(snap)
    assert saved is not None and saved.exists()

    loaded = mgr.load_snapshot(snap.key)
    assert loaded is not None
    assert isinstance(loaded.metrics, SnapshotMetrics)
    lm = cast(SnapshotMetrics, loaded.metrics)
    om = cast(SnapshotMetrics, snap.metrics)
    assert lm.total_nodes == om.total_nodes
    assert lm.total_edges == om.total_edges


def test_load_snapshot_latest_alias(kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", stats_dict=kg.stats())
    mgr.save_snapshot(snap)

    latest = mgr.load_snapshot("latest")
    assert latest is not None
    assert latest.key == snap.key


def test_load_missing_snapshot_returns_none(snapshots_dir: Path) -> None:
    mgr = SnapshotManager(snapshots_dir)
    assert mgr.load_snapshot("does-not-exist") is None


# ---------------------------------------------------------------------------
# SnapshotManager — list / diff
# ---------------------------------------------------------------------------


def test_list_snapshots(kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", stats_dict=kg.stats())
    mgr.save_snapshot(snap)

    snaps = mgr.list_snapshots()
    assert len(snaps) == 1
    assert snaps[0]["key"] == snap.key


def test_diff_snapshots_zero_delta_for_identical_stats(
    kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path
) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    stats = kg.stats()

    snap_a = mgr.capture(version="0.0.0-a", branch="test", stats_dict=stats, tree_hash="aaaa")
    snap_b = mgr.capture(version="0.0.0-b", branch="test", stats_dict=stats, tree_hash="bbbb")
    mgr.save_snapshot(snap_a)
    mgr.save_snapshot(snap_b)

    result = mgr.diff_snapshots("aaaa", "bbbb")
    assert "error" not in result
    assert result["delta"]["nodes"] == 0
    assert result["delta"]["files_delta"] == 0
    assert result["delta"]["dirs_delta"] == 0


def test_diff_snapshots_includes_filesystem_deltas(snapshots_dir: Path, tmp_path: Path) -> None:
    """``files_delta`` / ``dirs_delta`` are FileTreeKG-specific extensions."""
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")

    stats_a: dict[str, object] = {
        "total_nodes": 5,
        "total_edges": 4,
        "node_counts": {"file": 3, "directory": 2},
        "edge_counts": {"CONTAINS": 4},
    }
    stats_b: dict[str, object] = {
        "total_nodes": 8,
        "total_edges": 7,
        "node_counts": {"file": 5, "directory": 3},
        "edge_counts": {"CONTAINS": 7},
    }

    snap_a = mgr.capture(version="a", branch="t", stats_dict=stats_a, tree_hash="aaaa")
    snap_b = mgr.capture(version="b", branch="t", stats_dict=stats_b, tree_hash="bbbb")
    mgr.save_snapshot(snap_a)
    mgr.save_snapshot(snap_b)

    result = mgr.diff_snapshots("aaaa", "bbbb")
    assert result["delta"]["files_delta"] == 2
    assert result["delta"]["dirs_delta"] == 1


def test_diff_snapshots_missing_keys_returns_error(snapshots_dir: Path) -> None:
    mgr = SnapshotManager(snapshots_dir)
    result = mgr.diff_snapshots("nope-a", "nope-b")
    assert "error" in result


# ---------------------------------------------------------------------------
# kg_utils.snapshots integration — locks in the post-migration import path
# ---------------------------------------------------------------------------


def test_snapshot_re_export_origin() -> None:
    """``Snapshot`` and ``SnapshotManifest`` must come from kg_utils.snapshots,
    not the deprecated kg_snapshot package."""
    from ftree_kg.snapshots import Snapshot as ReExportedSnapshot
    from ftree_kg.snapshots import SnapshotManifest as ReExportedManifest

    assert ReExportedSnapshot.__module__.startswith("kg_utils.")
    assert ReExportedManifest.__module__.startswith("kg_utils.")
    assert isinstance(Snapshot, type)
