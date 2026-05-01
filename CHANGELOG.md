# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `ftree_kg.metadata` — per-format metadata extractor with image EXIF support via Pillow (camera make/model, lens, capture timestamp, description, ISO/F-number/exposure/focal length, GPS lat/lon decoded from DMS); stubs in place for audio/video/PDF
- `nodes.metadata` SQLite column — JSON blob populated by Pass 2.5 of `FileTreeKG.build()` with the canonical metadata dict for each file node
- `FileTreeKG.build(embed=True, metadata=True)` — Pass 2.5 (per-format metadata) and Pass 3 (LanceDB embedding) added to the build pipeline; both can be disabled
- `_embed_text()` — canonical text document builder used at embed time: `"{kind} {basename} at {path}"` plus a keyword line of path components, basename token splits, extension, and metadata-projected prose tokens (e.g. `"Apple iPhone 14 Pro 2023 beach at sunset"`)
- `FileTreeKG._semantic_query()` — LanceDB vector search over the `kg_nodes` table via `kg_utils.embedder`; returns ranked nodes with cosine-derived score
- `FileTreeKG._lexical_query()` — substring LIKE fallback (now also searching the `metadata` JSON blob), used when no vector index exists
- `FileTreeKG.pack()` — populates `SnippetPack.snippets` with real per-node content (kind, path, formatted size, docstring, EXIF prose) in addition to the existing `nodes` field
- `tests/test_metadata.py` — EXIF extraction tests including GPS DMS → decimal round-trip
- `tests/test_snapshots.py` — coverage for the FtreeSnapshotManager subclass
- Expanded `tests/test_query.py` — image-metadata embed-text and pack-snippet coverage
- `docs/CHEATSHEET.md` — query patterns and recipes (orient with `status`, build / incremental build, semantic search, EXIF-based image queries, `pack` for LLM context, snapshots, schema reference, exclusion rules) modeled on `doc_kg/docs/CHEATSHEET.md`
- `docs/CLI.md` — full flag reference for every subcommand (`build`, `query`, `pack`, `status`, `analyze`, `snapshot {save,list,show,diff,prune}`, `install-hooks`) with shared-options table, `pyproject.toml` config, storage layout, embedding-model notes, and a Python API mapping
- `docs/pipeline.md` — flowing-prose architecture and data-flow document modeled on `pycode_kg/docs/Architecture-plain.md`; suitable as input to PaperBanana / diagram generators (includes a "Diagram Hints" section specifying suggested layout, color coding, and arrow styles)
- Author / Last Revision / License headers added to every module under `src/ftree_kg/` and `src/ftree_kg/cli/`

### Changed
- `FileTreeKG.query()` — now performs semantic vector search first (LanceDB + embedder), with the lexical LIKE search as a graceful fallback when the vector index is missing or the embedder cannot load
- `pyproject.toml` — `lancedb>=0.29.0` and `pillow>=10.0.0` added as core dependencies (semantic search and EXIF are now first-class); `kg-snapshot` git dep removed in favour of `kg_utils.snapshots`; `kgmodule-utils` bumped to `>=0.2.1`; `kgdeps` extra now resolves `pycode-kg` and `doc-kg` from PyPI; `all` extra bumped to `pycode-kg>=0.17.0` and `doc-kg>=0.12.0`; `[tool.dockg].exclude` list trimmed (built-in skips no longer need to be enumerated); `black` removed (ruff handles formatting); `[tool.ruff.lint]` and `[tool.pytest.ini_options]` blocks added; pylint config switched to disable-all-then-enable to surface only the rules we care about
- `ftree_kg.snapshots` — imports `Snapshot`, `SnapshotManifest`, `SnapshotManager`, and `PruneResult` from `kg_utils.snapshots` (was `kg_snapshot.snapshots`); `import importlib.metadata` lifted to module top
- `cmd_status.py` — `datetime.timezone` import replaced with `datetime.UTC`
- `README.md` — rewritten in the pycode_kg / doc_kg style: Overview cross-links sister repos (PyCodeKG, DocKG, KGRAG), Features list expanded with EXIF/semantic-search/lexical-fallback bullets, Quick Start now demos `"iPhone photos from 2023"`, inline detail moved to the new `docs/CHEATSHEET.md`, `docs/CLI.md`, and `docs/pipeline.md`
- `.github/workflows/ci.yml` — `pytest` invocation now passes `-m "not integration"` so CI skips tests that require a real embedder / LanceDB

### Fixed
- mypy: `_embed_text(row: tuple)` annotated as `tuple[Any, ...]` to satisfy `type-arg`
- mypy: `extract_image_metadata` now skips EXIF tags whose id is missing from `PIL.ExifTags.TAGS` instead of falling back to the int id, so `_EXIF_FIELDS.get(tag_name)` always sees a `str`
- mypy: `tests/test_query.py` asserts `kg.db_path is not None` before passing it to `sqlite3.connect()`
- mypy: removed unused `# type: ignore[attr-defined]` on `from PIL.TiffImagePlugin import IFDRational` in `tests/test_metadata.py`
- pylint: `extract_image_metadata` outer `except Exception` annotated `# pylint: disable=broad-exception-caught`

### Removed
- `docs/ftreekg_packaging_fix.md` — stale packaging-fix note superseded by current `pyproject.toml` and `docs/CLI.md`

## [0.8.0] - 2026-04-29

### Added
- `ftreekg status` command — rich-formatted live display of graph node/edge counts, total indexed size, LanceDB presence, config (include/exclude dirs), and size-by-top-directory bar chart
- Dotdir auto-exclusion in `FileTreeKGExtractor` — directories whose names start with `.` are now skipped automatically unless explicitly listed in `include_dirs`; eliminates the need to enumerate `.git`, `.venv`, `.codekg`, `.pytest_cache`, etc. in `DEFAULT_SKIP_DIRS`

### Changed
- `DEFAULT_SKIP_DIRS` — simplified to non-dotdir names only; dotdirs now handled by the extractor's dotdir skip rule
- `.mcp.json` — corrected: stale `codekg` entry (wrong binary, wrong-case path) replaced with `pycodekg` (`poetry run pycodekg mcp`) and `dockg` (`poetry run dockg-mcp`)
- `.claude/commands/setup-mcp.md` — complete rewrite for FTreeKG: covers `ftreekg build`, `pycodekg build`, and `dockg build` with correct index dirs (`.filetreekg/`, `.pycodekg/`, `.dockg/`) and MCP server names
- `.claude/commands/release.md` — update CodeKG build step to use `pycodekg build --repo .`
- `.github/workflows/publish.yml` — add PyPI publish step using `PYPI_TOKEN` secret
- `poetry.lock` — resolves `kgmodule-utils` from PyPI (`>=0.2.0`) instead of git

## [0.7.0] - 2026-04-26

### Added
- `workflow_dispatch` trigger added to `.github/workflows/ci.yml` — enables manual CI runs from the GitHub Actions UI

### Changed
- `options.py`: default embedding model sourced from `kg_utils.embed.DEFAULT_MODEL` instead of hardcoded `"BAAI/bge-small-en-v1.5"` — stays in sync with `kg_utils` automatically
- `.pre-commit-config.yaml`: ruff hooks moved before pylint and given `exclude`, `pass_filenames: false`, and `always_run: true`; pylint now passes `--rcfile=pyproject.toml`; detect-secrets repositioned before local hooks
- `pytest.ini`: added `pythonpath = src` so tests resolve package imports without requiring an editable install

## [0.6.0] - 2026-04-24

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
