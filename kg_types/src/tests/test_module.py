"""Tests for KGModule base class."""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_types import KGModule


def test_base_raises_not_implemented() -> None:
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


def test_init_defaults() -> None:
    m = KGModule(repo_root=Path("/tmp"))
    assert m.repo_root == Path("/tmp")
    assert m.db_path is None
    assert m.lancedb_dir is None
    assert m.config == {}


def test_init_with_paths() -> None:
    m = KGModule(
        repo_root=Path("/repo"),
        db_path=Path("/db/graph.sqlite"),
        lancedb_dir=Path("/db/lancedb"),
        config={"key": "value"},
    )
    assert m.db_path == Path("/db/graph.sqlite")
    assert m.lancedb_dir == Path("/db/lancedb")
    assert m.config == {"key": "value"}
