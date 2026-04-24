[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![Version](https://img.shields.io/badge/version-0.6.0-blue.svg)](https://github.com/Flux-Frontiers/FTreeKG/releases)
[![CI](https://github.com/Flux-Frontiers/FTreeKG/actions/workflows/ci.yml/badge.svg)](https://github.com/Flux-Frontiers/FTreeKG/actions/workflows/ci.yml)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![DOI](https://zenodo.org/badge/1182124358.svg)](https://zenodo.org/badge/latestdoi/1182124358)

# FTreeKG

A [KGModule](https://github.com/Flux-Frontiers/kg_utils) for building knowledge graphs of filesystem hierarchies. Indexes files, directories, and symlinks with metadata, text search, and size analytics.

## Features

- **Path kinds:** `file`, `directory`, `symlink`
- **Link relations:** `CONTAINS`, `CHILD_OF`, `PARENT_OF`
- **Two-pass build:** extracts structure then enriches with `size_bytes` per file
- **Rich analysis:** summary table, ASCII size chart, directory tree, path/link breakdowns
- **KGRAG integration:** federates with CodeKG, DocKG as `kind="meta"`
- **CLI:** `ftreekg build`, `query`, `pack`, `analyze`, `snapshot`

## Requirements

- Python 3.12 or 3.13
- Poetry

## Installation

```bash
git clone https://github.com/flux-frontiers/FTreeKG.git
cd FTreeKG
poetry install --with dev
poetry shell
```

## Quick Start

```python
from ftree_kg import FileTreeKG

kg = FileTreeKG(repo_root="/path/to/directory")
kg.build()                                  # wipe=True by default

results = kg.query("configuration files", k=5)
for node in results.nodes:
    print(f"{node['kind']:10} {node['qualname']}")

stats = kg.stats()
print(f"{stats['total_nodes']} paths, {stats['total_edges']} links")
print(f"Total size: {stats['total_size_bytes']} bytes")
```

## CLI

```bash
# Build the index (wipes by default)
ftreekg build --repo /path/to/dir

# Keep existing index
ftreekg build --repo /path/to/dir --no-wipe

# Query
ftreekg query "config files" --k 10

# Full analysis report (written to analysis/filetreekg_analysis.md)
ftreekg analyze
```

## Analysis report

`ftreekg analyze` produces a Markdown report with:

- Summary table (paths, links, files, dirs, total size)
- ASCII bar chart — size by top-level directory
- ASCII directory tree (depth ≤ 3)
- Path and link breakdowns by kind/relation

## Configuration

Add to your `pyproject.toml` to scope which directories are indexed:

```toml
[tool.filetreekg]
include = ["src", "docs"]   # empty = entire repo
exclude = ["archives"]      # added on top of built-in skip list
```

## Development

```bash
poetry run pytest --tb=short
poetry run pylint src/
poetry run mypy src/ tests/
```

See [docs/guide.md](docs/guide.md) for architecture details.

## License

[Elastic License 2.0](https://www.elastic.co/licensing/elastic-license) — see [LICENSE](LICENSE).
