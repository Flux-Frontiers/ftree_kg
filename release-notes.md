# Release Notes — v0.6.0

> Released: 2026-04-24

### Added
- `_ascii_tree()` — renders a depth-limited, child-truncated ASCII directory tree from SQLite path rows; shown in `analyze()` under "Directory tree (depth ≤ 3)"
- `analyze()` — "Directory tree" section added after the size chart
- `pylint` added to dev dependencies so `poetry run pylint` uses the project venv
- `ftreekg snapshot prune` CLI command — removes metric-duplicate, broken, and orphaned snapshots; supports `--dry-run`
- `PruneResult` re-exported from `ftree_kg.snapshots` for backwards compatibility
- `CITATION.cff` — software citation metadata for Zenodo/GitHub
- `ftree_kg.code-workspace` — VS Code workspace file for the project
- DOI badge added to `README.md`

### Changed
- `analyze()` — terminology updated: "nodes" → "paths", "edges" → "links" throughout (summary table, section headings)
- `README.md` — rewritten for v0.5.0: correct imports (`ftree_kg`), updated features list (paths/links, two-pass build, rich analysis), CLI examples, configuration section, link to `docs/guide.md`
- `docs/README.md` → `docs/guide.md` — renamed to avoid confusion with root README
- `.gitignore` — `.agentkg/` now fully excluded (local-only); `.claude/plugins/marketplaces/` excluded to prevent embedded-repo warnings
- `pyproject.toml` — consolidated all optional dependencies into PEP 621 `[project.optional-dependencies]`: `dev`, `kgdeps`, and `all` extras; removed Poetry-specific `[tool.poetry.group.*]` sections; both `pip install -e ".[all]"` and `poetry install --all-extras` now work
- `.vscode/settings.json` — fixed `python.testing.pytestArgs` to point at `tests/` (was `filetreekg/tests/`)

### Fixed
- `_ascii_tree()` type annotations: bare `dict` → `dict[str, dict[str, Any]]` (mypy `type-arg` errors)
- `_bar` local variable renamed to `_size_bar` / `size_bar` to satisfy pylint `disallowed-name`

### Removed
- `.agentkg/snapshots/` — removed from git history; agentkg data is now local-only
- `pyproject.toml` — removed stale `pycode_kg.*` from mypy overrides; removed Poetry group deps (now in PEP 621 extras)

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
