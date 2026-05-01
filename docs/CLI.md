# FTreeKG CLI Reference

Full flag reference for every `ftreekg` subcommand. For quick examples and
query patterns see [CHEATSHEET.md](CHEATSHEET.md). For the data-flow pipeline
see [pipeline.md](pipeline.md).

---

## Unified CLI

All commands are available via the `ftreekg` entry point:

```bash
ftreekg --help
ftreekg <command> --help
ftreekg --version
```

A handful of subcommands also ship as dedicated `ftreekg-<name>` script
aliases — useful for shell scripts, Makefiles, and CI pipelines with no
`poetry run` required.

| Script alias        | Subcommand          | Description                                    |
|---------------------|---------------------|------------------------------------------------|
| `ftreekg-build`     | `ftreekg build`     | Walk the tree → SQLite + LanceDB + metadata    |
| `ftreekg-query`     | `ftreekg query`     | Semantic search                                |
| `ftreekg-pack`      | `ftreekg pack`      | Metadata snippet pack                          |
| `ftreekg-analyze`   | `ftreekg analyze`   | Full Markdown analysis report                  |
| `ftreekg-snapshot`  | `ftreekg snapshot`  | Save / list / show / diff / prune snapshots    |

Subcommands without a dedicated alias (`status`, `install-hooks`) are only
reachable via the `ftreekg <command>` form.

---

## Shared Options

The following options are reused across most subcommands:

| Option         | Default                              | Description                                                         |
|----------------|--------------------------------------|---------------------------------------------------------------------|
| `--repo`       | `.`                                  | Repository or filesystem root                                        |
| `--db`         | `<repo>/.filetreekg/graph.sqlite`    | SQLite database path                                                 |
| `--lancedb`    | `<repo>/.filetreekg/lancedb`         | LanceDB index directory                                              |
| `--model`      | `BAAI/bge-small-en-v1.5`             | Sentence-transformer model (used by the embedder via `kg_utils`)     |
| `-k`, `--k`    | `8`                                  | Number of top results to return                                      |
| `--include-dir`| —                                    | Top-level directory to include (repeatable; replaces config)         |
| `--exclude-dir`| —                                    | Directory name to skip at every depth (repeatable; replaces config)  |

---

## `ftreekg build` — Index a tree

```bash
ftreekg build [OPTIONS]
```

Walks the filesystem, extracts nodes (files, directories, symlinks), populates
sizes and per-format metadata (EXIF, etc.), and embeds canonical text into
LanceDB. Wipes existing data by default.

| Option          | Default                              | Description                                              |
|-----------------|--------------------------------------|----------------------------------------------------------|
| `--repo`        | `.`                                  | Tree root                                                |
| `--db`          | `<repo>/.filetreekg/graph.sqlite`    | SQLite path                                              |
| `--lancedb`     | `<repo>/.filetreekg/lancedb`         | LanceDB path                                             |
| `--model`       | `BAAI/bge-small-en-v1.5`             | Embedding model                                          |
| `--include-dir` | —                                    | Restrict to these tops (repeatable)                      |
| `--exclude-dir` | —                                    | Skip these names at every depth (repeatable)             |
| `--no-wipe`     | off                                  | Keep existing graph; only add new paths                  |

CLI `--include-dir` / `--exclude-dir` flags override `[tool.filetreekg]`
config from `pyproject.toml`. Built-in skip list (`__pycache__`, `venv`,
`build`, `dist`, `node_modules`, `egg-info`, `env`) and dotdirs always apply.

---

## `ftreekg query` — Semantic search

```bash
ftreekg query QUERY [OPTIONS]
```

| Option       | Default                              | Description                          |
|--------------|--------------------------------------|--------------------------------------|
| `QUERY`      | required                             | Natural-language search string       |
| `--repo`     | `.`                                  | Tree root                            |
| `--db`       | `<repo>/.filetreekg/graph.sqlite`    | SQLite path                          |
| `--lancedb`  | `<repo>/.filetreekg/lancedb`         | LanceDB path                         |
| `-k`, `--k`  | `8`                                  | Top-K results                        |

Vector search is primary; if LanceDB is missing or empty, falls back to
substring `LIKE` over `qualname`, `kind`, `docstring`, and `metadata`.

---

## `ftreekg pack` — Metadata snippet pack

```bash
ftreekg pack QUERY [OPTIONS]
```

