# FTreeKG Project Instructions

## Overview

FTreeKG is a KGModule for indexing and querying filesystem hierarchies. It integrates with the KGRAG federated knowledge graph system.

## Development Workflow

### Setup

Requires Python 3.12 or 3.13.

```bash
# Basic setup (standalone)
./scripts/setup.sh

# With KGRAG integration
./scripts/setup.sh --with-kgrag

# Or using make
make setup
```

Then activate and build indices:

```bash
poetry shell
poetry run pycodekg build --repo . --wipe
poetry run dockg build --repo .
```

### Code Style

- Use `:param:` docstring style (Google format)
- Format with ruff
- Lint with ruff
- Type check with ty

### Before Committing

```bash
ruff format src tests conftest.py
ruff check --fix src tests
ty check src
pytest --cov=ftree_kg
```

### Pre-commit Hook

`.git/hooks/pre-commit` is customized locally to run `pycodekg build` and `dockg build` (+ `snapshot save`) instead of the generic `ftreekg build` that `ftreekg install-hooks` installs by default. This repo's own dev workflow cares about the code/docs KGs, not the filetree KG. This customization lives only in the local `.git/hooks/pre-commit` file (not tracked by git) — running `ftreekg install-hooks --force` will overwrite it back to the `ftreekg build` default, so reapply this note's change if that happens.

## Testing

- Tests live in `tests/`
- Use `sample_filesystem` fixture from `conftest.py` for filesystem tests
- All extraction must be deterministic (node IDs stable across runs)
- Coverage target: >80%

## Building Knowledge Graphs

The module itself should be indexed:

```bash
pycodekg build --repo . --wipe
dockg build --repo .
```

This enables semantic search over FTreeKG's own codebase.

## Release Workflow

See `CHANGELOG.md` for version management. Releases use Poetry:

```bash
poetry version patch/minor/major
poetry build
poetry publish
```

## Architecture Notes

- **FileTreeKGExtractor** (`src/ftree_kg/extractor.py`) — walks filesystem, yields NodeSpec/EdgeSpec
- **FileTreeKG** (`src/ftree_kg/module.py`) — KGModule (build, query, pack, analyze)
- **FileTreeKGAdapter** (`src/ftree_kg/adapter.py`) — KGRAG integration (kind="meta")

### Node ID Format

`<kind>:<relative_path>:<name>`

Example: `file:src/modules/core.py:core.py`

### Index Locations

- SQLite DB: `.filetreekg/graph.sqlite`
- Vector Index: `.filetreekg/lancedb/`
- PyCodeKG Index: `.pycodekg/` (auto-built by pycodekg)
- DocKG Index: `.dockg/` (auto-built by dockg)
