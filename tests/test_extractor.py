"""tests/test_extractor.py

Tests for FileTreeKGExtractor.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from kg_utils.types import NodeSpec, EdgeSpec
from ftree_kg.extractor import FileTreeKGExtractor


@pytest.fixture
def extractor(tmp_path: Path) -> FileTreeKGExtractor:
    # Create a simple filesystem structure for testing
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").touch()
    (tmp_path / "dir2").mkdir()
    (tmp_path / "file2.txt").touch()
    return FileTreeKGExtractor(tmp_path)


def test_node_kinds(extractor: FileTreeKGExtractor) -> None:
    kinds = extractor.node_kinds()
    assert isinstance(kinds, list)
    assert len(kinds) > 0
    assert all(isinstance(k, str) for k in kinds)


def test_edge_kinds(extractor: FileTreeKGExtractor) -> None:
    rels = extractor.edge_kinds()
    assert isinstance(rels, list)
    assert len(rels) > 0


def test_meaningful_node_kinds_subset(extractor: FileTreeKGExtractor) -> None:
    assert set(extractor.meaningful_node_kinds()).issubset(set(extractor.node_kinds()))


def test_extract_yields_specs(extractor: FileTreeKGExtractor) -> None:
    items = list(extractor.extract())
    nodes = [i for i in items if isinstance(i, NodeSpec)]
    edges = [i for i in items if isinstance(i, EdgeSpec)]
    assert len(nodes) > 0, "extractor should yield at least one NodeSpec"
    # edges are optional depending on fixture content
    _ = edges


def test_node_ids_are_stable(extractor: FileTreeKGExtractor) -> None:
    run1 = {n.node_id for n in extractor.extract() if isinstance(n, NodeSpec)}
    run2 = {n.node_id for n in extractor.extract() if isinstance(n, NodeSpec)}
    assert run1 == run2, "node_ids must be deterministic across runs"


def test_node_id_format(extractor: FileTreeKGExtractor) -> None:
    for spec in extractor.extract():
        if isinstance(spec, NodeSpec):
            parts = spec.node_id.split(":")
            assert len(parts) >= 2, f"node_id should be '<kind>:<path>:...' got {spec.node_id!r}"
            assert spec.kind == parts[0], "node_id kind prefix must match NodeSpec.kind"


def test_coverage_metric_range(extractor: FileTreeKGExtractor) -> None:
    nodes = [n for n in extractor.extract() if isinstance(n, NodeSpec)]
    score = extractor.coverage_metric(nodes)
    assert 0.0 <= score <= 1.0
