# Release Notes -- v0.18.0

> Released: 2026-10-26

FTreeKG's MCP server now runs on the fleet's shared base, `kg_utils.mcp`, so
it answers the same five tools under the same names as every other KG server:
`stats`, `query`, `pack`, `get_node` and `neighbors`, plus `analyze_tree`.
`FileTreeKG` gained the methods behind the two new tools, and its search can
now expand through the tree.

## What changed

**Canonical tool names.** `graph_stats` is `stats`, `query_tree` is `query`
and `pack_tree` is `pack`, with no aliases. The new `get_node` returns one
path with its size and decoded metadata, and `neighbors` lists a directory's
entries (`direction="out"`) or a file's parent (`"in"`).

**Search that can walk the tree.** `query` and `pack` take `hop`, `rels` and
`max_nodes`. `hop` defaults to 0, so a search returns only its matches as
before; `hop=1` on a matched directory brings its entries and the edges
between them.

**One command, standard flags.** `ftreekg mcp` takes the fleet's `--repo`,
`--db`, `--vectors`, `--model`, `--transport stdio|streamable-http`, `--host`,
`--port` and `--manifest`. `ftreekg-mcp` is the same command. The graph opens
per session and closes after, and a tree with no graph is refused instead of
served empty.

**Statistics in the fleet shape.** `FileTreeKG.stats()` returns `kind`,
`nodes` (`total`, `by_kind`) and `edges` (`total`, `by_rel`), plus
`total_size_bytes` and `size_by_top_dir`. `ftreekg build`, `status` and
`analyze` print what they did before, and snapshots record the same keys.

## Upgrading

Rename the tools in agent instructions and scripts (`graph_stats` -> `stats`,
`query_tree` -> `query`, `pack_tree` -> `pack`) and drop `--transport sse`
from any config. Code that read `FileTreeKG.stats()["total_nodes"]` reads
`["nodes"]["total"]` instead, or calls `kg_utils.stats.flat_stats()`.
ftree-kg now needs kgmodule-utils 0.29.0, whose `[mcp]` extra brings the MCP
SDK.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
