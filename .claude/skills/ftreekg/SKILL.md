---
name: ftreekg
description: Expert knowledge for installing, configuring, and using FTreeKG — a knowledge graph over filesystem hierarchies (files, directories, symlinks) with filesystem stat and image EXIF metadata. Use this skill when the user asks about: setting up FTreeKG in a project, adding ftree-kg as a Poetry dependency, building the SQLite or sqlite-vec index over a directory tree, configuring .mcp.json for the ftreekg MCP server, using the ftreekg CLI (ftreekg build, ftreekg query, ftreekg pack, ftreekg analyze, ftreekg status, ftreekg snapshot, ftreekg install-hooks), using the query_tree / pack_tree / graph_stats / analyze_tree MCP tools, the FileTreeKG Python API, the FileTreeKGAdapter KGRAG integration (kind="filetree"), configuring [tool.filetreekg] include/exclude, or troubleshooting FTreeKG errors.
---

# FTreeKG — Filesystem Tree Knowledge Graph

## What it is

FTreeKG indexes a **filesystem hierarchy** — not code, not prose. Every file,
directory, and symlink becomes a node carrying filesystem stat (size, mtime,
mode, symlink target) plus per-format metadata (image EXIF), linked by
`CONTAINS` edges from parent to immediate child.

Reach for it to answer questions about **what is on disk**: where files live,
how large they are, when they changed, what camera took an image. For what code
*does* use PyCodeKG; for what documents *say* use DocKG.

Structure is authoritative — semantic search is an acceleration layer, never a
source of structure. Node IDs are deterministic, so builds are idempotent.

Repo: `~/repos/ftree_kg`. Package: `ftree-kg`. Python 3.12–3.13.

## Install

```bash
poetry add ftree-kg                  # core runtime
poetry add "ftree-kg[adapter]"       # + kg-rag, for the KGRAG adapter
```

Development setup in the repo itself:

```bash
poetry install --with dev            # + pytest, ruff, ty, pre-commit
poetry install --with dev,kg         # + the dockg/pycodekg CLIs (maintainer tooling)
```

`adapter` is the only feature extra. Dev tooling is a Poetry group, never an
extra — the fleet rule from `FLEET_STANDARDS.md`.

## Build

```bash
ftreekg build --repo .
```

Full pipeline: filesystem walk → SQLite → size collection → EXIF metadata →
sqlite-vec embedding. **It wipes and rebuilds by default.** Opt out with
`--no-wipe` to keep the existing graph and only add new paths.

> Note the polarity. FTreeKG is the one fleet CLI with a `--no-wipe` flag;
> `pycodekg build` and `dockg build` wipe unconditionally and reject `--wipe`
> outright. Passing `--wipe` to any of the three is an error.

Useful flags: `--include-dir` / `--exclude-dir` (repeatable), `--db`,
`--vectors`, `--model`.

## Query

```bash
ftreekg query "Python config files" -k 8      # ranked matches
ftreekg pack  "large images"        -k 8      # + size/stat/EXIF metadata blocks
ftreekg status                                # live counts, index metadata
ftreekg analyze -o analysis/report.md         # full Markdown report
```

Query falls back to a substring `LIKE` match over `qualname`, `kind`,
`docstring`, and the JSON `metadata` column when no vector index exists — so it
always returns something, embeddings or not.

## MCP server

```bash
ftreekg-mcp --repo /path/to/repo     # stdio (default) or --transport sse
```

`.mcp.json` for Claude Code:

```json
{
  "mcpServers": {
    "ftreekg": {
      "command": "poetry",
      "args": ["run", "ftreekg-mcp", "--repo", "/abs/path/to/repo"],
      "env": { "POETRY_VIRTUALENVS_IN_PROJECT": "false" }
    }
  }
}
```

| Tool | Returns |
|------|---------|
| `query_tree(q, k)` | Ranked nodes as JSON |
| `pack_tree(q, k, max_nodes)` | Markdown metadata blocks (size, stat, EXIF) |
| `graph_stats()` | JSON counts, `total_size_bytes`, `size_by_top_dir` |
| `analyze_tree()` | Full Markdown analysis report |

The server warns on stderr and still starts when the graph is missing — run
`ftreekg build` first or every tool returns empty.

> **Availability:** the MCP server landed after 0.12.0. Until the next release
> it exists only on `main` / a source install, not on the PyPI wheel.

## Schema

