"""kg_utils/types/extractor.py — Abstract base class for KG extractors."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from kg_utils.types.specs import EdgeSpec, NodeSpec


class KGExtractor:
    """Base class for knowledge-graph extractors.

    Subclasses must implement :meth:`node_kinds`, :meth:`edge_kinds`,
    and :meth:`extract`.

    :param repo_path: Absolute path to the repository or corpus root.
    :param config: Optional domain-specific configuration dict.
    """

    def __init__(self, repo_path: Path, config: dict[str, Any] | None = None) -> None:
        self.repo_path = repo_path
        self.config = config or {}

    def node_kinds(self) -> list[str]:
        """Return canonical node kind names.

        :return: List of node kind strings.
        """
        raise NotImplementedError

    def edge_kinds(self) -> list[str]:
        """Return canonical edge relation types.

        :return: List of edge relation strings.
        """
        raise NotImplementedError

    def meaningful_node_kinds(self) -> list[str]:
        """Return node kinds included in the vector index and coverage metrics.

        Override to exclude structural stubs from the default (all node_kinds).

        :return: Subset of node_kinds() to index semantically.
        """
        return self.node_kinds()

    def coverage_metric(self, nodes: list[NodeSpec]) -> float:
        """Compute a domain coverage quality metric.

        Default: fraction of meaningful nodes with a non-empty docstring.

        :param nodes: All extracted NodeSpec objects.
        :return: Coverage score in [0.0, 1.0].
        """
        meaningful = [n for n in nodes if n.kind in self.meaningful_node_kinds()]
        if not meaningful:
            return 0.0
        covered = sum(1 for n in meaningful if n.docstring.strip())
        return covered / len(meaningful)

    def extract(self) -> Iterator[NodeSpec | EdgeSpec]:
        """Traverse the source and yield NodeSpec / EdgeSpec objects.

        :return: Iterator of NodeSpec and EdgeSpec objects.
        """
        raise NotImplementedError
