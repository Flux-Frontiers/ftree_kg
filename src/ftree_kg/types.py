"""ftree_kg/types.py

Local base types for the KGModule SDK.

These were originally imported from pycode_kg.module but are defined here
to remove the runtime dependency on pycode-kg.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Spec dataclasses
# ---------------------------------------------------------------------------


@dataclass
class NodeSpec:
    """Specification for a knowledge-graph node."""

    node_id: str
    kind: str
    name: str
    qualname: str
    source_path: str
    docstring: str = ""


@dataclass
class EdgeSpec:
    """Specification for a knowledge-graph edge."""

    source_id: str
    target_id: str
    relation: str


@dataclass
class SnippetPack:
    """Result container returned by KGModule.pack()."""

    query: str
    seeds: int = 0
    expanded_nodes: int = 0
    returned_nodes: int = 0
    hop: int = 0
    rels: list[str] = field(default_factory=list)
    model: str = ""
    nodes: list[Any] = field(default_factory=list)
    edges: list[Any] = field(default_factory=list)
    snippets: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class KGExtractor:
    """Base class for knowledge-graph extractors."""

    def __init__(self, repo_path: Path, config: dict[str, Any] | None = None) -> None:
        self.repo_path = repo_path
        self.config = config or {}

    def node_kinds(self) -> list[str]:
        raise NotImplementedError

    def edge_kinds(self) -> list[str]:
        raise NotImplementedError

    def meaningful_node_kinds(self) -> list[str]:
        return self.node_kinds()

    def coverage_metric(self, nodes: list[NodeSpec]) -> float:
        meaningful = [n for n in nodes if n.kind in self.meaningful_node_kinds()]
        if not meaningful:
            return 0.0
        covered = sum(1 for n in meaningful if n.docstring.strip())
        return covered / len(meaningful)

    def extract(self) -> Iterator[NodeSpec | EdgeSpec]:
        raise NotImplementedError


class KGModule:
    """Base class for knowledge-graph modules."""

    def __init__(
        self,
        repo_root: Path,
        db_path: Path | None = None,
        lancedb_dir: Path | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.repo_root = repo_root
        self.db_path = db_path
        self.lancedb_dir = lancedb_dir
        self.config = config or {}

    def make_extractor(self) -> KGExtractor:
        raise NotImplementedError

    def kind(self) -> str:
        raise NotImplementedError

    def build(self, wipe: bool = False) -> None:
        raise NotImplementedError

    def query(self, q: str, k: int = 8, **kwargs: Any) -> Any:
        raise NotImplementedError

    def stats(self) -> dict[str, Any]:
        raise NotImplementedError

    def pack(self, q: str, **kwargs: Any) -> Any:
        raise NotImplementedError

    def analyze(self) -> str:
        raise NotImplementedError

    def close(self) -> None:
        """Release any resources held by the module."""
