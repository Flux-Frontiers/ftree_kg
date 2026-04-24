# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## [0.5.0] - 2026-04-06

### Added
- `FileTreeKG.build()` — SQLite-backed graph build pipeline using the extractor; creates `nodes` and `edges` tables, wipes on request
- `FileTreeKG.query()` — text-match query over qualname, kind, and docstring; returns `kg_utils.types.QueryResult`
- `FileTreeKG.stats()` — SQLite aggregation returning `total_nodes`, `total_edges`, `node_counts`, `edge_counts`
- `nodes.size_bytes` column — two-pass build: pass 1 extracts nodes/edges, pass 2 re-stats each file to populate byte sizes
- `FileTreeKG.stats()` now returns `total_size_bytes` and `size_by_top_dir` (size aggregated per top-level directory)
- `FileTreeKG.analyze()` — richer Markdown report with summary table, ASCII bar chart of size by directory, and formatted node/edge breakdown tables
- `.gitignore` — added `.agentkg/` exclusions (DB + vectors only; snapshots tracked); switched all KG index entries from whole-directory exclusion to fine-grained patterns that keep `snapshots/` tracked

### Changed
- `build()` default changed from `wipe=False` to `wipe=True` — rebuild is the safe default
- `ftreekg build` CLI: `--wipe` flag replaced by `--no-wipe` (opt-out of the default rebuild)
- `_SCHEMA` now uses `DROP TABLE IF EXISTS` + `CREATE TABLE` instead of `CREATE TABLE IF NOT EXISTS` — prevents column-mismatch errors when schema evolves

### Changed
- `extractor.py`: replaced local-stub import (`ftree_kg.types`) with `from kg_utils.types import EdgeSpec, KGExtractor, NodeSpec`
- `module.py`: replaced broken try/except import block with `from kg_utils.types import KGModule, QueryResult, SnippetPack, NodeSpec, EdgeSpec`; `FileTreeKG` now inherits from the installed `kg_utils` SDK rather than the local stub
- `tests/test_query.py`: updated `importorskip` guard from `pycode_kg` → `kg_utils`; updated snapshot test guards from `kg_rag.snapshots` → `kg_snapshot`
- `.pre-commit-config.yaml`: mypy hook now covers `tests/` in addition to `src/`
- `pytest.ini`: `testpaths` updated to `./tests` (top-level); `pythonpath` set to `src`

### Removed
- `kg_utils/` local subpackage — promoted to a standalone installed package (`kg-utils`); all source, tests, and configuration deleted from this repo
- `src/tests/` — tests consolidated under top-level `tests/` directory

## [0.4.1] - 2026-04-06

### Added
- `poetry.toml` — in-project virtualenv configuration (`in-project = true`)
- `.gitignore`: added `.pycodekg/` entry to exclude the pycodekg index from version control (alongside existing `.codekg/`, `.dockg/`, `.filetreekg/` entries)

### Changed
- Migrated `pyproject.toml` from `[tool.poetry]` to PEP 621 `[project]` table; `kg-snapshot` is now a required runtime dependency (git source)
- `--db` and `--lancedb` CLI options now default to `None`; each command resolves the path relative to `--repo` at runtime, so `ftreekg build --repo /path/to/repo` no longer requires explicit db/lancedb flags
- `pyproject.toml` formatting: aligned tool config tables, added section comments, reformatted multi-value lists for readability
- `follow_untyped_imports = true` added to `[[tool.mypy.overrides]]` for `kg_snapshot.*` so mypy follows the imported types rather than silently treating them as `Any`
- Version bumped to `0.4.1` in `pyproject.toml` and `src/ftree_kg/__init__.py`

### Fixed
- `adapter.py`: `FileTreeKGAdapter.stats()` was accessing `.node_count` / `.edge_count` as attributes on the `dict` returned by `kg.stats()` — now uses `s.get("total_nodes", 0)` / `s.get("total_edges", 0)` (runtime `AttributeError` at every stats call)
- `snapshots.py`: `FtreeSnapshotManager.save_snapshot()` was missing the `force` keyword argument present in the base class — callers passing `force=True` would get a `TypeError`; return type corrected to `Path | None`
- `snapshots.py`: `FtreeSnapshotManager.capture()` parameter order corrected to match base class (`graph_stats_dict` positional, `stats_dict` keyword-only); `hotspots` and `issues` params added and forwarded to `super()`
- `snapshots.py`: `diff_snapshots()` now uses `cast(SnapshotMetrics, snap.metrics)` before passing to `metrics_to_dict()` to satisfy mypy after `follow_untyped_imports` was enabled
- `extractor.py`, `module.py`, `snapshots.py`: removed stale `# type: ignore[misc]` comments on class definitions — no longer needed now that pycode_kg/kg_snapshot types are fully resolved
- `module.py`: `FileTreeKG.pack()` override annotated with `# type: ignore[override]` — intentionally uses a different (filesystem-appropriate) interface
- `cmd_snapshot.py`, `test_query.py`: added `cast(SnapshotMetrics, ...)` / `cast(SnapshotDelta, ...)` at attribute-access sites to satisfy mypy; `saved.exists()` guard updated to handle `Path | None`

