"""Tests for kg_types spec dataclasses."""

from __future__ import annotations

from kg_types.specs import EdgeSpec, NodeSpec, QueryResult, SnippetPack


def test_nodespec_defaults() -> None:
    n = NodeSpec(
        node_id="file:src/main.py:main.py",
        kind="file",
        name="main.py",
        qualname="src/main.py",
        source_path="src/main.py",
    )
    assert n.docstring == ""
    assert n.node_id == "file:src/main.py:main.py"


def test_nodespec_with_docstring() -> None:
    n = NodeSpec(
        node_id="func:src/main.py:main",
        kind="function",
        name="main",
        qualname="src/main.py:main",
        source_path="src/main.py",
        docstring="Entry point.",
    )
    assert n.docstring == "Entry point."


def test_edgespec() -> None:
    e = EdgeSpec(source_id="a", target_id="b", relation="CALLS")
    assert e.source_id == "a"
    assert e.target_id == "b"
    assert e.relation == "CALLS"


def test_queryresult_defaults() -> None:
    q = QueryResult()
    assert q.nodes == []
    assert q.edges == []
    assert q.seeds == 0


def test_snippetpack_defaults() -> None:
    s = SnippetPack(query="test")
    assert s.query == "test"
    assert s.nodes == []
    assert s.snippets == []
