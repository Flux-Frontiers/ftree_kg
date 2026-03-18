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

MIT
