[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![Version](https://img.shields.io/badge/version-0.8.0-blue.svg)](https://github.com/Flux-Frontiers/FTreeKG/releases)
[![CI](https://github.com/Flux-Frontiers/FTreeKG/actions/workflows/ci.yml/badge.svg)](https://github.com/Flux-Frontiers/FTreeKG/actions/workflows/ci.yml)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![DOI](https://zenodo.org/badge/1182124358.svg)](https://zenodo.org/badge/latestdoi/1182124358)

**FTreeKG** — A Knowledge Graph for Filesystem Hierarchies
with Semantic Indexing and Per-Format Metadata Extraction

*Author: Eric G. Suchanek, PhD*
*Flux-Frontiers, Liberty TWP, OH*

---

## Overview

FTreeKG turns any directory tree into a knowledge graph you can talk to.
It walks the filesystem, classifies every entry as a file, directory, or
symlink, captures the cheap stat the OS already exposes — size, mtime,
mode, symlink target — and reaches one step further to lift per-format
metadata (image EXIF today; audio, video, and PDF reserved) into a
JSON blob that travels with each node. The skeleton is persisted to
SQLite; a LanceDB vector index sits on top for semantic search.

The point is to make a filesystem **askable**. *"Where do we keep
configuration?" "Which photos came from the iPhone in 2023?" "What
changed in `src/` since the last release?"* — questions that normally
require some combination of `find`, `mdfind`, manual inspection, and
guesswork get a single, ranked answer. The graph is small, fast to
build, and cheap to rebuild, so it works equally well as a one-shot
analysis tool, an LLM context source, and a structural complement to
codebase- and document-level knowledge graphs in the same workflow.

FTreeKG is a member of the [KGRAG](https://github.com/Flux-Frontiers/kgrag)
family of knowledge graphs. It uses the same hybrid SQLite-plus-LanceDB
architecture as its sister projects [PyCodeKG](https://github.com/Flux-Frontiers/pycode_kg)
(Python source) and [DocKG](https://github.com/Flux-Frontiers/doc_kg)
(document corpora), exposes itself to KGRAG's federated query layer with
the dedicated `KGKind.FILETREE` kind, and is built on the shared
[KGModule](https://github.com/Flux-Frontiers/kg_utils) primitives so it
slots cleanly into the same agents and pipelines.

The technical reading list:

- **[docs/SCHEMA.md](docs/SCHEMA.md)** — node kinds, edge types, node-ID
  format, full SQLite and LanceDB column reference, per-format metadata
  fields.
- **[docs/CHEATSHEET.md](docs/CHEATSHEET.md)** — query patterns, EXIF
  search recipes, snapshot workflows, common questions answered with
  one-liners.
- **[docs/CLI.md](docs/CLI.md)** — flag-by-flag reference for every
  `ftreekg` subcommand, plus the `pyproject.toml` configuration surface.
- **[docs/pipeline.md](docs/pipeline.md)** — the build and query
  pipelines as flowing prose, with diagram hints suitable for
  PaperBanana or any other generator.
- **[docs/MCP.md](docs/MCP.md)** — how the local `.mcp.json` wires
  PyCodeKG and DocKG into AI agents working on this repo, and what a
  dedicated FTreeKG MCP server would look like.

---

## Quick start

After installing the package, point `ftreekg build` at any directory.
The first run wipes any existing index and produces a fresh
`.filetreekg/` folder with the SQLite graph and the LanceDB vector
index inside it. Subsequent commands operate against that store with no
further setup.

```bash
ftreekg build --repo /path/to/project    # walk + extract + embed
ftreekg query "configuration files"      # natural-language search
ftreekg query "iPhone photos from 2023"  # EXIF-grounded search
ftreekg status                           # live dashboard
ftreekg analyze                          # full Markdown report
```

The `query` and `pack` commands are deliberately the primary surface:
`query` returns a ranked list of nodes, `pack` returns the same nodes
with their metadata rendered as paste-ready blocks for LLM context.
`status` is the orientation tool — run it whenever you want to know
what's in the index right now. `analyze` writes a longer report to
`analysis/filetreekg_analysis.md` with a summary table, an
ASCII size-by-top-directory bar chart, a depth-3 directory tree, and
per-kind/per-relation breakdowns.

For the full set of commands and flags see [docs/CLI.md](docs/CLI.md);
for query recipes see [docs/CHEATSHEET.md](docs/CHEATSHEET.md).

---

## Installation

FTreeKG requires Python 3.12 or 3.13. The core install pulls Click,
Rich, LanceDB, Pillow, and the shared `kgmodule-utils` package:

```bash
pip install ftree-kg                  # core runtime
pip install 'ftree-kg[kgdeps]'        # add PyCodeKG + DocKG for federation
poetry add ftree-kg                   # Poetry equivalent
```

The `kgdeps` extra is what you want if you're working in a repo where
PyCodeKG and DocKG are also indexing alongside FTreeKG — it pins
compatible versions of both. For a complete development setup
(linting, tests, pre-commit, all extras), see
[docs/CLI.md#development-setup](docs/CLI.md).

---

## How it works

A build runs three meaningful passes. The first walks the tree with
`Path.rglob`, applies the include/exclude/dotdir rules, and inserts a
node row per entry plus a `CONTAINS` edge from each parent. The second
re-stats every file to fill in `size_bytes`. The third — the per-format
metadata pass — calls into the dispatcher in `ftree_kg.metadata`, which
opens images with Pillow and decodes camera, lens, capture timestamp,
GPS coordinates, and dimensions; the resulting dict is JSON-serialized
into the `metadata` column. A final embedding step builds a canonical
two-line text document for each node — `"{kind} {basename} at {path}"`
plus a keyword line that includes path components, basename token
splits, the file extension, and projected metadata tokens (camera
make/model, year, year-month, GPS) — embeds them in batches via
`kg_utils.embedder`, and writes the vectors to a single LanceDB table.

That metadata projection is what makes EXIF-grounded queries work
without any filename hints. A photo whose path is just
`photos/IMG_0042.jpg` ends up with an embed line that mentions
`apple iphone 14 pro 2023 2023-07 gps:37.7749,-122.4194`, so a query
like *"iPhone photos from 2023"* matches it directly. The schema doc
walks through the embed-text format end-to-end:
[docs/SCHEMA.md#embed-text-format](docs/SCHEMA.md#embed-text-format).

Querying is intentionally simple: the query string is embedded with the
same model used at build time, LanceDB returns the top-`k` nodes ranked
by cosine distance, and that's the answer. There is no graph expansion
phase — filesystem nodes have only `CONTAINS`, which is structural and
not semantically informative for hop-style retrieval. When the LanceDB
table is missing or the embedder fails to load, `query` falls back to a
substring `LIKE` search across `qualname`, `kind`, `docstring`, and
`metadata`, so it always returns something useful even on a freshly
extracted tree with no embeddings.

The full pipeline is described in flowing prose, layer by layer, in
[docs/pipeline.md](docs/pipeline.md), which doubles as the input format
for diagram generators.

---

## Python API

Everything the CLI does is one method call away on `FileTreeKG`:

```python
from ftree_kg import FileTreeKG

kg = FileTreeKG(repo_root="/path/to/project")
kg.build()                              # wipe=True, embed=True, metadata=True

result = kg.query("configuration files", k=5)
for node in result.nodes:
    print(f"{node['kind']:12} {node['qualname']}  ({node['score']:.3f})")

stats = kg.stats()
print(f"{stats['total_nodes']:,} paths, {stats['total_size_bytes']:,} bytes")

print(kg.analyze())                     # Markdown report as a string
kg.close()
```

`build()` accepts `embed=False` and `metadata=False` to skip the
expensive passes — useful when you want a fast structural index for
testing, or when the embedder isn't available in CI.

---

## Configuration

Indexing scope is configurable from `pyproject.toml`. The block lives
under `[tool.filetreekg]` and has two keys, both optional:

```toml
[tool.filetreekg]
include = ["src", "docs"]   # restrict to these top-level directories
exclude = ["archives"]      # skip in addition to the built-in skip list
```

`include` is a whitelist — when it's non-empty, only paths under one of
the listed directories are indexed. `exclude` is additive on top of
the always-skipped names (`venv`, `env`, `__pycache__`, `build`,
`dist`, `egg-info`, `node_modules`). All dotdirs (`.git`, `.venv`,
`.pycodekg`, …) are skipped automatically unless you explicitly list them
in `include`.

CLI flags `--include-dir` and `--exclude-dir` override the config when
specified. Full precedence rules and per-command examples live in
[docs/CLI.md](docs/CLI.md).

---

## Storage

A built tree gets a single hidden directory:

```
.filetreekg/
  graph.sqlite       # canonical knowledge graph (nodes + edges + metadata)
  lancedb/           # derived vector index (kg_nodes.lance)
  snapshots/         # temporal metric snapshots, keyed by git tree hash
    manifest.json
    <tree-hash>.json
```

SQLite is **canonical** — it is the source of truth. LanceDB is
**derived and disposable**: deleting `.filetreekg/lancedb/` and
re-running `ftreekg build` reproduces it without re-walking the tree
(the embed pass reads from SQLite). Snapshots are append-only and
keyed by the git tree hash of the staged index, so they form a
deterministic timeline you can `diff` between commits or releases.
`ftreekg install-hooks` writes a pre-commit hook that captures a
snapshot on every commit.

For column-level details — node IDs, every SQLite column, every
LanceDB column, every per-format metadata field — see
[docs/SCHEMA.md](docs/SCHEMA.md).

---

## KGRAG federation

`FileTreeKG.kind()` returns `"filetree"` (the dedicated
`KGKind.FILETREE` enum value), and `FileTreeKGAdapter` exposes the
module to the [KGRAG](https://github.com/Flux-Frontiers/kgrag)
federation layer. That means a single federated query can combine
filesystem context with code and document context from PyCodeKG and
DocKG indexed against the same repo:

```python
from kg_rag import KGRAG

kgrag = KGRAG()
result = kgrag.query("how do we ship releases",
                     kinds=["code", "doc", "filetree"])
```

For working with the repo through MCP-compatible AI agents — including
the `.mcp.json` shipped in this checkout and the federated alternative
to a dedicated FTreeKG MCP server — see [docs/MCP.md](docs/MCP.md).

---

## Citation

If you use FTreeKG in research or a project, please cite it:

[![DOI](https://zenodo.org/badge/1182124358.svg)](https://zenodo.org/badge/latestdoi/1182124358)

**APA**

> Suchanek, E. G. (2026). *FTreeKG: Knowledge Graph for Filesystem Hierarchies* (Version 0.8.0) [Software]. Flux-Frontiers. https://doi.org/10.5281/zenodo.1182124358

**BibTeX**

```bibtex
@software{suchanek_ftree_kg,
  author    = {Suchanek, Eric G.},
  title     = {{FTreeKG}: Knowledge Graph for Filesystem Hierarchies},
  version   = {0.8.0},
  year      = {2026},
  publisher = {Flux-Frontiers},
  url       = {https://github.com/Flux-Frontiers/FTreeKG},
  doi       = {10.5281/zenodo.1182124358},
}
```

---

## License

[Elastic License 2.0](LICENSE) — free for non-commercial and internal
use; commercial redistribution requires a license from Flux-Frontiers.
