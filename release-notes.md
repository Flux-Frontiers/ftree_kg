# Release Notes — v0.13.0

> Released: 2026-08-15

FTreeKG gets an MCP server. Until now it was the only indexing KGModule in the
fleet without one — PyCodeKG and DocKG were reachable from an agent, the
filesystem graph was not, and closing that gap meant shelling out to the CLI or
routing through KGRAG federation. `ftreekg-mcp` makes the filetree graph a
first-class participant alongside its sisters.

## What changed

**An MCP server, deliberately small.** `ftreekg-mcp` speaks stdio or SSE and
exposes four tools: `query_tree` for ranked filesystem nodes, `pack_tree` for
their metadata rendered as Markdown blocks, `graph_stats` for counts and size
totals, and `analyze_tree` for the full report. That is the whole surface, and
it is meant to be. A filesystem graph has three node kinds and one edge type, so
there are no call chains or similarity edges to traverse — the hop-expansion
machinery that justifies seventeen tools in PyCodeKG would only re-derive the
directory tree here. The server starts even when the graph is missing, warning
on stderr rather than failing, so a misconfigured client reports empty results
instead of a crash.

**A pack-rendering bug that had been there all along.** Wiring the server up
immediately broke on `SnippetPack.to_markdown()`, which raised `KeyError: 'id'`
on every FTreeKG pack. The cause was a quiet divergence: FTreeKG's query nodes
carried only its own `node_id` spelling, while the shared `kg_utils` node
contract — and every other module in the fleet — uses `id`. Nothing had noticed
because the CLI renders packs through rich and never calls `to_markdown()`. Both
keys are now emitted, so anything reading `node_id` is untouched.

The test that should have caught it is worth a mention, because it existed and
passed. It read `node.get("id") or node.get("node_id")` — an either-or on a
two-spelling contract, which is indistinguishable from no assertion at all. It
is now an equality check, and the semantic query path, which builds its node
dicts separately from the lexical one, got its own coverage rather than
inheriting a fix it never exercised.

**Documentation caught up with the code.** `docs/MCP.md` was written around the
premise that FTreeKG has no MCP server and argued at length for why it did not
need one; it now documents the server that exists. Smaller corrections came out
of the same pass: the adapter was documented as registering `kind="meta"` when
the source has always used `KGKind.FILETREE`, and `snapshots.py` described
itself as a thin layer over `kg_rag.snapshots` when it has imported
`kg_utils.snapshots` for some time — which misleadingly implied that a core
module depended on the optional `[adapter]` extra.

## Upgrading

Nothing to migrate, and no rebuild is required — the graph format is unchanged,
so an existing `.filetreekg/` keeps working.

The one thing to know is that `mcp>=1.0.0,<2` is now a **core** dependency, not
an extra, so a plain `pip install ftree-kg` pulls it. The upper bound is
deliberate and matches doc-kg and pycode-kg: mcp 2.0 split `FastMCP` into a
standalone package, and `mcp_server.py` imports it from `mcp` at module scope.

To use the server, build an index and point a client at it:

```bash
ftreekg build --repo .
ftreekg-mcp --repo /abs/path/to/tree
```

For Claude Code, add an `ftreekg` entry to `.mcp.json` running
`ftreekg-mcp --repo .`; `docs/MCP.md` covers Copilot, Claude Desktop, and Cline
as well.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
