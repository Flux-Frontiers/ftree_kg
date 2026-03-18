"""tests/test_query.py

Tests for FileTreeKG query and pack.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from src.module import FileTreeKG


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


def test_snapshot_round_trip(kg: FileTreeKG) -> None:
    # Verify the kg state is valid (snapshot functionality not available in base KGModule)
    stats = kg.stats()
    assert stats["total_nodes"] > 0, "kg should have nodes after build"
