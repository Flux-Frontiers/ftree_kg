"""tests/test_snapshots.py

Tests for FileTreeKG temporal snapshots:
  SnapshotMetrics, SnapshotDelta, FtreeSnapshotManager
"""

from __future__ import annotations

import json
from pathlib import Path

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


def test_capture_stores_metrics_as_a_plain_dict(
    kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path
) -> None:
    """capture() returns the dict the shared manager reads and writes.

    This module used to overwrite the three structured fields with dataclass
    instances after every load and convert them back before every save, which
    forced overrides of load_snapshot, save_snapshot and diff_snapshots. The
    equivalent save_snapshot override in two sibling repos dropped the
    snapshot key on the way to disk.
    """
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", graph_stats_dict=kg.stats())

    assert isinstance(snap.metrics, dict)
    m = metrics_from_dict(snap.metrics)
    assert m.total_nodes > 0
    assert m.total_files >= 0
    assert m.total_dirs >= 0


def test_save_and_load_round_trip(kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", graph_stats_dict=kg.stats())
    saved = mgr.save_snapshot(snap)
    assert saved is not None and saved.exists()

    loaded = mgr.load_snapshot(snap.key)
    assert loaded is not None
    assert isinstance(loaded.metrics, dict)
    lm = metrics_from_dict(loaded.metrics)
    om = metrics_from_dict(snap.metrics)
    assert lm.total_nodes == om.total_nodes
    assert lm.total_edges == om.total_edges


def test_load_snapshot_latest_alias(kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    snap = mgr.capture(version="0.0.0-test", branch="test", graph_stats_dict=kg.stats())
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
    snap = mgr.capture(version="0.0.0-test", branch="test", graph_stats_dict=kg.stats())
    mgr.save_snapshot(snap)

    snaps = mgr.list_snapshots()
    assert len(snaps) == 1
    assert snaps[0]["key"] == snap.key


def test_diff_snapshots_zero_delta_for_identical_stats(
    kg: FileTreeKG, snapshots_dir: Path, tmp_path: Path
) -> None:
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    stats = kg.stats()

    snap_a = mgr.capture(
        version="0.0.0-a", branch="test", graph_stats_dict=stats, tree_hash="aaaa", key="v0.0.0-a"
    )
    snap_b = mgr.capture(
        version="0.0.0-b", branch="test", graph_stats_dict=stats, tree_hash="bbbb", key="v0.0.0-b"
    )
    mgr.save_snapshot(snap_a)
    mgr.save_snapshot(snap_b)

    result = mgr.diff_snapshots("v0.0.0-a", "v0.0.0-b")
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

    snap_a = mgr.capture(
        version="a", branch="t", graph_stats_dict=stats_a, tree_hash="aaaa", key="va"
    )
    snap_b = mgr.capture(
        version="b", branch="t", graph_stats_dict=stats_b, tree_hash="bbbb", key="vb"
    )
    mgr.save_snapshot(snap_a)
    mgr.save_snapshot(snap_b)

    result = mgr.diff_snapshots("va", "vb")
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


# ---------------------------------------------------------------------------
# Key scheme (kgmodule-utils >= 0.19.0)
# ---------------------------------------------------------------------------


def test_snapshot_is_the_shared_class() -> None:
    """Hydrating the structured fields is what forced the removed overrides.

    A Snapshot that carries dataclasses instead of dicts breaks every shared
    manager method that reads those fields, and each one then needs a
    hand-written copy. One such copy dropped the key in two sibling repos.
    """
    from kg_utils.snapshots import Snapshot as SharedSnapshot

    assert Snapshot is SharedSnapshot


def test_save_snapshot_persists_key_subject_and_tool(snapshots_dir: Path, tmp_path: Path) -> None:
    """The key, subject and tool provenance survive the trip to disk."""
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")
    tree_hash = "c" * 40
    snap = mgr.capture(
        version="0.15.0",
        branch="main",
        graph_stats_dict={
            "total_nodes": 10,
            "total_edges": 5,
            "node_counts": {"file": 6, "directory": 4},
            "edge_counts": {"CONTAINS": 5},
        },
        tree_hash=tree_hash,
        key="v0.15.0",
        subject="repo:ftree-kg",
    )
    assert snap.key == "v0.15.0"

    saved = mgr.save_snapshot(snap)
    assert saved is not None and saved.name == "v0.15.0.json"

    on_disk = json.loads(saved.read_text(encoding="utf-8"))
    assert on_disk["key"] == "v0.15.0"
    assert on_disk["subject"] == "repo:ftree-kg"
    assert on_disk["tree_hash"] == tree_hash
    assert on_disk["tool"] in {"ftree-kg", "filetreekg"}
    assert on_disk["tool_version"]

    entry = json.loads(mgr.manifest_path.read_text(encoding="utf-8"))["snapshots"][0]
    assert entry["key"] == "v0.15.0"
    assert entry["subject"] == "repo:ftree-kg"


def test_capture_without_a_key_does_not_use_the_tree_hash(snapshots_dir: Path) -> None:
    """The tree hash names a tree that is never committed, so it cannot be the key."""
    mgr = SnapshotManager(snapshots_dir)
    snap = mgr.capture(
        version="0.15.0",
        branch="main",
        graph_stats_dict={"total_nodes": 3, "total_edges": 2},
        tree_hash="d" * 40,
    )
    assert snap.key != "d" * 40
    assert snap.tree_hash == "d" * 40


# ---------------------------------------------------------------------------
# The deleted overrides: each behaviour now comes from a base extension point
#
# 0.16.0 removed capture and diff_snapshots from this module. These tests pin
# the behaviour those overrides provided, so a regression in the shared SDK
# surfaces here rather than in a shipped snapshot file.
# ---------------------------------------------------------------------------


def test_save_and_reload_persists_key_subject_and_tool(snapshots_dir: Path) -> None:
    """The round trip this repo could not have passed before 0.15.0.

    Its kgmodule-utils floor was >=0.18.0 until then, where Snapshot.key still
    returned the tree hash, so a release tag never reached disk as the key.
    """
    mgr = SnapshotManager(snapshots_dir)
    snap = mgr.capture(
        version="9.9.9",
        branch="main",
        graph_stats_dict={"total_nodes": 3, "total_edges": 2},
        tree_hash="e" * 40,
        key="v9.9.9",
        subject="repo:ftree-kg",
    )
    saved = mgr.save_snapshot(snap)
    assert saved is not None and saved.name == "v9.9.9.json"

    on_disk = json.loads(saved.read_text(encoding="utf-8"))
    assert on_disk["key"] == "v9.9.9"
    assert on_disk["subject"] == "repo:ftree-kg"
    assert on_disk["tree_hash"] == "e" * 40
    assert on_disk["tool"] in {"ftree-kg", "filetreekg"}
    assert on_disk["tool_version"]

    reloaded = mgr.load_snapshot("v9.9.9")
    assert reloaded is not None
    assert reloaded.key == "v9.9.9"
    assert reloaded.subject == "repo:ftree-kg"


def test_capture_signature_is_the_base_signature(snapshots_dir: Path) -> None:
    """The trap the _domain_metrics hook exists to close."""
    mgr = SnapshotManager(snapshots_dir)
    snap = mgr.capture(graph_stats_dict={"total_nodes": 1}, key="v1.2.3", subject="tree:/tmp")
    assert snap.key == "v1.2.3"
    assert snap.subject == "tree:/tmp"
    assert "key" not in snap.metrics
    assert "subject" not in snap.metrics


def test_domain_metrics_derives_file_and_dir_totals(snapshots_dir: Path) -> None:
    """Replaces the derivation the deleted capture() did inline."""
    mgr = SnapshotManager(snapshots_dir)
    snap = mgr.capture(
        graph_stats_dict={
            "total_nodes": 10,
            "node_counts": {"file": 7, "directory": 3},
        },
        key="k",
    )
    assert snap.metrics["total_files"] == 7
    assert snap.metrics["total_dirs"] == 3
    assert snap.metrics["dir_node_counts"] == {}


def test_diff_carries_dir_node_counts_delta(snapshots_dir: Path) -> None:
    """Replaces the deleted diff_snapshots: only changed directories appear."""
    mgr = SnapshotManager(snapshots_dir)
    for key, counts in (
        ("dl_a", {"src": 5, "same": 2, "gone": 4}),
        ("dl_b", {"src": 8, "same": 2, "new": 1}),
    ):
        mgr.save_snapshot(mgr.capture(key=key, total_nodes=1, dir_node_counts=counts), force=True)
    result = mgr.diff_snapshots("dl_a", "dl_b")
    assert result["dir_node_counts_delta"] == {"src": 3, "gone": -4, "new": 1}


def test_diff_carries_timestamp_and_issues_delta(snapshots_dir: Path) -> None:
    """Both now come from the base rather than a module override."""
    mgr = SnapshotManager(snapshots_dir)
    for key, nodes, issues in (("dl_a", 1, ["kept", "gone"]), ("dl_b", 2, ["kept", "new"])):
        mgr.save_snapshot(
            mgr.capture(graph_stats_dict={"total_nodes": nodes}, key=key, issues=issues),
            force=True,
        )
    result = mgr.diff_snapshots("dl_a", "dl_b")
    assert result["a"]["timestamp"] and result["b"]["timestamp"]
    assert result["issues_delta"] == {"introduced": ["new"], "resolved": ["gone"]}


def test_legacy_stats_dict_keyword_still_works_and_warns(snapshots_dir: Path) -> None:
    """``stats_dict`` was this repo's legacy alias for ``graph_stats_dict``.

    It was a named parameter on the capture() override removed in 0.16.0.
    Without capture_aliases the old name would be recorded as a metric called
    "stats_dict" and the graph stats would be missing entirely.
    """
    mgr = SnapshotManager(snapshots_dir)
    with pytest.warns(DeprecationWarning, match="graph_stats_dict"):
        snap = mgr.capture(key="k", stats_dict={"total_nodes": 7, "node_counts": {"file": 7}})
    assert snap.metrics["total_nodes"] == 7
    assert snap.metrics["total_files"] == 7
    assert "stats_dict" not in snap.metrics
