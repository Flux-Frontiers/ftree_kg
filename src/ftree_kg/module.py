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
DROP TABLE IF EXISTS nodes;
DROP TABLE IF EXISTS edges;
CREATE TABLE nodes (
    node_id     TEXT PRIMARY KEY,
    kind        TEXT,
    name        TEXT,
    qualname    TEXT,
    source_path TEXT,
    docstring   TEXT,
    size_bytes  INTEGER DEFAULT 0
);
CREATE TABLE edges (
    source_id TEXT,
    target_id TEXT,
    relation  TEXT
);
"""


def _ascii_tree(
    rows: list[tuple[str, str]],
    max_depth: int = 3,
    max_children: int = 12,
) -> list[str]:
    """Render an ASCII tree from (source_path, kind) rows.

    :param rows: List of (source_path, kind) tuples from the nodes table.
    :param max_depth: Maximum directory depth to display.
    :param max_children: Max children shown per directory before truncating.
    :return: Lines of the ASCII tree (no trailing newlines).
    """
    # Build a nested dict tree: {name: {"_kind": kind, "_children": {...}}}
    root: dict[str, dict[str, Any]] = {}
    for source_path, kind in sorted(rows):
        parts = Path(source_path).parts
        if len(parts) > max_depth:
            continue
        node = root
        for part in parts[:-1]:
            node = node.setdefault(part, {}).setdefault("_children", {})
        leaf = parts[-1]
        entry = node.setdefault(leaf, {})
        entry["_kind"] = kind

    lines: list[str] = []

    def render(tree: dict[str, dict[str, Any]], prefix: str) -> None:
        items = [(k, v) for k, v in sorted(tree.items()) if not k.startswith("_")]
        truncated = len(items) > max_children
        if truncated:
            items = items[:max_children]
        for idx, (name, subtree) in enumerate(items):
            is_last = idx == len(items) - 1 and not truncated
            connector = "└── " if is_last else "├── "
            kind = subtree.get("_kind", "directory")
            suffix = "/" if kind == "directory" else ""
            lines.append(f"{prefix}{connector}{name}{suffix}")
            children = subtree.get("_children", {})
            if children:
                extension = "    " if is_last else "│   "
                render(children, prefix + extension)
        if truncated:
            lines.append(f"{prefix}└── … ({len(tree) - max_children} more)")

    render(root, "")
    return lines


def _fmt_size(n: int) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n //= 1024
    return f"{n:.1f} TB"


def _size_bar(value: int, total: int, width: int = 20) -> str:
    """ASCII bar proportional to value/total."""
    filled = int(width * value / total) if total else 0
    return "█" * filled + "░" * (width - filled)


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

    def build(self, wipe: bool = True) -> None:
        """Build the SQLite graph index by running the extractor.

        Pass 1 — extract nodes/edges from the filesystem.
        Pass 2 — re-stat each file node to populate size_bytes.

        :param wipe: If True, delete the existing database before building.
        """
        assert self.db_path is not None
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if wipe and self.db_path.exists():
            self.db_path.unlink()

        extractor = self.make_extractor()

        # Pass 1: extract nodes and edges
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(_SCHEMA)
            for spec in extractor.extract():
                if isinstance(spec, NodeSpec):
                    conn.execute(
                        "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,0)",
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

        # Pass 2: populate size_bytes for file nodes
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT node_id, source_path FROM nodes WHERE kind = 'file'"
            ).fetchall()
            updates = []
            for node_id, source_path in rows:
                full_path = self.repo_root / source_path
                try:
                    size = full_path.stat().st_size
                except OSError:
                    size = 0
                updates.append((size, node_id))
            conn.executemany("UPDATE nodes SET size_bytes = ? WHERE node_id = ?", updates)
            conn.commit()

    def stats(self) -> dict[str, Any]:
        """Return statistics about the knowledge graph.

        :return: Dict with total_nodes, total_edges, node_counts, edge_counts,
                 total_size_bytes, size_by_top_dir.
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
            total_size: int = conn.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM nodes WHERE kind = 'file'"
            ).fetchone()[0]
            # Size by top-level directory
            rows = conn.execute(
                "SELECT source_path, size_bytes FROM nodes WHERE kind = 'file'"
            ).fetchall()

        size_by_dir: dict[str, int] = {}
        for source_path, size in rows:
            parts = Path(source_path).parts
            top = parts[0] if len(parts) > 1 else "."
            size_by_dir[top] = size_by_dir.get(top, 0) + size

        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_counts": node_counts,
            "edge_counts": edge_counts,
            "total_size_bytes": total_size,
            "size_by_top_dir": dict(sorted(size_by_dir.items(), key=lambda x: x[1], reverse=True)),
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
            total_size = s.get("total_size_bytes", 0)
            size_by_dir: dict[str, int] = s.get("size_by_top_dir", {})
            node_counts: dict[str, int] = s.get("node_counts", {})
            edge_counts: dict[str, int] = s.get("edge_counts", {})

            assert self.db_path is not None
            with sqlite3.connect(self.db_path) as conn:
                tree_rows: list[tuple[str, str]] = conn.execute(
                    "SELECT source_path, kind FROM nodes ORDER BY source_path"
                ).fetchall()

            lines = [
                "# FileTreeKG Analysis",
                "",
                "## Summary",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Total paths | {s['total_nodes']:,} |",
                f"| Total links | {s['total_edges']:,} |",
                f"| Files | {node_counts.get('file', 0):,} |",
                f"| Directories | {node_counts.get('directory', 0):,} |",
                f"| Symlinks | {node_counts.get('symlink', 0):,} |",
                f"| Total size (files) | {_fmt_size(total_size)} |",
                "",
                "## Size by top-level directory",
                "",
            ]

            if size_by_dir:
                max_size = max(size_by_dir.values()) or 1
                lines.append("```")
                for top_dir, size in size_by_dir.items():
                    size_bar = _size_bar(size, max_size)
                    lines.append(f"{top_dir:<20} {size_bar}  {_fmt_size(size):>10}")
                lines.append("```")
            else:
                lines.append("_No file size data available._")

            tree_lines = _ascii_tree(tree_rows)
            if tree_lines:
                lines += ["", "## Directory tree (depth ≤ 3)", "", "```"]
                lines.extend(tree_lines)
                lines.append("```")

            lines += [
                "",
                "## Path breakdown",
                "",
                "| Kind | Count |",
                "|------|-------|",
            ]
            for kind, count in sorted(node_counts.items()):
                lines.append(f"| `{kind}` | {count:,} |")

            lines += [
                "",
                "## Link breakdown",
                "",
                "| Relation | Count |",
                "|----------|-------|",
            ]
            for rel, count in sorted(edge_counts.items()):
                lines.append(f"| `{rel}` | {count:,} |")

            return "\n".join(lines)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# FileTreeKG Analysis\n\nAnalysis failed: {exc}\n"

    def close(self) -> None:
        """No persistent connections to release."""
