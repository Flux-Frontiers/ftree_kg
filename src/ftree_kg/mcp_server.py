#!/usr/bin/env python3
"""filetreekg/mcp_server.py

FTreeKG MCP Server — exposes the filesystem-tree knowledge graph as Model
Context Protocol (MCP) tools for MCP-compatible agents.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ftree_kg.module import FileTreeKG

_kg: FileTreeKG | None = None  # pylint: disable=invalid-name


def _get_kg() -> FileTreeKG:
    """Return the global FileTreeKG instance, raising if not initialised.

    :return: The FileTreeKG instance built by :func:`main`.
    :raises RuntimeError: If the server was imported without going through main().
    """
    if _kg is None:
        raise RuntimeError("FTreeKG not initialised. Run via 'ftreekg-mcp --repo /path/to/repo'")
    return _kg


mcp = FastMCP(
    "ftreekg",
    instructions=(
        "FTreeKG is a knowledge graph over a filesystem hierarchy. Every file, "
        "directory, and symlink is a node carrying filesystem stat (size, mtime, "
        "mode) plus per-format metadata (image EXIF), linked by CONTAINS edges. "
        "Use these tools to answer questions about what is on disk — where files "
        "live, how large they are, when they changed — rather than what code or "
        "prose says."
    ),
)


@mcp.tool()
def query_tree(q: str, k: int = 8) -> str:
    """Search the filesystem tree semantically and return ranked nodes as JSON.

    Falls back to a substring match when no vector index is present, so it
    always returns something useful.

    :param q: Semantic query string (e.g. "Python config files", "large images").
    :param k: Maximum number of results.
    :return: JSON-encoded QueryResult with ranked node dicts.
    """
    return _get_kg().query(q, k=k).to_json()


@mcp.tool()
def pack_tree(q: str, k: int = 8, max_nodes: int = 15) -> str:
    """Return filesystem metadata blocks for the nodes matching a query.

    Filesystem nodes have no source body, so each snippet is a compact metadata
    blob — kind, path, size, and stat — rather than code.

    :param q: Semantic query string.
    :param k: Number of results to seed from.
    :param max_nodes: Maximum nodes included in the pack.
    :return: Markdown-formatted metadata pack.
    """
    return _get_kg().pack(q, k=k, max_nodes=max_nodes).to_markdown()


@mcp.tool()
def graph_stats() -> str:
    """Return node/edge counts and size totals for the current FTreeKG store.

    :return: JSON with total_nodes, total_edges, node_counts, edge_counts,
             total_size_bytes, and size_by_top_dir.
    """
    return json.dumps(_get_kg().stats(), indent=2, ensure_ascii=False)


@mcp.tool()
def analyze_tree() -> str:
    """Generate a full Markdown analysis report of the filesystem tree.

    :return: Markdown report with counts, breakdown by kind, and size metrics.
    """
    return _get_kg().analyze()


def _parse_args(argv: list | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the FTreeKG MCP server.

    :param argv: Argument vector; defaults to ``sys.argv[1:]``.
    :return: Parsed namespace.
    """
    p = argparse.ArgumentParser(
        prog="ftreekg-mcp",
        description="FTreeKG MCP server — exposes filesystem tree query tools to AI agents.",
    )
    p.add_argument("--repo", default=".", help="Repository or filesystem root directory")
    p.add_argument(
        "--db",
        default=".filetreekg/graph.sqlite",
        help="Path to SQLite graph (default: .filetreekg/graph.sqlite)",
    )
    p.add_argument(
        "--vectors",
        default=None,
        help="Path to the sqlite-vec vector store (default: derived next to the graph)",
    )
    p.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="MCP transport: stdio (default) or sse",
    )
    return p.parse_args(argv)


def main(argv: list | None = None) -> None:
    """Start the FTreeKG MCP server and expose tools over MCP transport.

    :param argv: Argument vector; defaults to ``sys.argv[1:]``.
    """
    global _kg  # pylint: disable=global-statement

    args = _parse_args(argv)

    repo = Path(args.repo).resolve()
    db = Path(args.db) if Path(args.db).is_absolute() else repo / args.db
    vectors = None
    if args.vectors:
        vp = Path(args.vectors)
        vectors = vp if vp.is_absolute() else repo / vp

    if not db.exists():
        print(
            f"WARNING: SQLite database not found at '{db}'.\nRun 'ftreekg build' first.",
            file=sys.stderr,
        )

    _kg = FileTreeKG(repo_root=repo, db_path=db, vectors_path=vectors)

    print(
        f"FTreeKG MCP server starting\n"
        f"  repo     : {repo}\n"
        f"  db       : {db}\n"
        f"  vectors  : {_kg.vectors_path}\n"
        f"  transport: {args.transport}",
        file=sys.stderr,
    )

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
