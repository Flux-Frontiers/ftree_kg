"""Tests for kg_utils.types."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from kg_utils.types import EdgeSpec, KGExtractor, KGModule, NodeSpec, QueryResult, SnippetPack


# -- Spec dataclasses --------------------------------------------------------


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
    assert e.relation == "CALLS"


def test_queryresult_defaults() -> None:
    q = QueryResult()
    assert q.nodes == []
    assert q.seeds == 0


def test_snippetpack_defaults() -> None:
    s = SnippetPack(query="test")
    assert s.query == "test"
    assert s.nodes == []
    assert s.snippets == []


# -- KGExtractor -------------------------------------------------------------


class DummyExtractor(KGExtractor):
    def node_kinds(self) -> list[str]:
        return ["file", "directory"]

    def edge_kinds(self) -> list[str]:
        return ["CONTAINS"]

    def extract(self) -> Iterator[NodeSpec | EdgeSpec]:
        yield NodeSpec(
            node_id="file:a.txt:a.txt", kind="file", name="a.txt",
            qualname="a.txt", source_path="a.txt", docstring="A text file.",
        )
        yield NodeSpec(
            node_id="file:b.txt:b.txt", kind="file", name="b.txt",
            qualname="b.txt", source_path="b.txt",
        )
        yield EdgeSpec(source_id="directory:.:.", target_id="file:a.txt:a.txt", relation="CONTAINS")


def test_extractor_node_kinds(tmp_path: Path) -> None:
    ext = DummyExtractor(tmp_path)
    assert ext.node_kinds() == ["file", "directory"]


def test_extractor_meaningful_defaults(tmp_path: Path) -> None:
    ext = DummyExtractor(tmp_path)
    assert ext.meaningful_node_kinds() == ext.node_kinds()


def test_extractor_extract(tmp_path: Path) -> None:
    items = list(DummyExtractor(tmp_path).extract())
    nodes = [i for i in items if isinstance(i, NodeSpec)]
    edges = [i for i in items if isinstance(i, EdgeSpec)]
    assert len(nodes) == 2
    assert len(edges) == 1


def test_extractor_coverage(tmp_path: Path) -> None:
    ext = DummyExtractor(tmp_path)
    nodes = [i for i in ext.extract() if isinstance(i, NodeSpec)]
    assert ext.coverage_metric(nodes) == pytest.approx(0.5)


def test_base_extractor_raises() -> None:
    base = KGExtractor(Path("/tmp"))
    with pytest.raises(NotImplementedError):
        base.node_kinds()
    with pytest.raises(NotImplementedError):
        list(base.extract())


# -- KGModule ----------------------------------------------------------------


def test_base_module_raises() -> None:
    m = KGModule(repo_root=Path("/tmp"))
    with pytest.raises(NotImplementedError):
        m.make_extractor()
    with pytest.raises(NotImplementedError):
        m.kind()
    with pytest.raises(NotImplementedError):
        m.build()
    with pytest.raises(NotImplementedError):
        m.query("test")
    with pytest.raises(NotImplementedError):
        m.stats()
    with pytest.raises(NotImplementedError):
        m.pack("test")
    with pytest.raises(NotImplementedError):
        m.analyze()


def test_module_init_defaults() -> None:
    m = KGModule(repo_root=Path("/tmp"))
    assert m.db_path is None
    assert m.lancedb_dir is None
    assert m.config == {}
