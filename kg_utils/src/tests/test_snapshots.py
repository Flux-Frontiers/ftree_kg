"""Tests for kg_utils.snapshots."""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_utils.snapshots import PruneResult, Snapshot, SnapshotManifest, SnapshotManager


# -- Snapshot model ----------------------------------------------------------


def test_snapshot_to_from_dict() -> None:
    snap = Snapshot(
        branch="main",
        timestamp="2026-01-01T00:00:00+00:00",
        version="1.0.0",
        metrics={"total_nodes": 10, "total_edges": 5},
        tree_hash="abc123",
    )
    d = snap.to_dict()
    assert d["key"] == "abc123"
    assert d["metrics"]["total_nodes"] == 10

    restored = Snapshot.from_dict(d)
    assert restored.key == "abc123"
    assert restored.metrics["total_nodes"] == 10
    assert restored.branch == "main"


def test_snapshot_key_property() -> None:
    snap = Snapshot(branch="main", timestamp="", metrics={}, tree_hash="deadbeef")
    assert snap.key == "deadbeef"


# -- SnapshotManifest --------------------------------------------------------


def test_manifest_round_trip() -> None:
    m = SnapshotManifest(
        format_version="1.0",
        last_update="2026-01-01",
        snapshots=[{"key": "a", "timestamp": "t1"}],
    )
    d = m.to_dict()
    restored = SnapshotManifest.from_dict(d)
    assert len(restored.snapshots) == 1
    assert restored.snapshots[0]["key"] == "a"


# -- SnapshotManager ---------------------------------------------------------


@pytest.fixture
def mgr(tmp_path: Path) -> SnapshotManager:
    return SnapshotManager(tmp_path / "snapshots", package_name="test-pkg")


def test_capture_and_save(mgr: SnapshotManager) -> None:
    snap = mgr.capture(
        version="0.1.0",
        branch="test",
        graph_stats_dict={"total_nodes": 5, "total_edges": 3},
        tree_hash="hash1",
    )
    assert snap.key == "hash1"
    assert snap.metrics["total_nodes"] == 5

    path = mgr.save_snapshot(snap)
    assert path is not None and path.exists()


def test_save_rejects_zero_nodes(mgr: SnapshotManager) -> None:
    snap = mgr.capture(
        version="0.1.0",
        branch="test",
        graph_stats_dict={"total_nodes": 0, "total_edges": 0},
        tree_hash="empty",
    )
    with pytest.raises(ValueError, match="0 nodes"):
        mgr.save_snapshot(snap)


def test_load_snapshot(mgr: SnapshotManager) -> None:
    snap = mgr.capture(
        version="0.1.0", branch="test",
        graph_stats_dict={"total_nodes": 10, "total_edges": 5},
        tree_hash="loadtest",
    )
    mgr.save_snapshot(snap)

    loaded = mgr.load_snapshot("loadtest")
    assert loaded is not None
    assert loaded.metrics["total_nodes"] == 10


def test_load_latest(mgr: SnapshotManager) -> None:
    snap = mgr.capture(
        version="0.1.0", branch="test",
        graph_stats_dict={"total_nodes": 7, "total_edges": 2},
        tree_hash="latest1",
    )
    mgr.save_snapshot(snap)

    latest = mgr.load_snapshot("latest")
    assert latest is not None
    assert latest.key == "latest1"


def test_list_snapshots(mgr: SnapshotManager) -> None:
    for i, h in enumerate(["aaa", "bbb"]):
        snap = mgr.capture(
            version="0.1.0", branch="test",
            graph_stats_dict={"total_nodes": 10 + i, "total_edges": 5},
            tree_hash=h,
        )
        mgr.save_snapshot(snap, force=True)

    snaps = mgr.list_snapshots()
    assert len(snaps) == 2


def test_diff_snapshots(mgr: SnapshotManager) -> None:
    s1 = mgr.capture(
        version="0.1.0", branch="test",
        graph_stats_dict={"total_nodes": 10, "total_edges": 5, "node_counts": {"file": 10}},
        tree_hash="diff_a",
    )
    s2 = mgr.capture(
        version="0.1.0", branch="test",
        graph_stats_dict={"total_nodes": 15, "total_edges": 8, "node_counts": {"file": 15}},
        tree_hash="diff_b",
    )
    mgr.save_snapshot(s1, force=True)
    mgr.save_snapshot(s2, force=True)

    result = mgr.diff_snapshots("diff_a", "diff_b")
    assert "error" not in result
    assert result["delta"]["nodes"] == 5
    assert result["delta"]["edges"] == 3


def test_prune_dry_run(mgr: SnapshotManager) -> None:
    for h in ["p1", "p2", "p3"]:
        snap = mgr.capture(
            version="0.1.0", branch="test",
            graph_stats_dict={"total_nodes": 10, "total_edges": 5},
            tree_hash=h,
        )
        mgr.save_snapshot(snap, force=True)

    result = mgr.prune_snapshots(dry_run=True)
    assert isinstance(result, PruneResult)
    assert result.dry_run is True
    # p2 is a metric-duplicate interior entry
    assert len(result.removed) == 1


def test_prune_result_total_cleaned() -> None:
    pr = PruneResult(removed=["a"], orphaned_files=["b.json"], broken_entries=["c"], dry_run=False)
    assert pr.total_cleaned == 3
