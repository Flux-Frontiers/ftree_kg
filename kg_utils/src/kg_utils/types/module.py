"""kg_utils/types/module.py — Abstract base class for KG modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_utils.types.extractor import KGExtractor
from kg_utils.types.specs import QueryResult, SnippetPack


class KGModule:
    """Base class for knowledge-graph modules.

    Subclasses must implement :meth:`make_extractor`, :meth:`kind`,
    and should override :meth:`build`, :meth:`query`, :meth:`stats`,
    :meth:`pack`, and :meth:`analyze` with domain-specific logic.

    :param repo_root: Absolute path to the repository or corpus root.
    :param db_path: Path for the SQLite graph database.
    :param lancedb_dir: Path for the LanceDB vector index directory.
    :param config: Optional domain-specific configuration dict.
    """

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
        """Return the domain extractor for this module.

        :return: KGExtractor subclass instance.
        """
        raise NotImplementedError

    def kind(self) -> str:
        """Return the KGKind string for this module.

        :return: Kind string (e.g. "code", "meta", "doc").
        """
        raise NotImplementedError

    def build(self, wipe: bool = False) -> None:
        """Build the knowledge graph index.

        :param wipe: If True, delete existing index before building.
        """
        raise NotImplementedError

    def query(self, q: str, k: int = 8, **kwargs: Any) -> QueryResult:
        """Query the knowledge graph.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: QueryResult with matched nodes and edges.
        """
        raise NotImplementedError

    def stats(self) -> dict[str, Any]:
        """Return statistics about the knowledge graph.

        :return: Dict with keys like total_nodes, total_edges, etc.
        """
        raise NotImplementedError

    def pack(self, q: str, **kwargs: Any) -> SnippetPack:
        """Pack query results with source context.

        :param q: Natural-language query string.
        :return: SnippetPack with nodes, edges, and snippets.
        """
        raise NotImplementedError

    def analyze(self) -> str:
        """Run full analysis and return a Markdown report.

        :return: Markdown-formatted analysis report.
        """
        raise NotImplementedError
