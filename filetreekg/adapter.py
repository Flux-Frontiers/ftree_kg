"""filetreekg/adapter.py

FileTreeKGAdapter — KGAdapter shim wiring FileTreeKG into the KGRAG federation layer.
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind

from filetreekg.module import FileTreeKG


class FileTreeKGAdapter(KGAdapter):
    """KGRAG adapter for FileTreeKG.

    :param entry: KGEntry with kind=KGKind.META.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: FileTreeKG | None = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        self._kg = FileTreeKG(
            repo_root=self.entry.repo_path,
            db_path=self.entry.sqlite_path,
            lancedb_path=self.entry.lancedb_path,
        )

    def is_available(self) -> bool:
        """Return True if filetreekg is importable and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import filetreekg  # noqa: F401  # pylint: disable=import-outside-toplevel
            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query FileTreeKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects, or [] on error.
        """
        try:
            self._load()
            result = self._kg.query(q, k=k)
            return [
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.META,
                    node_id=n["node_id"],
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=n.get("score", 0.0),
                    summary=n.get("docstring", ""),
                    source_path=n.get("source_path", ""),
                )
                for n in result.nodes[:k]
            ]
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query FileTreeKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (for source-code KGs).
        :return: List of CrossSnippet objects, or [] on error.
        """
        try:
            self._load()
            pack = self._kg.pack(q, k=k, context=context)
            return [
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.META,
                    node_id=s.node_id,
                    source_path=s.source_path,
                    content=s.content,
                    score=s.score,
                    lineno=s.lineno,
                    end_lineno=s.end_lineno,
                )
                for s in pack.snippets
            ]
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this FileTreeKG instance.

        :return: Dict with at minimum a "kind" key.
        """
        try:
            self._load()
            s = self._kg.stats()
            return {
                "kind": "meta",
                "node_count": s.node_count,
                "edge_count": s.edge_count,
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "meta", "error": "stats unavailable"}

    def analyze(self) -> str:
        """Run full analysis on this FileTreeKG instance.

        :return: Markdown-formatted analysis report.
        """
        try:
            self._load()
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# FileTreeKG Analysis\n\nAnalysis failed: {exc}\n"