| Option       | Default                              | Description                          |
|--------------|--------------------------------------|--------------------------------------|
| `QUERY`      | required                             | Natural-language search string       |
| `--repo`     | `.`                                  | Tree root                            |
| `--db`       | `<repo>/.filetreekg/graph.sqlite`    | SQLite path                          |
| `--lancedb`  | `<repo>/.filetreekg/lancedb`         | LanceDB path                         |
| `-k`, `--k`  | `8`                                  | Top-K results                        |

Returns the same ranked nodes as `query` but emits per-node metadata blocks
suitable for LLM context: kind, path, size, docstring, projected metadata
prose (camera, taken_at, GPS, dimensions, etc.).

---

## `ftreekg status` — Live dashboard

```bash
ftreekg status [OPTIONS]
```

| Option   | Default                              | Description     |
|----------|--------------------------------------|-----------------|
| `--repo` | `.`                                  | Tree root       |
| `--db`   | `<repo>/.filetreekg/graph.sqlite`    | SQLite path     |

Exits 1 if the graph store is missing. Renders a Rich-formatted panel showing
version, build timestamp, DB path/size, LanceDB presence, include/exclude
config, node/edge count tables, total indexed size, and a size-by-top-level
directory bar chart.

---

## `ftreekg analyze` — Full report

```bash
ftreekg analyze [OPTIONS]
```

| Option         | Default                                     | Description                          |
|----------------|---------------------------------------------|--------------------------------------|
| `--repo`       | `.`                                         | Tree root                            |
| `--db`         | `<repo>/.filetreekg/graph.sqlite`           | SQLite path                          |
| `--lancedb`    | `<repo>/.filetreekg/lancedb`                | LanceDB path                         |
| `-o`, `--output` | `<repo>/analysis/filetreekg_analysis.md`  | Markdown output path                 |

Writes a Markdown report with summary table, size-by-top-dir ASCII chart,
directory tree (depth ≤ 3), and path/link breakdowns.

---

## `ftreekg snapshot` — Temporal metrics

```bash
ftreekg snapshot save [VERSION] [OPTIONS]
ftreekg snapshot list [OPTIONS]
ftreekg snapshot show KEY [OPTIONS]
ftreekg snapshot diff KEY_A KEY_B [OPTIONS]
ftreekg snapshot prune [OPTIONS]
```

Snapshots are stored at `.filetreekg/snapshots/<tree-hash>.json`, indexed by
a `manifest.json`. The tree hash is auto-detected from the staged git tree
when not provided.

### `save`

| Option            | Default                              | Description                                    |
|-------------------|--------------------------------------|------------------------------------------------|
| `VERSION`         | —                                    | Optional version tag (e.g. `0.8.0`)            |
| `--repo`          | `.`                                  | Tree root                                      |
| `--db`            | `<repo>/.filetreekg/graph.sqlite`    | SQLite path                                    |
| `--lancedb`       | `<repo>/.filetreekg/lancedb`         | LanceDB path                                   |
| `--snapshots-dir` | `<repo>/.filetreekg/snapshots`       | Snapshots directory                            |
| `--branch`        | auto-detect from git                 | Branch name override                           |
| `--tree-hash`     | auto-detect via `git write-tree`     | Tree hash override                             |

### `list`

| Option            | Default                              | Description                              |
|-------------------|--------------------------------------|------------------------------------------|
| `--snapshots-dir` | `<cwd>/.filetreekg/snapshots`        | Snapshots directory                      |
| `--limit`         | unlimited                            | Max snapshots to show                    |
| `--branch`        | —                                    | Filter by branch name                    |
| `--json`          | off                                  | Emit JSON instead of formatted table     |

### `show KEY`

| Option            | Default                              | Description                              |
|-------------------|--------------------------------------|------------------------------------------|
| `KEY`             | required                             | Tree hash, short prefix, or `latest`     |
| `--snapshots-dir` | `<cwd>/.filetreekg/snapshots`        | Snapshots directory                      |

Shows full metrics, node/edge breakdown, top-level directory counts, and
deltas vs. previous and baseline snapshots.

### `diff KEY_A KEY_B`

| Option            | Default                              | Description                              |
|-------------------|--------------------------------------|------------------------------------------|
| `KEY_A` / `KEY_B` | required                             | Tree hashes (or `latest`)                |
| `--snapshots-dir` | `<cwd>/.filetreekg/snapshots`        | Snapshots directory                      |
| `--json`          | off                                  | Emit JSON                                |

Side-by-side comparison: total nodes/edges/files/dirs and changed
directories.

### `prune`

