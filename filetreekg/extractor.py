"""filetreekg/extractor.py

FileTreeKGExtractor — KGExtractor for filetreekg.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from code_kg.module import EdgeSpec, KGExtractor, NodeSpec


class FileTreeKGExtractor(KGExtractor):
    """Extract nodes and edges from filetreekg sources.

    :param repo_path: Absolute path to the repository or corpus root.
    :param config: Optional domain-specific configuration dict.
    """

    def __init__(self, repo_path: Path, config: dict[str, Any] | None = None) -> None:
        super().__init__(repo_path, config)

    def node_kinds(self) -> list[str]:
        """Return canonical node kind names.

        :return: ["file", "directory", "symlink", "module"]
        """
        return ["file", "directory", "symlink", "module"]

    def edge_kinds(self) -> list[str]:
        """Return canonical edge relation types.

        :return: ["CONTAINS", "CHILD_OF", "PARENT_OF"]
        """
        return ["CONTAINS", "CHILD_OF", "PARENT_OF"]

    def meaningful_node_kinds(self) -> list[str]:
        """Return node kinds included in the vector index and coverage metrics.

        Override to exclude structural stubs from the default (all node_kinds).

        :return: Subset of node_kinds() to index semantically.
        """
        return self.node_kinds()

    def coverage_metric(self, nodes: list[NodeSpec]) -> float:
        """Compute a domain coverage quality metric for snapshots.

        Default: fraction of meaningful nodes with a non-empty docstring.
        Override with a domain-appropriate signal.

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

        node_id format: '<kind>:<source_path>:<qualname>'

        :return: Iterator of NodeSpec and EdgeSpec objects.
        """
        # Walk the filesystem tree starting from repo_path
        for path in self.repo_path.rglob("*"):
            rel_path = path.relative_to(self.repo_path)

            # Determine node kind
            if path.is_symlink():
                kind = "symlink"
            elif path.is_dir():
                kind = "directory"
            else:
                kind = "file"

            # Create node
            yield NodeSpec(
                node_id=f"{kind}:{rel_path}:{rel_path.name}",
                kind=kind,
                name=path.name,
                qualname=str(rel_path),
                source_path=str(rel_path),
                docstring="",
            )

            # Create CONTAINS edge from parent directory
            if path.parent != self.repo_path:
                parent_rel = path.parent.relative_to(self.repo_path)
                yield EdgeSpec(
                    source_id=f"directory:{parent_rel}:{path.parent.name}",
                    target_id=f"{kind}:{rel_path}:{rel_path.name}",
                    relation="CONTAINS",
                )
            elif kind != "directory" or path.parent == self.repo_path:
                # Root level items contained by repo root
                if path != self.repo_path:
                    yield EdgeSpec(
                        source_id=f"directory:.:",
                        target_id=f"{kind}:{rel_path}:{rel_path.name}",
                        relation="CONTAINS",
                    )
