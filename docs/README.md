# FTreeKG Documentation

## Overview

FTreeKG (FileTreeKG) is a KGModule that transforms filesystem hierarchies into queryable knowledge graphs. It indexes files, directories, symlinks, and logical modules with semantic search capabilities.

## Architecture

### Node Types
- **file** — Regular files indexed with semantic search
- **directory** — Directory nodes organizing hierarchy
- **symlink** — Symbolic links in the filesystem
- **module** — Logical groupings or modules

### Edge Relations
- **CONTAINS** — Parent-child containment relationships
- **CHILD_OF** — Inverse child relationship
- **PARENT_OF** — Inverse parent relationship

### KGKind
- **meta** — Classified as metadata/structural knowledge graph

## Usage

### Building an Index

```python
from filetreekg import FileTreeKG

kg = FileTreeKG(repo_root="/path/to/analyze")
kg.build(wipe=True)
```

### Querying

```python
# Semantic search
results = kg.query("configuration files", k=5)

# Pack with context
snippets = kg.pack("directory structure", k=3)
```

### Analysis

```python
# Get statistics
stats = kg.stats()
print(f"Total nodes: {stats.node_count}")
print(f"Total edges: {stats.edge_count}")

# Full analysis report
analysis = kg.analyze()
print(analysis)
```

## Integration with KGRAG

FileTreeKG integrates with KGRAG for federated queries across CodeKG, DocKG, and other knowledge graphs:

```python
from kg_rag import KGRAG

kgrag = KGRAG()
# Query all registered KGs including FileTreeKG
results = kgrag.query("find all config files", kinds=["meta"])
```

## Project Structure

```
FTreeKG/
├── filetreekg/           # Main package
│   ├── extractor.py      # FileTreeKGExtractor
│   ├── module.py         # FileTreeKG KGModule
│   ├── adapter.py        # FileTreeKGAdapter (KGRAG)
│   └── tests/            # Test suite
├── docs/                 # Documentation
├── .claude/              # Project config
│   └── CLAUDE.md         # Development guide
├── .github/workflows/    # CI/CD
├── .mcp.json             # MCP server config
├── pyproject.toml        # Poetry configuration
└── pytest.ini            # Pytest config
```

## Development

See [`CLAUDE.md`](../.claude/CLAUDE.md) for project-specific instructions.
