"""Tests for KGExtractor base class."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from kg_types import KGExtractor, NodeSpec, EdgeSpec


class DummyExtractor(KGExtractor):
    """Minimal concrete extractor for testing."""

    def node_kinds(self) -> list[str]:
        return ["file", "directory"]

    def edge_kinds(self) -> list[str]:
        return ["CONTAINS"]

    def extract(self) -> Iterator[NodeSpec | EdgeSpec]:
        yield NodeSpec(
            node_id="file:a.txt:a.txt",
            kind="file",
            name="a.txt",
            qualname="a.txt",
            source_path="a.txt",
            docstring="A text file.",
        )
        yield NodeSpec(
            node_id="file:b.txt:b.txt",
            kind="file",
            name="b.txt",
            qualname="b.txt",
            source_path="b.txt",
        )
        yield EdgeSpec(
            source_id="directory:.:.",
            target_id="file:a.txt:a.txt",
            relation="CONTAINS",
        )


@pytest.fixture
def extractor(tmp_path: Path) -> DummyExtractor:
    return DummyExtractor(tmp_path)


def test_node_kinds(extractor: DummyExtractor) -> None:
    assert extractor.node_kinds() == ["file", "directory"]


def test_edge_kinds(extractor: DummyExtractor) -> None:
    assert extractor.edge_kinds() == ["CONTAINS"]


def test_meaningful_defaults_to_all(extractor: DummyExtractor) -> None:
    assert extractor.meaningful_node_kinds() == extractor.node_kinds()


def test_extract_yields_specs(extractor: DummyExtractor) -> None:
    items = list(extractor.extract())
    nodes = [i for i in items if isinstance(i, NodeSpec)]
    edges = [i for i in items if isinstance(i, EdgeSpec)]
    assert len(nodes) == 2
    assert len(edges) == 1


def test_coverage_metric(extractor: DummyExtractor) -> None:
    nodes = [i for i in extractor.extract() if isinstance(i, NodeSpec)]
    score = extractor.coverage_metric(nodes)
    # 1 of 2 nodes has a docstring
    assert score == pytest.approx(0.5)


def test_base_extract_raises() -> None:
    base = KGExtractor(Path("/tmp"))
    with pytest.raises(NotImplementedError):
        list(base.extract())


def test_base_node_kinds_raises() -> None:
    base = KGExtractor(Path("/tmp"))
    with pytest.raises(NotImplementedError):
        base.node_kinds()
