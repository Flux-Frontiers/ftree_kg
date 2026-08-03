"""filetreekg/adapter.py

FileTreeKGAdapter — KGAdapter shim wiring FileTreeKG into the KGRAG federation layer.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-07-28 08:58:00
License: Elastic 2.0
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import (
    CrossHit,
    CrossSnippet,
    KGEntry,
    KGKind,
    QueryScope,
)

from ftree_kg.module import FileTreeKG


class FileTreeKGAdapter(KGAdapter):  # type: ignore[misc]
    """KGRAG adapter for FileTreeKG.

    :param entry: KGEntry with kind=KGKind.FILETREE.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: FileTreeKG | None = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        # ``vectors_path`` may be None on registry entries written before the
        # sqlite-vec migration; FileTreeKG then derives its own default.
        self._kg = FileTreeKG(
            repo_root=self.entry.repo_path,
            db_path=self.entry.sqlite_path,
            vectors_path=getattr(self.entry, "vectors_path", None),
        )

    def is_available(self) -> bool:
        """Return True if filetreekg is importable and the DB is built.

        :return: True if this adapter can serve queries.
        """
        return bool(self.entry.is_built)

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossHit]:
        """Query FileTreeKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit scores below this, the whole
            result set is discarded rather than returning k noisy
            near-neighbour hits from a KG with nothing relevant to say.
        :param scope: Optional retrieval scope. FileTreeKG cannot push this
            into its backend, so it is accepted and ignored — the orchestrator
            post-filters, as :class:`~kg_rag.adapters.base.KGAdapter` permits
            for adapters that do not set ``supports_scope``.
        :return: List of CrossHit objects, or [] on error.
        """
        try:
            self._load()
            assert self._kg is not None
            result = self._kg.query(q, k=k)
            nodes = result.nodes[:k]
            if semantic_floor > 0.0 and nodes:
                if nodes[0].get("score", 0.0) < semantic_floor:
                    return []
            nodes = [n for n in nodes if n.get("score", 0.0) >= min_score]
            return [
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.FILETREE,
                    node_id=n["node_id"],
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=n.get("score", 0.0),
                    summary=n.get("docstring", ""),
                    source_path=n.get("source_path", ""),
                )
                for n in nodes
            ]
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def pack(
        self,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossSnippet]:
        """Query FileTreeKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (for source-code KGs).
        :param semantic_floor: If the best snippet scores below this, the whole
            result set is discarded. Mirrors the same parameter on
            :meth:`query`.
        :param scope: Optional retrieval scope, accepted and ignored — see
            :meth:`query`.
        :return: List of CrossSnippet objects, or [] on error.
        """
        try:
            self._load()
            assert self._kg is not None
            pack = self._kg.pack(q, k=k, context=context)
            # FileTreeKG.pack() fills SnippetPack.snippets with plain dicts
            # (node_id / source_path / content / score / kind / name), not
            # objects. This previously used attribute access, which raised
            # AttributeError on the first snippet and was swallowed by the
            # except below — so pack() silently returned [] every single time.
            # There are no line numbers: filesystem nodes are not source spans,
            # so lineno/end_lineno stay None.
            if semantic_floor > 0.0 and pack.snippets:
                if pack.snippets[0].get("score", 0.0) < semantic_floor:
                    return []
            return [
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.FILETREE,
                    node_id=s["node_id"],
                    source_path=s.get("source_path", ""),
                    content=s.get("content", ""),
                    score=s.get("score", 0.0),
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
            assert self._kg is not None
            s = self._kg.stats()
            return {
                "kind": "filetree",
                "node_count": s.get("total_nodes", 0),
                "edge_count": s.get("total_edges", 0),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "filetree", "error": "stats unavailable"}

    def analyze(self) -> str:
        """Run full analysis on this FileTreeKG instance.

        :return: Markdown-formatted analysis report.
        """
        try:
            self._load()
            assert self._kg is not None
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# FileTreeKG Analysis\n\nAnalysis failed: {exc}\n"
