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
poetry run codekg build --repo . --wipe
poetry run dockg build --repo . --wipe
```

### Code Style

- Use `:param:` docstring style (Google format)
- Format with black
- Lint with ruff
- Type check with mypy

### Before Committing

```bash
black filetreekg tests conftest.py
ruff check --fix filetreekg tests
mypy filetreekg
pytest --cov=filetreekg
```

## Testing

- Tests live in `filetreekg/tests/`
- Use `sample_filesystem` fixture from `conftest.py` for filesystem tests
- All extraction must be deterministic (node IDs stable across runs)
- Coverage target: >80%

## Building Knowledge Graphs

The module itself should be indexed:

```bash
codekg build --repo . --wipe
dockg build --repo . --wipe
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

- **FileTreeKGExtractor** (`filetreekg/extractor.py`) — walks filesystem, yields NodeSpec/EdgeSpec
- **FileTreeKG** (`filetreekg/module.py`) — KGModule (build, query, pack, analyze)
- **FileTreeKGAdapter** (`filetreekg/adapter.py`) — KGRAG integration (kind="meta")

### Node ID Format

`<kind>:<relative_path>:<name>`

Example: `file:src/modules/core.py:core.py`

### Index Locations

- SQLite DB: `.filetreekg/graph.sqlite`
- Vector Index: `.filetreekg/lancedb/`
- CodeKG Index: `.codekg/` (auto-built by codekg)
- DocKG Index: `.dockg/` (auto-built by dockg)
