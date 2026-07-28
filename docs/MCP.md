# MCP Integration

FTreeKG does **not** ship its own MCP server in v0.9 — the index is
small enough and the query surface narrow enough that the CLI and the
Python API cover the use cases that would otherwise want one. What this
repo *does* ship is a `.mcp.json` config that wires the **sister
KG servers** (PyCodeKG and DocKG) into any Claude-Code-compatible AI
agent working in this checkout.

This document covers two things: how the local `.mcp.json` is laid out
for FTreeKG developers, and what an FTreeKG-specific MCP server would
look like if/when one is added.

---

## Local `.mcp.json` (sister-server wiring)

The repo ships a `.mcp.json` at the project root that any per-repo MCP
client (Claude Code, Kilo Code) reads automatically when it opens this
checkout. It registers two read-only servers that index this very repo:

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
    }
  }
}
```

What that gets you, working in FTreeKG:

- **`pycodekg`** — the seventeen-tool PyCodeKG server pointed at FTreeKG's
  own Python source. `graph_stats`, `query_codebase`, `pack_snippets`,
  `callers`, `explain`, `centrality`, `analyze_repo`, snapshots, and
  the rest. This is how Claude navigates the FTreeKG codebase.
- **`dockg`** — the four-tool DocKG server pointed at FTreeKG's
  documentation corpus. `graph_stats`, `query_docs`, `pack_docs`,
  `get_node`. This is how Claude finds prose from the README, docs/,
  and CHANGELOG.

To activate: build the indices (`pycodekg build --repo .` and
`dockg build .`), then reload your MCP client window
(`Cmd+Shift+P` → `Developer: Reload Window` in VS Code-derived
clients). The two servers come up read-only — they query existing
indices and never write back.

> The `.mcp.json` shipped in this repo uses an absolute `--repo` path
> tied to the maintainer's checkout. Forks and contributors should
> rewrite the path to their own clone (or, better, switch the entries to
> use `"args": ["run", "pycodekg", "mcp", "--repo", "."]` if their MCP
> client launches the command from the repo root).

---

## Why FTreeKG itself has no MCP server (yet)

A filesystem KG has a deliberately narrow query surface — there are
three node kinds, one edge type, and the whole graph is small enough
that `ftreekg query` and `ftreekg pack` answer what an agent typically
wants to know. The structural-expansion phase that justifies an MCP
server in PyCodeKG and DocKG simply isn't there: there are no call
chains to traverse, no inheritance hierarchies to follow, no semantic
similarity edges to chase. Hop expansion over `CONTAINS` would
re-derive the directory tree, which the Python API already exposes
directly via `FileTreeKG.stats()` and `FileTreeKG.analyze()`.

For now, agents that need filesystem context against an FTreeKG-indexed
tree have two clean options:

1. **Shell out to the CLI** — `ftreekg query "..."` and
   `ftreekg pack "..."` from a Bash tool call. Each invocation opens
   the SQLite store, runs the sqlite-vec lookup, and exits. No daemon
   required.
2. **Use the KGRAG federation layer** — register the FTreeKG
   instance with KGRAG and let the federated MCP server (provided by
   `kgrag`) route filesystem queries through `FileTreeKGAdapter`.
   This is the path that the sister projects already take for
   cross-graph queries.

---

## Future: a dedicated `ftreekg mcp` command

If the use case grows beyond shell-out and KGRAG federation, a future
release would add a `ftreekg mcp` subcommand symmetric to PyCodeKG's
and DocKG's. The expected tool set:

| Tool | Description |
|---|---|
| `graph_stats()` | Node / edge counts and total indexed size — start here |
| `query_filetree(q, k)` | Hybrid semantic search; returns ranked filesystem nodes as JSON |
| `pack_filetree(q, k)` | Same query, but emits per-node metadata blocks as Markdown (kind, path, size, EXIF prose) |
| `get_node(node_id)` | Fetch a single node by stable ID; returns full metadata blob |
| `analyze_filetree()` | Render the full Markdown analysis report |
| `snapshot_list(limit, branch)` | List saved metric snapshots newest-first with deltas |
| `snapshot_show(key)` | Full metrics for a specific snapshot key, or `"latest"` |
| `snapshot_diff(key_a, key_b)` | Side-by-side comparison |

Provider configuration would mirror the patterns documented in
`pycode_kg/docs/MCP.md` and `doc_kg/docs/MCP.md`:

- **Claude Code / Kilo Code** — per-repo `.mcp.json` with a `ftreekg`
  entry pointing at `ftreekg-mcp --repo .`.
- **GitHub Copilot** — per-repo `.vscode/mcp.json` with an absolute
  `--db` and `--vectors` to satisfy Copilot's no-cwd-inheritance
  behavior.
- **Claude Desktop** — global `claude_desktop_config.json` with an
  absolute path to the `ftreekg-mcp` venv binary.
- **Cline** — global, per-repo-keyed entry under
  `cline_mcp_settings.json` (`ftreekg-<repo-name>`).

Tracking issue: open a request on
[the issue tracker](https://github.com/Flux-Frontiers/FTreeKG/issues)
if your workflow needs this sooner.

---

## Federated alternative: KGRAG today

KGRAG already exposes `FileTreeKG` to MCP clients **via federation**.
Once the FTreeKG instance is registered with `kgrag`, the
`kgrag.query(q, kinds=["filetree"])` path returns FTreeKG hits inside
the same `CrossHit` / `CrossSnippet` envelope as PyCodeKG and DocKG
results — and the KGRAG MCP server makes that available to Claude as a
single `kgrag_query` tool.

```python
from kg_rag import KGRAG

kgrag = KGRAG()
# Filesystem context only
fs_hits = kgrag.query("config files", kinds=["filetree"])
# Cross-graph: code + docs + filesystem in one query
combined = kgrag.query("how do we ship releases",
                       kinds=["code", "doc", "filetree"])
```

This is the recommended path for any agent that needs filesystem
context alongside code or docs — it removes the MCP-server ceremony
entirely and routes everything through one federation layer.

---

## See also

- [CLI.md](CLI.md) — full `ftreekg` command reference (the surface area
  an MCP server would expose)
- [SCHEMA.md](SCHEMA.md) — node and edge schema (what an MCP tool would
  return)
- [pipeline.md](pipeline.md) — how the index is built (what an MCP
  server would query against)
- [pycode_kg's `docs/MCP.md`](https://github.com/Flux-Frontiers/pycode_kg/blob/main/docs/MCP.md)
  — the canonical multi-provider MCP setup template
- [doc_kg's `docs/MCP.md`](https://github.com/Flux-Frontiers/doc_kg/blob/main/docs/MCP.md)
  — same template adapted for a document corpus
