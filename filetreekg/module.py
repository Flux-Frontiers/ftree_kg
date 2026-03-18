"""filetreekg/module.py

FileTreeKG — KGModule for filetreekg.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from code_kg.module import KGModule

from filetreekg.extractor import FileTreeKGExtractor


class FileTreeKG(KGModule):
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
        lancedb_dir = Path(lancedb_path) if lancedb_path else repo_root / ".filetreekg" / "lancedb"
        self._config = config or {}
        super().__init__(repo_root=repo_root, db_path=db_path, lancedb_dir=lancedb_dir)

    def make_extractor(self) -> FileTreeKGExtractor:
        """Return the domain extractor for this module.

        :return: FileTreeKGExtractor instance.
        """
        return FileTreeKGExtractor(self.repo_root, self._config)

    def kind(self) -> str:
        """Return the KGKind string for this module.

        :return: "meta"
        """
        return "meta"

    def _kind_priority(self, kind: str) -> int:
        """Return sort priority for file-tree node kinds (lower = ranked first).

        :param kind: Node kind string.
        :return: Integer priority.
        """
        return {"directory": 0, "module": 1, "file": 2, "symlink": 3}.get(kind, 99)

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
            for kind, count in s.get("node_counts", {}).items():
                lines.append(f"- `{kind}`: {count}")
            lines += ["", "## Edge breakdown", ""]
            for rel, count in s.get("edge_counts", {}).items():
                lines.append(f"- `{rel}`: {count}")
            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# FileTreeKG Analysis\n\nAnalysis failed: {exc}\n"
