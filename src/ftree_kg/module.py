"""filetreekg/module.py

FileTreeKG — KGModule for filetreekg.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from kg_utils.types import EdgeSpec, KGModule, NodeSpec, QueryResult, SnippetPack

from ftree_kg.config import load_exclude_dirs, load_include_dirs
from ftree_kg.extractor import FileTreeKGExtractor
from ftree_kg.metadata import extract_metadata, metadata_keywords, metadata_prose

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
    size_bytes  INTEGER DEFAULT 0,
    metadata    TEXT
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


def _embed_text(row: tuple[Any, ...]) -> str:
    """Build the canonical text document used to embed a filesystem node.

    A file tree's semantic axes are intentionally narrow: a node is identified
    by its **kind** (file / directory / symlink), its **basename** (with
    extension), the **path components** that lead to it, and the **extension**
    itself.  There is no docstring, no qualname, no module — those concepts
    belong to source code, not filesystem entries.

    The text is two lines:

    * a one-sentence locator (``"{kind} {basename} at {source_path}"``)
    * a flat keyword line containing the path components, the basename split
      on ``_``/``-``/``.``, and the extension as its own token

    For ``src/ftree_kg/cli/cmd_build.py`` this produces::

        file cmd_build.py at src/ftree_kg/cli/cmd_build.py
        keywords: src ftree_kg cli cmd_build cmd build py

    making ``"build script"``, ``"CLI"``, ``"py"``, and ``"cmd_build"`` all
    plausible matches against the same vector.

    When the row carries per-format metadata (EXIF for images, etc.), prose
    tokens projected from that metadata (camera make/model, capture year, GPS
    coordinates, description) are appended to the keyword line so a query
    like ``"iPhone photos from 2023"`` can hit a vacation snapshot whose path
    says nothing about either.

    :param row: SQLite row ``(node_id, kind, name, qualname, source_path,
                docstring, size_bytes, metadata)`` — only ``kind``, ``name``,
                ``source_path``, and ``metadata`` are used.
    :return: Canonical text document.
    """
    _node_id, kind, name, _qualname, source_path, _docstring, _size, metadata = row
    src = source_path or ""
    parts = [p for p in Path(src).parts if p and p != "."]

    # Basename split: drop the extension, keep the stem itself, then split it
    # on _/-/. so both literal ("cmd_build") and tokenised ("cmd", "build")
    # forms are reachable from the same vector.
    basename = name or (parts[-1] if parts else "")
    stem, _dot, ext = basename.rpartition(".")
    stem = stem or basename
    base_tokens = [t for t in re.split(r"[._\-]+", stem) if t]

    meta_dict: dict[str, Any] | None = None
    if metadata:
        try:
            meta_dict = json.loads(metadata)
        except (TypeError, ValueError):
            meta_dict = None
    meta_tokens = metadata_keywords(meta_dict)

    keywords = " ".join(
        dict.fromkeys([*parts, stem, *base_tokens, *([ext] if ext else []), *meta_tokens])
    )
    return f"{kind} {basename} at {src}\nkeywords: {keywords}"


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

    def build(self, wipe: bool = True, embed: bool = True, metadata: bool = True) -> None:
        """Build the SQLite graph index and (optionally) the LanceDB vector index.

        Pass 1   — extract nodes/edges from the filesystem.
        Pass 2   — re-stat each file node to populate ``size_bytes``.
        Pass 2.5 — extract per-format metadata (EXIF, etc.) into the
                   ``metadata`` column when ``metadata=True``.
        Pass 3   — embed each node's canonical text and write to LanceDB
                   when ``embed=True`` and ``kg_utils.embedder`` is available.

        :param wipe: If True, delete the existing database before building.
        :param embed: If True, populate the LanceDB vector index after Pass 2.5.
        :param metadata: If True, extract per-format metadata (image EXIF, etc.)
            for each file node.  Cheap — the dispatcher returns immediately
            for files outside the supported extension set.
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
                        "INSERT OR REPLACE INTO nodes "
                        "(node_id, kind, name, qualname, source_path, docstring,"
                        " size_bytes, metadata) "
                        "VALUES (?,?,?,?,?,?,0,NULL)",
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

        # Pass 2.5: extract per-format metadata (EXIF for images, etc.)
        if metadata:
            self._extract_node_metadata()

        # Pass 3: embed nodes into LanceDB
        if embed:
            self._embed_nodes(wipe=wipe)

    def _extract_node_metadata(self) -> None:
        """Walk every file node, run :func:`extract_metadata`, persist as JSON.

        Directories and symlinks are skipped (no per-format metadata applies).
        Failures on individual files are silently swallowed — a single bad
        image must not abort the build.
        """
        assert self.db_path is not None
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT node_id, source_path FROM nodes WHERE kind = 'file'"
            ).fetchall()
            updates: list[tuple[str | None, str]] = []
            for node_id, source_path in rows:
                full_path = self.repo_root / source_path
                try:
                    meta = extract_metadata(full_path)
                except Exception:  # pylint: disable=broad-exception-caught
                    meta = None
                blob = json.dumps(meta) if meta else None
                updates.append((blob, node_id))
            conn.executemany("UPDATE nodes SET metadata = ? WHERE node_id = ?", updates)
            conn.commit()

    def _embed_nodes(self, wipe: bool = True) -> None:
        """Embed every node into LanceDB at ``self.lancedb_dir / kg_nodes.lance``.

        Builds a canonical text document per node (kind, name, qualname, source
        path, docstring, keywords derived from path components), embeds it via
        :func:`kg_utils.embedder.get_embedder`, and writes ``(id, kind, name,
        qualname, module_path, text, vector)`` rows to a LanceDB table named
        ``kg_nodes``.

        Silently no-ops (and prints a brief warning to stderr) when LanceDB or
        the sentence-transformer embedder is unavailable, so a missing model
        cache or a CI runner without ``sentence-transformers`` does not break
        the build.

        :param wipe: If True, drop and recreate the table; if False, append.
        """
        if self.lancedb_dir is None:
            return
        try:
            import lancedb  # pylint: disable=import-outside-toplevel
            from kg_utils.embedder import get_embedder  # pylint: disable=import-outside-toplevel
        except ImportError as exc:  # pragma: no cover
            import sys  # pylint: disable=import-outside-toplevel

            print(
                f"[FileTreeKG] embedding pass skipped — {exc}",
                file=sys.stderr,
            )
            return

        assert self.db_path is not None
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT node_id, kind, name, qualname, source_path, docstring,"
                " size_bytes, metadata FROM nodes"
            ).fetchall()
        if not rows:
            return

        try:
            embedder = get_embedder()
        except Exception as exc:  # pylint: disable=broad-exception-caught # pragma: no cover
            import sys  # pylint: disable=import-outside-toplevel

            print(
                f"[FileTreeKG] embedding pass skipped — embedder load failed: {exc}",
                file=sys.stderr,
            )
            return

        texts = [_embed_text(r) for r in rows]
        vectors = embedder.embed_texts(texts)

        records: list[dict[str, Any]] = []
        for (
            (
                node_id,
                kind,
                name,
                qualname,
                source_path,
                _docstring,
                _size,
                _metadata,
            ),
            text,
            vec,
        ) in zip(rows, texts, vectors, strict=True):
            records.append(
                {
                    "id": node_id,
                    "kind": kind,
                    "name": name,
                    "qualname": qualname,
                    "module_path": source_path,
                    "text": text,
                    "vector": vec,
                }
            )

        self.lancedb_dir.mkdir(parents=True, exist_ok=True)
        db = lancedb.connect(str(self.lancedb_dir))
        if "kg_nodes" in db.list_tables().tables:
            if wipe:
                db.drop_table("kg_nodes")
                db.create_table("kg_nodes", data=records)
            else:
                db.open_table("kg_nodes").add(records)
        else:
            db.create_table("kg_nodes", data=records)

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
        """Semantic query against the LanceDB vector index, with LIKE fallback.

        Vector-seeds via the kg_utils embedder against ``kg_nodes.lance`` and
        ranks by cosine distance.  When the LanceDB table is missing or empty
        (e.g. embeddings not yet built), falls back to a substring LIKE match
        against ``qualname``, ``kind``, and ``docstring`` so the method always
        returns something useful.

        :param q: Query string.
        :param k: Maximum number of results.
        :return: QueryResult with matched node dicts ranked by score.
        """
        nodes = self._semantic_query(q, k)
        if not nodes:
            nodes = self._lexical_query(q, k)
        return QueryResult(nodes=nodes, seeds=len(nodes), returned_nodes=len(nodes))

    def _semantic_query(self, q: str, k: int) -> list[dict[str, Any]]:
        """Vector search over the LanceDB table; returns [] if unavailable."""
        if self.lancedb_dir is None:
            return []
        table_path = Path(self.lancedb_dir) / "kg_nodes.lance"
        if not table_path.exists():
            return []
        try:
            import lancedb  # pylint: disable=import-outside-toplevel
            from kg_utils.embedder import get_embedder  # pylint: disable=import-outside-toplevel

            embedder = get_embedder()
            vec = embedder.embed_query(q)
            db = lancedb.connect(str(self.lancedb_dir))
            table = db.open_table("kg_nodes")
            rows = table.search(vec).limit(k).to_list()
        except Exception:  # pylint: disable=broad-exception-caught
            return []

        nodes: list[dict[str, Any]] = []
        for r in rows:
            dist = float(r.get("_distance", 0.0))
            score = max(0.0, 1.0 - dist / 2.0)
            nodes.append(
                {
                    "node_id": r.get("id", ""),
                    "kind": r.get("kind", ""),
                    "name": r.get("name", ""),
                    "qualname": r.get("qualname", ""),
                    "source_path": r.get("module_path", ""),
                    "docstring": r.get("text", ""),
                    "score": score,
                }
            )
        return nodes

    def _lexical_query(self, q: str, k: int) -> list[dict[str, Any]]:
        """Substring LIKE fallback used when no vector index is available.

        Searches ``qualname``, ``kind``, ``docstring``, and the JSON-encoded
        ``metadata`` column so a query like ``"sunset"`` can match an image
        whose EXIF description contains it, even without an embedding index.
        """
        assert self.db_path is not None
        pattern = f"%{q}%"
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT node_id, kind, name, qualname, source_path, docstring
                FROM nodes
                WHERE qualname LIKE ? OR kind LIKE ? OR docstring LIKE ?
                   OR metadata LIKE ?
                LIMIT ?
                """,
                (pattern, pattern, pattern, pattern, k),
            ).fetchall()
        return [
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

    def pack(self, q: str, **kwargs: Any) -> SnippetPack:
        """Pack metadata "snippets" for filesystem nodes.

        Filesystem nodes have no source body, so each snippet's ``content`` is
        a compact metadata blob — kind + path + size + docstring — assembled
        from the SQLite ``nodes`` table.  Both ``SnippetPack.nodes`` and
        ``SnippetPack.snippets`` are populated; consumers of either will work.

        :param q: Query string.
        :param k: Number of results.
        :param max_nodes: Max nodes in pack.
        :return: SnippetPack with snippet dicts (node_id, source_path, content, score, kind, name).
        """
        k: int = kwargs.get("k", 8)
        max_nodes: int = kwargs.get("max_nodes", 15)
        qresult = self.query(q, k=k)

        sizes: dict[str, int] = {}
        meta_blobs: dict[str, str | None] = {}
        if self.db_path is not None:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute("SELECT node_id, size_bytes, metadata FROM nodes").fetchall()
            for nid, sz, mb in rows:
                sizes[nid] = sz
                meta_blobs[nid] = mb

        snippets: list[dict[str, Any]] = []
        for n in qresult.nodes[:max_nodes]:
            nid = n.get("node_id", "")
            kind = n.get("kind", "")
            path = n.get("source_path", "")
            docstring = (n.get("docstring") or "").strip()
            size_bytes = sizes.get(nid, 0)
            lines = [f"{kind}: {path}"]
            if size_bytes:
                lines.append(f"size: {_fmt_size(size_bytes)}")
            if docstring:
                lines.append(docstring)
            mb = meta_blobs.get(nid)
            if mb:
                try:
                    meta = json.loads(mb)
                except (TypeError, ValueError):
                    meta = None
                prose = metadata_prose(meta)
                if prose:
                    lines.append(prose)
            snippets.append(
                {
                    "node_id": nid,
                    "source_path": path,
                    "content": "\n".join(lines),
                    "score": n.get("score", 0.0),
                    "kind": kind,
                    "name": n.get("name", ""),
                }
            )

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
            snippets=snippets,
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
