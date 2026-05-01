# FTreeKG Query Cheatsheet

A practical reference for the FTreeKG CLI and Python API, with examples drawn
from real filesystem trees. All queries below work against a live FTreeKG
knowledge graph built with `ftreekg build`.

---

## The CLI at a Glance

| Command | Best for | Returns |
|---|---|---|
| `ftreekg status` | Orientation — node/edge counts, indexed size, config | Rich dashboard |
| `ftreekg build` | Index a directory — SQLite + LanceDB + metadata pass | Build summary |
| `ftreekg query` | Semantic search — *which paths match this description* | Ranked node list |
| `ftreekg pack` | Metadata snippets — *what's actually in those nodes* | Per-node metadata blocks |
| `ftreekg analyze` | Full report — summary, size chart, directory tree | Markdown file |
| `ftreekg snapshot` | Temporal metrics — save, list, diff, prune | JSON snapshots |
| `ftreekg install-hooks` | Auto-snapshot pre-commit | Git hook script |

---

## 1. Orient First with `status`

Always start here when approaching an indexed tree or after a rebuild.

```bash
ftreekg status
```

Shows version, build timestamp, DB path and size, LanceDB presence,
include/exclude config, and node/edge breakdown alongside a size-by-top-level
directory bar chart.

```
FTreeKG Status — /Users/egs/repos/ftree_kg
  Version  : ftree-kg 0.8.0
  Built at : 2026-04-30 23:45:01 UTC
  DB path  : .filetreekg/graph.sqlite  (1.2 MB)
  LanceDB  : present

  Include dirs  : all (none specified)
  Exclude dirs  : .git, .venv, __pycache__, archives, backups, ...

  Nodes                       Edges
  ─────────────              ─────────────
  file       412              CONTAINS  573
  directory  158              total     573
  symlink     3
  total      573
```

Run this **before** querying — if `LanceDB: missing`, your queries will fall
back to lexical LIKE matching only.

---

## 2. Building the Index

### Standard build

```bash
ftreekg build --repo .
```

Wipes any existing index and runs the full three-pass pipeline:

1. **Pass 1** — walk the tree, emit `NodeSpec`/`EdgeSpec`, persist to SQLite
2. **Pass 2** — re-stat each file node to populate `size_bytes`
3. **Pass 2.5** — extract per-format metadata (EXIF for images, etc.)
4. **Pass 3** — embed canonical text per node, write to LanceDB

### Incremental build

```bash
ftreekg build --no-wipe
```

Keeps the existing graph and adds any new paths. Useful for iterative work
where you don't want to re-embed everything.

### Restrict scope

```bash
ftreekg build --include-dir src --include-dir docs
ftreekg build --exclude-dir node_modules --exclude-dir build
```

CLI flags **override** `[tool.filetreekg]` config from `pyproject.toml`.
With no flags and no config, all non-dotdir directories are indexed.

---

## 3. Semantic Search with `query`

Returns a ranked list of filesystem nodes most relevant to your description.
The vector index seeds the result; for filesystem nodes there is no graph
expansion (the only edge type is `CONTAINS`, which is a structural index, not
a semantic one).

### Find files by description

```bash
ftreekg query "Python CLI entry points"
ftreekg query "configuration and environment files"
ftreekg query "test fixtures"
```

Each result shows kind, qualname (relative path), score, and a snippet of the
filesystem stat docstring.

### Find images by EXIF

If your tree has photos, the EXIF metadata pass projects camera/date/GPS
into the embed text:

```bash
ftreekg query "iPhone photos from 2023"
ftreekg query "sunset photos San Francisco"
ftreekg query "Canon EOS portrait shots"
```

These work because `extract_image_metadata` lifts `Make`, `Model`,
`DateTimeOriginal`, `ImageDescription`, and GPS coordinates into the embed
keywords. No filename hints required.

### Tune result count

```bash
ftreekg query "large source files" -k 20
```

