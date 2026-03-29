# Release Notes — v0.4.0

> Released: 2026-03-29

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

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
