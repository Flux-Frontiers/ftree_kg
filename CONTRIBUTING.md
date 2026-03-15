# Contributing to FTreeKG

## Development Setup

```bash
# Clone and install in editable mode
git clone https://github.com/flux-frontiers/FTreeKG.git
cd FTreeKG
pip install -e ".[dev]"
```

## Code Style

- **Formatter:** black
- **Linter:** ruff
- **Type checker:** mypy
- **Docstrings:** Google-style (`:param:` format)

## Before Submitting a PR

```bash
# Format code
black filetreekg tests conftest.py

# Lint
ruff check --fix filetreekg tests conftest.py

# Type check
mypy filetreekg tests conftest.py

# Run tests
pytest --cov=filetreekg
```

## Test Requirements

- All new features must include tests
- Tests should use fixtures in `tests/test_extractor.py` pattern
- Run with `pytest --cov=filetreekg` to check coverage

## Commit Message Format

- Use present tense: "add feature" not "added feature"
- Reference issues: "fix: resolve node ID stability (fixes #123)"
- Prefix with: `feat:`, `fix:`, `docs:`, `test:`, `chore:`

## Questions?

Open an issue or start a discussion on GitHub.