`-k` / `--k` controls how many results are returned. Default: 8.

---

## 4. Metadata Snippets with `pack`

`pack` runs the same query as `query` but emits per-node metadata blocks:
kind, path, size, docstring, and projected metadata prose (camera model,
capture date, GPS, dimensions, etc.).

```bash
ftreekg pack "config files"
ftreekg pack "images with GPS"
```

Use this when feeding filesystem context to an LLM — each block is
self-describing and grounded to a real path.

```
1. [file] src/ftree_kg/cli/cmd_build.py
   file: src/ftree_kg/cli/cmd_build.py
   size: 2.8 KB
   **Size:** 2812 bytes
   **Modified:** 2026-04-30T23:41:26
   **Mode:** -rw-r--r--

2. [file] photos/IMG_0042.jpg
   file: photos/IMG_0042.jpg
   size: 3.1 MB
   dimensions: 4032x3024
   camera_make: Apple
   camera_model: iPhone 14 Pro
   taken_at: 2023:07:15 18:42:11
   gps: 37.774929, -122.419418
```

---

## 5. Full Reports with `analyze`

```bash
ftreekg analyze                          # → analysis/filetreekg_analysis.md
ftreekg analyze -o reports/snapshot.md   # custom output
```

The Markdown report contains:

- **Summary table** — total paths, links, files, directories, symlinks, total size
- **Size by top-level directory** — ASCII bar chart proportional to byte counts
- **Directory tree (depth ≤ 3)** — pretty-printed structural view with size hints
- **Path breakdown** — count by node kind
- **Link breakdown** — count by edge relation

Use it for release notes, onboarding docs, or as input to PaperBanana
diagram generation.

---

## 6. Temporal Snapshots

Capture graph metrics at a moment in time, keyed by git tree hash. Useful for
tracking how a corpus evolves across releases or feature branches.

### Save

```bash
ftreekg snapshot save                    # auto tree hash + branch
ftreekg snapshot save 0.8.0              # tag with version
ftreekg snapshot save --branch feature/x --tree-hash abc1234
```

Snapshots live at `.filetreekg/snapshots/<tree-hash>.json` with a
`manifest.json` index.

### List

```bash
ftreekg snapshot list                    # newest first
ftreekg snapshot list --branch main
ftreekg snapshot list --json             # machine-readable
```

### Inspect

```bash
ftreekg snapshot show latest
ftreekg snapshot show abc1234
```

Shows full metrics, node/edge breakdown, top-level directory counts, and
deltas vs. previous and baseline.

### Compare

```bash
ftreekg snapshot diff abc1234 def5678
```

Side-by-side comparison: total nodes/edges/files/dirs and changed
directories.

### Prune

```bash
ftreekg snapshot prune --dry-run         # preview
ftreekg snapshot prune                   # remove duplicates and broken entries
```

Removes interior snapshots with unchanged metrics, broken manifest entries,
and orphan JSON files. Always keeps oldest (baseline) and newest.

### Auto-snapshot on commit

```bash
ftreekg install-hooks
```

Installs a `pre-commit` hook that rebuilds the index, captures a snapshot
keyed by the staged tree hash, stages `.filetreekg/snapshots/`, then runs
`pre-commit run`. Skip with `FTREEKG_SKIP_SNAPSHOT=1 git commit ...`.

---

## 7. Common Query Patterns

### "What's in this tree?"

```bash
ftreekg status
ftreekg analyze
```

### "Which files configure this project?"

```bash
ftreekg query "configuration and environment files"
ftreekg pack "config files"
```

### "Where do I put new tests?"

```bash
ftreekg query "test fixtures and test entry points"
```

### "Find all photos from a specific trip"

```bash
ftreekg query "iPhone photos San Francisco 2023"
ftreekg pack  "vacation photos with GPS coordinates"
```

### "How big is this directory?"

```bash
ftreekg analyze    # see Size-by-top-level-directory chart
```

