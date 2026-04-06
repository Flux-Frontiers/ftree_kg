"""tests/test_query.py

Tests for FileTreeKG query and pack.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from typing import cast

pycode_kg = pytest.importorskip("pycode_kg", reason="pycode_kg required for integration tests")

from ftree_kg.module import FileTreeKG  # noqa: E402
from ftree_kg.snapshots import SnapshotMetrics  # noqa: E402


@pytest.fixture
def kg(tmp_path: Path) -> FileTreeKG:
    # Create a simple filesystem structure for testing
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").touch()
    (tmp_path / "dir2").mkdir()
    (tmp_path / "file2.txt").touch()

    instance = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / ".filetreekg" / "graph.sqlite",
        lancedb_path=tmp_path / ".filetreekg" / "lancedb",
    )
    instance.build(wipe=True)
    return instance


def test_build_produces_nodes(kg: FileTreeKG) -> None:
    s = kg.stats()
    assert s["total_nodes"] > 0, "build should produce at least one node"


def test_query_returns_results(kg: FileTreeKG) -> None:
    # Use a term likely to match something in the fixture corpus
    result = kg.query("directory", k=5)
    assert result is not None
    assert isinstance(result.nodes, list)


def test_query_scores_in_range(kg: FileTreeKG) -> None:
    result = kg.query("directory", k=5)
    for node in result.nodes:
        assert 0.0 <= node.get("score", 0.0) <= 1.0


def test_pack_returns_snippets(kg: FileTreeKG) -> None:
    pack = kg.pack("file", k=3)
    assert pack is not None
    assert isinstance(pack.nodes, list) or isinstance(pack.warnings, list)


def test_pack_snippets_have_content(kg: FileTreeKG) -> None:
    pack = kg.pack("file", k=3)
    for node in pack.nodes:
        assert node.get("docstring") or node.get("qualname"), "each node should have metadata"
        assert node.get("id") or node.get("node_id"), "each node must have an id"


def test_analyze_returns_markdown(kg: FileTreeKG) -> None:
    report = kg.analyze()
    assert report.startswith("#"), "analyze() must return Markdown starting with a heading"
    assert "FileTreeKG" in report or "Analysis" in report


def test_snapshot_round_trip(kg: FileTreeKG, tmp_path: Path) -> None:
    pytest.importorskip("kg_rag.snapshots")
    from ftree_kg.snapshots import SnapshotManager

    snapshots_dir = tmp_path / ".filetreekg" / "snapshots"
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")

    stats = kg.stats()
    snap = mgr.capture(version="0.0.0-test", branch="test", stats_dict=stats)
    saved = mgr.save_snapshot(snap)

    assert saved is not None and saved.exists(), "snapshot file must be written"
    m = cast(SnapshotMetrics, snap.metrics)
    assert m.total_nodes > 0
    assert m.total_files >= 0
    assert m.total_dirs >= 0
    assert snap.key != "", "snapshot must have a tree hash key"

    # Round-trip: load back and verify
    loaded = mgr.load_snapshot(snap.key)
    assert loaded is not None
    lm = cast(SnapshotMetrics, loaded.metrics)
    assert lm.total_nodes == m.total_nodes
    assert lm.total_edges == m.total_edges

    # 'latest' convenience key works
    latest = mgr.load_snapshot("latest")
    assert latest is not None
    assert latest.key == snap.key


def test_snapshot_list(kg: FileTreeKG, tmp_path: Path) -> None:
    pytest.importorskip("kg_rag.snapshots")
    from ftree_kg.snapshots import SnapshotManager

    snapshots_dir = tmp_path / ".filetreekg" / "snapshots"
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")

    stats = kg.stats()
    snap = mgr.capture(version="0.0.0-test", branch="test", stats_dict=stats)
    mgr.save_snapshot(snap)

    snaps = mgr.list_snapshots()
    assert len(snaps) == 1
    assert snaps[0]["key"] == snap.key


def test_snapshot_diff(kg: FileTreeKG, tmp_path: Path) -> None:
    pytest.importorskip("kg_rag.snapshots")
    from ftree_kg.snapshots import SnapshotManager

    snapshots_dir = tmp_path / ".filetreekg" / "snapshots"
    mgr = SnapshotManager(snapshots_dir, db_path=tmp_path / ".filetreekg" / "graph.sqlite")

    stats = kg.stats()
    snap_a = mgr.capture(version="0.0.0-a", branch="test", stats_dict=stats, tree_hash="aaaa")
    snap_b = mgr.capture(version="0.0.0-b", branch="test", stats_dict=stats, tree_hash="bbbb")
    mgr.save_snapshot(snap_a)
    mgr.save_snapshot(snap_b)

    result = mgr.diff_snapshots("aaaa", "bbbb")
    assert "error" not in result
    assert result["delta"]["nodes"] == 0  # same stats → zero delta