| Option            | Default                              | Description                                              |
|-------------------|--------------------------------------|----------------------------------------------------------|
| `--snapshots-dir` | `<cwd>/.filetreekg/snapshots`        | Snapshots directory                                      |
| `--dry-run`       | off                                  | Preview removals without deleting                        |

Removes vestigial snapshots with no new metric information:

1. **Metric duplicates** — interior snapshots whose metrics match neighbors
2. **Broken entries** — manifest entries whose JSON file is missing
3. **Orphaned files** — JSON files not referenced by the manifest

The oldest (baseline) and newest (latest) snapshots are always kept.

---

## `ftreekg install-hooks` — Pre-commit auto-snapshot

```bash
ftreekg install-hooks [OPTIONS]
```

| Option   | Default | Description                                |
|----------|---------|--------------------------------------------|
| `--repo` | `.`     | Repository root                            |
| `--force`| off     | Overwrite existing `.git/hooks/pre-commit` |

Installs a `pre-commit` hook that, on every commit:

1. Captures the staged tree hash via `git write-tree`
2. Rebuilds the local FTreeKG index (`ftreekg build --repo <root>`)
3. Captures a metrics snapshot keyed by the tree hash
4. Stages `.filetreekg/snapshots/` so the snapshot is committed atomically
5. Runs the `pre-commit` framework (ruff, mypy, etc.) if installed

Skip for a single commit:

```bash
FTREEKG_SKIP_SNAPSHOT=1 git commit -m "wip"
```

---

## Configuration (`pyproject.toml`)

FTreeKG reads its config from `[tool.filetreekg]` in the repo's
`pyproject.toml`:

```toml
[tool.filetreekg]
include = ["src", "docs"]   # restrict indexing to these top-level dirs
exclude = ["archives", "backups"]   # additional skips beyond built-in defaults
```

| Key       | Type            | Default | Effect                                                              |
|-----------|-----------------|---------|---------------------------------------------------------------------|
| `include` | list of strings | `[]`    | If non-empty, only paths under these top-level dirs are indexed     |
| `exclude` | list of strings | `[]`    | Directory names to skip at every depth (in addition to built-ins)   |

Built-in skip list (always applied): `venv`, `env`, `__pycache__`, `build`,
`dist`, `egg-info`, `node_modules`. All dotdirs (`.git`, `.venv`, `.codekg`,
…) are skipped unless explicitly listed in `include`.

CLI flags `--include-dir` / `--exclude-dir` **replace** the config values
(not additive) when specified.

---

## Storage Layout

```
<repo>/.filetreekg/
  graph.sqlite      # SQLite knowledge graph
  lancedb/          # LanceDB vector index
    kg_nodes.lance  # one table: kg_nodes (id, kind, name, qualname, module_path, text, vector)
  snapshots/
    manifest.json
    <tree-hash>.json
```

The SQLite store is **canonical**; LanceDB is derived and disposable —
`ftreekg build` rebuilds it from SQLite. Drop `.filetreekg/lancedb` and
re-run `build` to regenerate without re-walking the tree.

---

## Embedding Model

The default model is `BAAI/bge-small-en-v1.5` (384-dim) provided through
`kg_utils.embedder.get_embedder()`. Override per command with `--model`, or
globally via `KGRAG_MODEL_DIR` (cache directory) and `kg_utils` config.

If the embedder is unavailable (no `sentence-transformers` installed, model
cache missing, etc.), the build prints a warning to stderr, skips the
embedding pass, and the SQLite graph is still complete. Queries will then
fall back to lexical `LIKE` matching.

---

## Python API

Every CLI command has a Python equivalent on `FileTreeKG`:

```python
from ftree_kg import FileTreeKG

kg = FileTreeKG(repo_root="/path/to/repo")
kg.build(wipe=True, embed=True, metadata=True)

stats = kg.stats()
result = kg.query("Python config files", k=10)
pack   = kg.pack("photos with GPS", k=5)
report = kg.analyze()      # Markdown string
kg.close()
```

| Method            | CLI equivalent                  |
|-------------------|---------------------------------|
| `build()`         | `ftreekg build`                 |
| `stats()`         | `ftreekg status` (data source)  |
| `query(q, k)`     | `ftreekg query`                 |
| `pack(q, k)`      | `ftreekg pack`                  |
| `analyze()`       | `ftreekg analyze`               |

---

## See Also

- [CHEATSHEET.md](CHEATSHEET.md) — query recipes and common patterns
- [pipeline.md](pipeline.md) — data-flow architecture (input for diagram generators)
- [guide.md](guide.md) — high-level overview and Python API examples