### "Has anything new landed since last release?"

```bash
ftreekg snapshot diff <release-tree-hash> latest
```

---

## 8. Node ID Format

Every node has a stable, deterministic ID:

```
<kind>:<relative_path>:<name>

file:src/ftree_kg/module.py:module.py
directory:src/ftree_kg:ftree_kg
symlink:bin/python:python
```

IDs are reproducible across builds — same path + same kind = same ID.

---

## 9. Schema Quick Reference

### Nodes

| Kind | ID prefix | Description |
|---|---|---|
| `file` | `file:` | Regular file (with `size_bytes`, optional metadata blob) |
| `directory` | `directory:` | Directory node |
| `symlink` | `symlink:` | Symbolic link (target preserved in docstring) |

### Edges

| Relation | Direction | Meaning |
|---|---|---|
| `CONTAINS` | parent → child | Directory contains its immediate children |

### Per-node columns (SQLite)

| Column | Description |
|---|---|
| `node_id` | Stable ID (primary key) |
| `kind` | `file`, `directory`, or `symlink` |
| `name` | Basename (e.g. `module.py`) |
| `qualname` | Relative path from repo root |
| `source_path` | Same as qualname |
| `docstring` | Filesystem stat (size, mtime, mode, symlink target) |
| `size_bytes` | File size in bytes (0 for non-files) |
| `metadata` | JSON blob with per-format extraction (EXIF for images, etc.) |

---

## 10. Excluding Directories

By default FTreeKG indexes everything except dotdirs and a built-in skip list
(`venv`, `env`, `__pycache__`, `build`, `dist`, `egg-info`, `node_modules`).

**Configuration (`pyproject.toml`, persistent — recommended):**

```toml
[tool.filetreekg]
include = ["src", "docs"]    # restrict to these tops (empty = all non-skipped)
exclude = ["archives", "backups"]
```

**CLI flags (per-command override):**

```bash
ftreekg build --include-dir src --include-dir docs
ftreekg build --exclude-dir archives --exclude-dir backups
```

CLI flags **override** the pyproject.toml values entirely (not additive).
Dotdirs are excluded unless explicitly listed in `include`.

---

## 11. Per-Format Metadata Extraction

FTreeKG runs a metadata pass after stat collection. Currently implemented:

| Format | Extension(s) | Fields lifted into embed text |
|---|---|---|
| Images (EXIF) | `.jpg`, `.jpeg`, `.png`, `.tiff`, `.webp`, `.heic` | Make, Model, LensModel, DateTimeOriginal, ImageDescription, ISO, FNumber, Exposure, FocalLength, GPS, dimensions |

Stubs (return `None` for now): audio ID3, video metadata, PDF metadata.

The metadata is stored verbatim as a JSON blob in the `metadata` column AND
projected into the embed text as keyword tokens (year, year-month, GPS
coordinates, camera names, description). Both vector search and the lexical
LIKE fallback see this data.

A query like `"iPhone photos from 2023"` works because the embed text for a
photo taken on `2023:07:15` with an iPhone contains `Apple iPhone 2023
2023-07 ...` as keyword tokens.

---

## 12. KGRAG Integration

FTreeKG ships an adapter for the [KGRAG federated retrieval system](https://github.com/Flux-Frontiers/kgrag).
It registers with `kind="meta"`, distinguishing filesystem/structural metadata
from `kind="code"` (PyCodeKG) and `kind="docs"` (DocKG).

```python
from kg_rag import KGRAG

kgrag = KGRAG()
# Federated query — combines code, docs, and filesystem context
result = kgrag.query("how do we ship releases", kinds=["code", "docs", "meta"])
```

---

## 13. Live Stats Snapshot

Run on this repo right now:

```bash
ftreekg status
```

Or capture and inspect:

```bash
ftreekg snapshot save
ftreekg snapshot show latest
```

Rebuild after significant filesystem changes:

```bash
ftreekg build --repo .
```
