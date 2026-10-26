# MCP Integration

FTreeKG ships its own MCP server, `ftreekg mcp`, alongside a `.mcp.json`
that also wires the **sister KG servers** (PyCodeKG and DocKG) into any
Claude-Code-compatible AI agent working in this checkout.

This document covers three things: the FTreeKG server itself, how the
local `.mcp.json` is laid out for FTreeKG developers, and the federated
KGRAG alternative.

---

## The FTreeKG MCP server

```bash
ftreekg mcp --repo /path/to/tree                                 # stdio (default)
ftreekg mcp --repo /path/to/tree --transport streamable-http --port 8765
ftreekg mcp --manifest                                           # list the tools as JSON
```

`ftreekg-mcp` is the same command under its older name. The server is
built on the fleet's shared base, `kg_utils.mcp`, so the first five tools
have the same names and arguments on every fleet KG server:

| Tool | Description |
|---|---|
| `stats()` | Node and edge counts by kind and relation, plus `total_size_bytes` and `size_by_top_dir` -- start here |
| `query(q, k, hop, max_nodes, rels)` | Semantic search; ranked filesystem nodes and the edges among them. `hop=1` adds a matched directory's entries |
| `pack(q, k, hop, max_nodes, rels)` | Same search, emitting per-node metadata blocks as Markdown (kind, path, size, EXIF prose) |
| `get_node(node_id)` | One node: kind, path, size and decoded metadata |
| `neighbors(node_id, rels, direction, limit)` | A node's edges and the nodes at their far ends: a directory's entries (`direction="out"`), a file's parent (`"in"`) |
| `analyze_tree()` | Render the full Markdown analysis report |

`hop` defaults to 0 here, so `query` and `pack` return only the semantic
matches unless asked to expand.

Options: `--repo`, `--db` (default `.filetreekg/graph.sqlite`),
`--vectors` (default derived next to the graph), `--model`, `--transport`
(`stdio` or `streamable-http`), `--host`, `--port`, `--manifest`. A
relative `--db` or `--vectors` is taken from `--repo`.

A tree with no graph is refused at session start rather than served
empty, so build first:

```bash
ftreekg build --repo .
```

Queries degrade gracefully. When no vector index is present, `query`
and `pack` fall back to a substring `LIKE` match over `qualname`,
`kind`, `docstring`, and the JSON `metadata` column -- so an EXIF
description is still reachable without embeddings.

---

## Local `.mcp.json` (this repo)

The repo ships a `.mcp.json` at the project root that any per-repo MCP
client (Claude Code, Kilo Code) reads automatically when it opens this
checkout. It registers three read-only servers that index this very repo:

```json
{
  "mcpServers": {
    "pycodekg": {
      "command": "poetry",
      "args": ["run", "pycodekg", "mcp", "--repo", "/path/to/ftree_kg"],
      "env": { "POETRY_VIRTUALENVS_IN_PROJECT": "false" }
    },
    "dockg": {
      "command": "poetry",
      "args": ["run", "dockg-mcp", "--repo", "/path/to/ftree_kg"],
      "env": { "POETRY_VIRTUALENVS_IN_PROJECT": "false" }
    },
    "ftreekg": {
      "command": "poetry",
      "args": ["run", "ftreekg", "mcp", "--repo", "/path/to/ftree_kg"],
      "env": { "POETRY_VIRTUALENVS_IN_PROJECT": "false" }
    }
  }
}
```

What that gets you, working in FTreeKG:

- **`pycodekg`** — the PyCodeKG server pointed at FTreeKG's own Python
  source. `stats`, `query`, `pack`, `get_node`, `neighbors`, then
  `callers`, `explain`, `centrality`, `analyze_repo`, snapshots, and
  the rest. This is how Claude navigates the FTreeKG codebase.
- **`dockg`** — the DocKG server pointed at FTreeKG's documentation
  corpus, with the same five canonical tools. This is how Claude finds
  prose from the README, docs/, and CHANGELOG.
- **`ftreekg`** — this repo's own filesystem graph, dogfooding the server
  described above.

To activate: build the indices (`pycodekg build --repo .`,
`dockg build --repo .`, and `ftreekg build --repo .`), then reload your MCP
client window (`Cmd+Shift+P` → `Developer: Reload Window` in VS Code-derived
clients). All three servers come up read-only — they query existing indices
and never write back.

> The `.mcp.json` shipped in this repo uses an absolute `--repo` path
> tied to the maintainer's checkout. Forks and contributors should
> rewrite the path to their own clone (or, better, switch the entries to
> use `"args": ["run", "ftreekg", "mcp", "--repo", "."]` if their MCP
> client launches the command from the repo root).

### Other providers

Provider configuration mirrors the patterns documented in
`pycode_kg/docs/MCP.md` and `doc_kg/docs/MCP.md`:

- **Claude Code / Kilo Code** — per-repo `.mcp.json` with a `ftreekg`
  entry pointing at `ftreekg mcp --repo .`.
- **GitHub Copilot** — per-repo `.vscode/mcp.json` with an absolute
  `--db` and `--vectors` to satisfy Copilot's no-cwd-inheritance
  behavior.
- **Claude Desktop** — global `claude_desktop_config.json` with an
  absolute path to the `ftreekg-mcp` venv binary.
- **Cline** — global, per-repo-keyed entry under
  `cline_mcp_settings.json` (`ftreekg-<repo-name>`).

---

## Without a server: the CLI

Every tool has a CLI equivalent, and each invocation opens the SQLite
store, runs the lookup, and exits — no daemon required:

```bash
ftreekg query "config files" -k 8     # -> query
ftreekg pack  "large images"  -k 8    # -> pack
ftreekg status                        # -> stats
ftreekg analyze                       # -> analyze_tree
```

This is a first-class path, not a fallback — useful for one-shot lookups
and for agents that prefer a Bash tool call to an MCP round-trip.

---

## Federated alternative: KGRAG

KGRAG also exposes `FileTreeKG` to MCP clients **via federation**.
Once the FTreeKG instance is registered with `kgrag`, the
`kgrag.query(q, kinds=["filetree"])` path returns FTreeKG hits inside
the same `CrossHit` / `CrossSnippet` envelope as PyCodeKG and DocKG
results — and the KGRAG MCP server makes that available to Claude as its
`query` tool.

```python
from kg_rag import KGRAG

kgrag = KGRAG()
# Filesystem context only
fs_hits = kgrag.query("config files", kinds=["filetree"])
# Cross-graph: code + docs + filesystem in one query
combined = kgrag.query("how do we ship releases",
                       kinds=["code", "doc", "filetree"])
```

Prefer this when an agent needs filesystem context *alongside* code or
docs — one federation layer instead of three server registrations. Prefer
`ftreekg mcp` when the filesystem tree is the subject rather than a
supporting cast.

---

## See also

- [CLI.md](CLI.md) — full `ftreekg` command reference
- [SCHEMA.md](SCHEMA.md) — node and edge schema (what the MCP tools
  return)
- [pipeline.md](pipeline.md) — how the index is built (what the MCP
  server queries against)
- [pycode_kg's `docs/MCP.md`](https://github.com/Flux-Frontiers/pycode_kg/blob/main/docs/MCP.md)
  — the canonical multi-provider MCP setup template
- [doc_kg's `docs/MCP.md`](https://github.com/Flux-Frontiers/doc_kg/blob/main/docs/MCP.md)
  — same template adapted for a document corpus