**Node ID:** `<kind>:<relative_path>:<name>`

| Path on disk | Node ID |
|--------------|---------|
| `src/ftree_kg/module.py` | `file:src/ftree_kg/module.py:module.py` |
| `src/ftree_kg` | `directory:src/ftree_kg:ftree_kg` |
| `bin/python` (symlink) | `symlink:bin/python:python` |
| repository root | `directory:.:` (synthetic; edge source only) |

**Kinds:** `file`, `directory`, `symlink`. **Edges:** `CONTAINS` only
(parent → immediate child). Symlinks are recorded but never followed.

Node dicts carry both `id` (the `kg_utils` contract) and `node_id` (the
long-standing FTreeKG spelling) — they hold the same value.

**Indices:** `.filetreekg/graph.sqlite` (canonical), `.filetreekg/vectors.sqlite`
(derived and disposable), `.filetreekg/snapshots/`.

Embeddings: `BAAI/bge-small-en-v1.5`, 384-d, cosine.

## Configuration

```toml
[tool.filetreekg]
include = ["src", "docs"]           # empty/absent = index everything
exclude = ["archives", "backups"]   # additional dirs beyond the defaults
```

Always skipped regardless of config: `venv`, `env`, `__pycache__`, `build`,
`dist`, `egg-info`, `node_modules`. Dotdirs are skipped unless named explicitly
in `include`. CLI flags override the TOML values.

## Snapshots

Temporal metric capture keyed by git tree hash.

```bash
ftreekg snapshot save 0.12.0 --repo .
ftreekg snapshot list
ftreekg snapshot diff 660e4f0a 3487ed5b
ftreekg snapshot prune
```

> **Gotcha:** `snapshot save` takes `--repo`, but `list` / `show` / `diff` /
> `prune` take `--snapshots-dir` instead. Passing `--repo` to those is an error.

`prune` removes metric-duplicate interior snapshots, broken manifest entries,
and orphan JSON files. Oldest and newest are always kept.

## Python API

```python
from ftree_kg import FileTreeKG

kg = FileTreeKG(repo_root=".")
kg.build(wipe=True, embed=True, metadata=True)

kg.stats()                  # total_nodes, node_counts, total_size_bytes, size_by_top_dir
kg.query("large images", k=8)          # -> QueryResult
kg.pack("config files", k=8, max_nodes=15)   # -> SnippetPack
kg.analyze()                # -> Markdown str
kg.close()
```

## KGRAG integration

`FileTreeKGAdapter` registers as **`kind="filetree"`** (`KGKind.FILETREE`) —
distinct from `"code"` (PyCodeKG) and `"doc"` (DocKG).

```python
kgrag.query(q, kinds=["code", "doc", "filetree"])
```

Requires the `[adapter]` extra. `adapter.py` imports `kg_rag` at module scope
and is deliberately *not* exported from `__init__.py` — kg-rag ships its own
`kg_rag/adapters/ftree_adapter.py` that lazily imports `ftree_kg`, so declaring
kg-rag a core dependency would create a genuine cycle.

## Pre-commit hook

```bash
ftreekg install-hooks --repo .        # --force to overwrite an existing hook
```

Rebuilds the index, captures a snapshot keyed by tree hash, stages
`.filetreekg/snapshots/`, then runs the pre-commit framework checks. Skip with
`FTREEKG_SKIP_SNAPSHOT=1 git commit ...`.

> In the `ftree_kg` repo itself the hook is customised locally to run quality
> checks first and build the *code* and *doc* KGs instead — `install-hooks
> --force` overwrites that customisation.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Error: No such option '--wipe'` | FTreeKG uses the opposite polarity | Drop it; use `--no-wipe` to *keep* the graph |
| Empty query results | No vector index, or stale graph | `ftreekg build --repo .` |
| Queries return paths that no longer exist | Built with `--no-wipe` after deletions | Rebuild without `--no-wipe` |
| MCP tools all return empty | Graph never built | `ftreekg build`, then reload the MCP client |
| `No such option '--repo'` on `snapshot list` | Wrong flag for that subcommand | Use `--snapshots-dir` |
| Image metadata missing | Pillow missing, or corrupt/unsupported file | Metadata extraction degrades silently by design; check the file opens in Pillow |
| Build skips a directory | `DEFAULT_SKIP_DIRS`, `[tool.filetreekg].exclude`, or dotdir rule | Name it explicitly in `include` |
