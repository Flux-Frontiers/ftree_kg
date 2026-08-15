"""tests/test_mcp_server.py

Tests for the FTreeKG MCP server tool surface.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("mcp", reason="mcp required for MCP server tests")
pytest.importorskip("kg_utils", reason="kg_utils required for integration tests")

import ftree_kg.mcp_server as mcp_server  # noqa: E402
from ftree_kg.module import FileTreeKG  # noqa: E402


@pytest.fixture
def served_kg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FileTreeKG:
    """Install a built FileTreeKG as the server's module-level instance.

    Uses the lexical query path (no embedding pass) so the tests stay fast.
    """
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()

    instance = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / ".filetreekg" / "graph.sqlite",
        vectors_path=tmp_path / ".filetreekg" / "vectors.sqlite",
    )
    instance.build(wipe=True, embed=False)
    monkeypatch.setattr(mcp_server, "_kg", instance)
    return instance


def test_get_kg_raises_when_uninitialised(monkeypatch: pytest.MonkeyPatch) -> None:
    """_get_kg() must fail loudly rather than return None."""
    monkeypatch.setattr(mcp_server, "_kg", None)
    with pytest.raises(RuntimeError, match="not initialised"):
        mcp_server._get_kg()


def test_graph_stats_returns_json(served_kg: FileTreeKG) -> None:
    """graph_stats() emits parseable JSON carrying node/edge totals."""
    stats = json.loads(mcp_server.graph_stats())
    assert stats["total_nodes"] > 0
    assert "node_counts" in stats
    assert "total_size_bytes" in stats


def test_query_tree_returns_json_nodes(served_kg: FileTreeKG) -> None:
    """query_tree() emits a QueryResult whose nodes carry both id spellings."""
    result = json.loads(mcp_server.query_tree("file", k=5))
    assert result["nodes"], "expected at least one match for 'file'"
    node = result["nodes"][0]
    # ``id`` is the kg_utils contract; ``node_id`` is the FTreeKG spelling.
    assert node["id"] == node["node_id"]


def test_pack_tree_renders_markdown(served_kg: FileTreeKG) -> None:
    """pack_tree() renders Markdown — regression for the missing ``id`` key.

    SnippetPack.to_markdown() reads ``n['id']``; FTreeKG previously emitted only
    ``node_id``, so this path raised KeyError.
    """
    md = mcp_server.pack_tree("file", k=3, max_nodes=3)
    assert "## Nodes" in md
    assert "- id: `" in md


def test_analyze_tree_returns_report(served_kg: FileTreeKG) -> None:
    """analyze_tree() returns the Markdown analysis report."""
    report = mcp_server.analyze_tree()
    assert report.startswith("# FileTreeKG Analysis")


def test_parse_args_defaults() -> None:
    """Default paths mirror the CLI's .filetreekg layout."""
    args = mcp_server._parse_args(["--repo", "."])
    assert args.repo == "."
    assert args.db == ".filetreekg/graph.sqlite"
    assert args.transport == "stdio"
    assert args.vectors is None
