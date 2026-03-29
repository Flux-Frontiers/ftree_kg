[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![Version](https://img.shields.io/badge/version-0.4.0-blue.svg)](https://github.com/Flux-Frontiers/FTreeKG/releases)
[![CI](https://github.com/Flux-Frontiers/FTreeKG/actions/workflows/ci.yml/badge.svg)](https://github.com/Flux-Frontiers/FTreeKG/actions/workflows/ci.yml)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)

# FTreeKG

A KGModule for building knowledge graphs of file tree structures. Indexes filesystem hierarchies with semantic search over files, directories, symlinks, and logical modules.

## Features

- **Node kinds:** file, directory, symlink, module
- **Edge relations:** CONTAINS, CHILD_OF, PARENT_OF
- **KGKind:** meta
- **Semantic indexing:** Query filesystem structures by description
- **KGRAG integration:** Federate with CodeKG and DocKG

## Requirements

- Python 3.12 or 3.13
- Poetry

## Installation

```bash
# Clone and setup
git clone https://github.com/flux-frontiers/FTreeKG.git
cd FTreeKG
./scripts/setup.sh

# Activate environment
poetry shell
```

## Quick Start

```python
from filetreekg import FileTreeKG

# Initialize the knowledge graph
kg = FileTreeKG(repo_root="/path/to/directory")

# Build the index
kg.build(wipe=True)

# Query the filesystem
results = kg.query("find all configuration files", k=5)
for node in results.nodes:
    print(f"{node['name']}: {node['source_path']}")

# Get snippets with context
snippets = kg.pack("directory structure", k=3)
for snippet in snippets.snippets:
    print(f"{snippet.source_path}\n{snippet.content}")
```

## Development

```bash
# Install in editable mode
pip install -e .

# Run tests
pytest

# Build knowledge graph index
codekg build
```

## License

[Elastic License 2.0](https://www.elastic.co/licensing/elastic-license) — see [LICENSE](LICENSE).
