#!/usr/bin/env python3
"""filetreekg/mcp_server.py

FTreeKG MCP Server -- serves a filesystem tree's knowledge graph to any
MCP-compatible agent over the fleet's shared server base, :mod:`kg_utils.mcp`.

The server answers the fleet's canonical tools -- ``stats``, ``query``,
``pack``, ``get_node``, ``neighbors`` -- under the same names as every other
KG server, plus ``analyze_tree``. ``query`` and ``pack`` are FileTreeKG's own:
the search falls back to a substring match when no vector index is built, and
a pack holds metadata blocks, not source text.

The tool list is not kept by hand anywhere: each tool's docstring is its
description, the server's instructions are generated from them, and::

    ftreekg mcp --manifest

prints the whole list as JSON without opening the graph.

Usage
-----
::

    ftreekg mcp --repo /path/to/tree

``--db`` and ``--vectors`` default to ``.filetreekg/graph.sqlite`` and
``.filetreekg/vectors.sqlite``; a relative path is taken from ``--repo``.
``ftreekg-mcp`` is the same command under its older name.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_utils.mcp import Context, KGServer, kg_from, make_server

from ftree_kg import __version__
from ftree_kg.module import FileTreeKG

PREAMBLE = (
    "FTreeKG is a knowledge graph over a filesystem hierarchy. Every file, "
    "directory, and symlink is a node carrying filesystem stat (size, mtime, "
    "mode) plus per-format metadata (image EXIF), linked by CONTAINS edges. "
    "Use these tools to answer questions about what is on disk -- where files "
    "live, how large they are, when they changed -- rather than what code or "
    "prose says.\n\n"
    "## Recommended workflows\n\n"
    "- **Orientation**: stats, then analyze_tree for sizes and the directory tree\n"
    "- **Find paths**: query -> get_node\n"
    "- **Read their metadata**: pack with a descriptive query\n"
    "- **Walk the tree**: neighbors(node_id) -- a directory's entries with "
    "direction='out', its parent with direction='in'"
)


def query(
    q: str,
    k: int = 8,
    hop: int = 0,
    max_nodes: int = 25,
    rels: list[str] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """
    Search the filesystem tree semantically and return ranked nodes and the edges among them.

    Falls back to a substring match when no vector index is present, so it
    always returns something useful.

    :param q: Semantic query string (e.g. "Python config files", "large images").
    :param k: Seeds to start from (1-100, default 8).
    :param hop: Graph hops to expand from each seed (0-5, default 0); 1 brings a directory's entries.
    :param max_nodes: Most nodes to return (default 25).
    :param rels: Edge types to follow when expanding; omit for all.
    """
    return kg_from(ctx).query(q, k=k, hop=hop, rels=rels, max_nodes=max_nodes).to_dict()


def pack(
    q: str,
    k: int = 8,
    hop: int = 0,
    max_nodes: int = 15,
    rels: list[str] | None = None,
    *,
    ctx: Context,
) -> str:
    """
    Filesystem metadata blocks for the nodes matching a query, as Markdown.

    Filesystem nodes have no source body, so each snippet is a compact metadata
    blob -- kind, path, size, and stat -- rather than code.

    :param q: Semantic query string.
    :param k: Seeds to start from (1-100, default 8).
    :param hop: Graph hops to expand from each seed (0-5, default 0).
    :param max_nodes: Most nodes in the pack (default 15).
    :param rels: Edge types to follow when expanding; omit for all.
    """
    return kg_from(ctx).pack(q, k=k, hop=hop, rels=rels, max_nodes=max_nodes).to_markdown()


def analyze_tree(ctx: Context) -> str:
    """
    A full Markdown analysis report of the filesystem tree.

    Counts, the breakdown by kind and relation, size by top-level directory,
    and the directory tree to depth 3.
    """
    return kg_from(ctx).analyze()


#: Domain tools, registered after the canonical five in this order.
EXTRA_TOOLS = (analyze_tree,)


def build_server(
    repo: str | Path,
    db: str | Path | None = None,
    vectors: str | Path | None = None,
    model: str | None = None,
) -> KGServer:
    """Build the FTreeKG MCP server for one tree, without opening its graph.

    :param repo: Tree root the graph was built from.
    :param db: Graph database; ``None`` for ``<repo>/.filetreekg/graph.sqlite``.
    :param vectors: Vector store; ``None`` for the store next to the graph.
    :param model: Accepted for the standard command; FileTreeKG embeds with
        the kg_utils default model.
    :return: The server; serve it with :func:`kg_utils.mcp.run`.
    """
    root = Path(repo).resolve()

    def open_kg() -> FileTreeKG:
        return FileTreeKG(repo_root=root, db_path=db, vectors_path=vectors)

    server = make_server(
        open_kg, name="ftreekg", kind="filetree", version=__version__, instructions=PREAMBLE
    )
    server.canonical("query")(query)
    server.canonical("pack")(pack)
    for fn in EXTRA_TOOLS:
        server.tool()(fn)
    return server


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``ftreekg-mcp``: the same command as ``ftreekg mcp``.

    :param argv: Arguments; ``None`` for ``sys.argv[1:]``.
    """
    from ftree_kg.cli.cmd_mcp import mcp_command  # pylint: disable=import-outside-toplevel

    mcp_command.main(args=argv, prog_name="ftreekg-mcp")


if __name__ == "__main__":
    main()
