"""filetreekg/module.py

FileTreeKG — KGModule for filetreekg.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from kg_utils.types import KGModule, QueryResult, SnippetPack
from kg_utils.types import NodeSpec, EdgeSpec

from ftree_kg.config import load_exclude_dirs, load_include_dirs
from ftree_kg.extractor import FileTreeKGExtractor

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    node_id     TEXT PRIMARY KEY,
    kind        TEXT,
    name        TEXT,
    qualname    TEXT,
    source_path TEXT,
    docstring   TEXT
);
CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT,
    target_id TEXT,
    relation  TEXT
);
"""


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

    def build(self, wipe: bool = False) -> None:
        """Build the SQLite graph index by running the extractor.

        :param wipe: If True, delete the existing database before building.
        """
        assert self.db_path is not None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if wipe and self.db_path.exists():
            self.db_path.unlink()

        extractor = self.make_extractor()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)
            for spec in extractor.extract():
                if isinstance(spec, NodeSpec):
                    conn.execute(
                        "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?)",
                        (
                            spec.node_id,
                            spec.kind,
                            spec.name,
                            spec.qualname,
                            spec.source_path,
                            spec.docstring,
                        ),
                    )
                elif isinstance(spec, EdgeSpec):
                    conn.execute(
                        "INSERT INTO edges VALUES (?,?,?)",
                        (spec.source_id, spec.target_id, spec.relation),
                    )
            conn.commit()

    def stats(self) -> dict[str, Any]:
        """Return statistics about the knowledge graph.

        :return: Dict with total_nodes, total_edges, node_counts, edge_counts.
        """
        assert self.db_path is not None
        with sqlite3.connect(self.db_path) as conn:
            total_nodes: int = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            total_edges: int = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            node_counts: dict[str, int] = dict(
                conn.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind").fetchall()
            )
            edge_counts: dict[str, int] = dict(
                conn.execute("SELECT relation, COUNT(*) FROM edges GROUP BY relation").fetchall()
            )
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_counts": node_counts,
            "edge_counts": edge_counts,
        }

    def query(self, q: str, k: int = 8, **kwargs: Any) -> QueryResult:
        """Query the graph by text match against qualname, kind, and docstring.

        :param q: Query string.
        :param k: Maximum number of results.
        :return: QueryResult with matched node dicts.
        """
        assert self.db_path is not None
        pattern = f"%{q}%"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT node_id, kind, name, qualname, source_path, docstring
                FROM nodes
                WHERE qualname LIKE ? OR kind LIKE ? OR docstring LIKE ?
                LIMIT ?
                """,
                (pattern, pattern, pattern, k),
            ).fetchall()
        nodes = [
            {
                "node_id": r[0],
                "kind": r[1],
                "name": r[2],
                "qualname": r[3],
                "source_path": r[4],
                "docstring": r[5],
                "score": 1.0,
            }
            for r in rows
        ]
        return QueryResult(nodes=nodes, seeds=len(nodes), returned_nodes=len(nodes))

    def pack(self, q: str, **kwargs: Any) -> SnippetPack:
        """Pack metadata snippets for filesystem nodes.

        For filesystem trees, we return node metadata (size, timestamps, permissions)
        rather than file contents. The nodes are in the SnippetPack.nodes field.

        :param q: Query string.
        :param k: Number of results.
        :param max_nodes: Max nodes in pack.
        :return: SnippetPack with metadata in nodes field.
        """
        k: int = kwargs.get("k", 8)
        max_nodes: int = kwargs.get("max_nodes", 15)

        qresult = self.query(q, k=k)

        return SnippetPack(
            query=q,
            seeds=qresult.seeds,
            expanded_nodes=qresult.expanded_nodes,
            returned_nodes=qresult.returned_nodes,
            hop=qresult.hop,
            rels=qresult.rels,
            model="",
            nodes=qresult.nodes[:max_nodes],
            edges=qresult.edges,
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

    def close(self) -> None:
        """No persistent connections to release."""
