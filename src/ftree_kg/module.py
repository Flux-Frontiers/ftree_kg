"""filetreekg/module.py

FileTreeKG — KGModule for filetreekg.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pycode_kg.module import KGModule

from ftree_kg.config import load_exclude_dirs, load_include_dirs
from ftree_kg.extractor import FileTreeKGExtractor


class FileTreeKG(KGModule):  # type: ignore[misc]
    """Knowledge graph module for filetreekg.

    Provides build, query, pack, analyze, and snapshot operations
    over filetreekg sources using the KGModule infrastructure.

    :param repo_root: Absolute path to the repository or corpus root.
    :param db_path: Path for the SQLite graph database.
    :param lancedb_path: Path for the LanceDB vector index directory.
    :param config: Optional domain-specific configuration dict.
    """

    def __init__(
        self,
        repo_root: Path | str,
        db_path: Path | str | None = None,
        lancedb_path: Path | str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        repo_root = Path(repo_root).resolve()
        db_path = Path(db_path) if db_path else repo_root / ".filetreekg" / "graph.sqlite"
        lancedb_path = Path(lancedb_path) if lancedb_path else repo_root / ".filetreekg" / "lancedb"
        super().__init__(repo_root=repo_root, db_path=db_path, lancedb_dir=lancedb_path)
        self.config = config or {}

    def make_extractor(self) -> FileTreeKGExtractor:
        """Return the domain extractor for this module.

        Loads include/exclude directories from [tool.filetreekg] in pyproject.toml.

        :return: FileTreeKGExtractor instance.
        """
        return FileTreeKGExtractor(
            self.repo_root,
            self.config,
            include_dirs=load_include_dirs(self.repo_root),
            exclude_dirs=load_exclude_dirs(self.repo_root),
        )

    def kind(self) -> str:
        """Return the KGKind string for this module.

        :return: "meta"
        """
        return "meta"

    def pack(
        self,
        q: str,
        k: int = 8,
        hop: int = 0,
        rels: str = "",
        include_symbols: bool = False,
        context: int = 5,
        max_lines: int = 60,
        max_nodes: int = 15,
        min_score: float = 0.0,
        max_per_module: int = 0,
        missing_lineno_policy: str = "cap_or_skip",
        include_edge_provenance: bool = False,
    ) -> Any:
        """Pack metadata snippets for filesystem nodes.

        For filesystem trees, we return node metadata (size, timestamps, permissions)
        rather than file contents. The nodes are in the SnippetPack.nodes field.

        :param q: Query string.
        :param k: Number of results.
        :param max_nodes: Max nodes in pack.
        :return: SnippetPack with metadata in nodes field.
        """
        from pycode_kg.module.types import SnippetPack

        qresult = self.query(q, k=k)

        return SnippetPack(
            query=q,
            seeds=qresult.seeds if hasattr(qresult, "seeds") else 0,
            expanded_nodes=qresult.expanded_nodes if hasattr(qresult, "expanded_nodes") else 0,
            returned_nodes=qresult.returned_nodes if hasattr(qresult, "returned_nodes") else 0,
            hop=qresult.hop if hasattr(qresult, "hop") else 0,
            rels=qresult.rels if hasattr(qresult, "rels") else [],
            model="",
            nodes=qresult.nodes[:max_nodes],
            edges=qresult.edges if hasattr(qresult, "edges") else [],
        )

    def analyze(self) -> str:
        """Run full analysis and return a Markdown report.

        :return: Markdown-formatted analysis report.
        """
        try:
            s = self.stats()
            lines = [
                "# FileTreeKG Analysis",
                "",
                f"**Nodes:** {s['total_nodes']}  ",
                f"**Edges:** {s['total_edges']}  ",
                "",
                "## Node breakdown",
                "",
            ]
            for kind, count in (s.get("node_counts") or {}).items():
                lines.append(f"- `{kind}`: {count}")
            lines += ["", "## Edge breakdown", ""]
            for rel, count in (s.get("edge_counts") or {}).items():
                lines.append(f"- `{rel}`: {count}")
            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# FileTreeKG Analysis\n\nAnalysis failed: {exc}\n"