## [0.4.0] - 2026-03-29

### Added
- `src/ftree_kg/` — proper Python package namespace replacing the flat `src/` layout; Poetry now builds and installs the `ftree_kg` distribution correctly
- `[[tool.mypy.overrides]]` for `ftree_kg.*` so mypy gracefully handles self-referential imports in isolated environments
- `poetry.toml` — in-project virtualenv configuration (`in-project = true`)
- Initial FileTreeKG scaffold with KGModule infrastructure
- FileTreeKGExtractor for filesystem traversal
- FileTreeKG module with build, query, pack, analyze operations
- FileTreeKGAdapter for KGRAG federation (meta kind)
- Comprehensive test suite for extractor and query operations
- Full CLI (`ftreekg`) with `build`, `query`, `pack`, `analyze`, and `snapshot` subcommands
- `src/ftree_kg/snapshots.py` — `SnapshotManager` with `capture`, `save_snapshot`, `load_snapshot` (including `"latest"` key), `list_snapshots`, and `diff_snapshots`; filesystem-specific metrics (`total_files`, `total_dirs`, `dir_node_counts` per top-level directory); delta tracking vs. previous and baseline snapshots; degenerate-snapshot guard; git tree hash / branch auto-detection
- `src/ftree_kg/config.py` — reads `[tool.filetreekg]` from `pyproject.toml` for `include`/`exclude` dir lists; ships `DEFAULT_SKIP_DIRS` applied at every walk depth
- `.claude/` tooling: agents, commands, plugins, and skills for Claude Code integration
- `examples/query_examples.py` — runnable usage examples
- `analysis/filetreekg_analysis.md` — architectural analysis report
- `.pre-commit-config.yaml` and `.secrets.baseline` for pre-commit quality gates
- `src/ftree_kg/cli/cmd_hooks.py` — `ftreekg hooks install` CLI command that writes a pre-commit hook into `.git/hooks/`
- `FTreeKG.code-workspace` — VSCode workspace file for the project
- `codekg_pyproject.toml` — reference pyproject.toml snippet showing CodeKG integration setup
- `analysis/FTreeKG_analysis_20260321.md` — CodeKG architectural analysis report (2026-03-21, 936 nodes, grade D/55)

### Changed
- Renamed package root from `src/` (flat, uninstallable) to `src/ftree_kg/` and updated `pyproject.toml` `packages` declaration to `{include = "ftree_kg", from = "src"}`
- All internal imports rewritten from `src.*` → `ftree_kg.*` across every module, CLI command, and test file
- CLI entry points updated from `src.cli.*` → `ftree_kg.cli.*`
- Removed `kg-rag` as a required dependency; `code-kg` and `doc-kg` remain as direct git-sourced dependencies
- Removed `[tool.poetry.extras]` stanza (extras replaced by direct dependencies)
- `ftreekg snapshot` promoted from stub to a proper subcommand group (`save`, `list`, `show`, `diff`) backed by `SnapshotManager`
- Restructured source tree: `filetreekg/` → `src/ftree_kg/` and renamed package from `filetreekg` to `ftree-kg`
- Tests relocated from `filetreekg/tests/` to `src/tests/`
- `src/ftree_kg/snapshots.py` refactored as a thin layer over `kg_rag.snapshots`; `FtreeSnapshotManager` subclass adds filesystem-specific `SnapshotMetrics`/`SnapshotDelta` hydration and `files_delta`/`dirs_delta` in deltas
- `src/ftree_kg/cli/main.py` registers all subcommand modules via explicit imports so CLI entry points resolve correctly at install time
- Updated `poetry.lock` to Poetry 2.3.2 format

### Fixed
- Package was previously uninstallable via `pip install` / `poetry install` because `packages = [{include = "src"}]` included the entire `src/` directory rather than a named importable package
- Removed stale `type: ignore` comments from `snapshots.py` made redundant by `[[tool.mypy.overrides]]`
- Resolved cyclic import between `cli/main.py` and all `cmd_*.py` modules by extracting the Click group into `cli/group.py`
- Guarded `from kg_rag.snapshots import ...` with `try/except ImportError` so the module loads cleanly when `kg_rag` is absent
- CI type-check job now installs all extras so mypy can resolve `code_kg` and `kg_rag` imports

## [0.1.0] - 2026-03-15

### Added
- Initial release of FileTreeKG
