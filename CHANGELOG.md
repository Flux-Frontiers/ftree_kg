# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial FileTreeKG scaffold with KGModule infrastructure
- FileTreeKGExtractor for filesystem traversal
- FileTreeKG module with build, query, pack, analyze operations
- FileTreeKGAdapter for KGRAG federation (meta kind)
- Comprehensive test suite for extractor and query operations
- Full CLI (`ftreekg`) with `build`, `query`, `pack`, `analyze`, and `snapshot` subcommands
- `src/config.py` — reads `[tool.filetreekg]` from `pyproject.toml` for `include`/`exclude` dir lists; ships `DEFAULT_SKIP_DIRS` applied at every walk depth
- `.claude/` tooling: agents, commands, plugins, and skills for Claude Code integration
- `examples/query_examples.py` — runnable usage examples
- `analysis/filetreekg_analysis.md` — architectural analysis report
- `.pre-commit-config.yaml` and `.secrets.baseline` for pre-commit quality gates

### Changed
- Restructured source tree: `filetreekg/` → `src/` and renamed package from `filetreekg` to `ftree-kg`
- `code-kg`, `doc-kg`, and `kg-rag` are now optional extras (`[code-kg]`, `[doc-kg]`, `[kgrag]`) instead of required/group dependencies
- `kg-rag` moved from a local path dev dependency to an optional git-sourced extra
- Tests relocated from `filetreekg/tests/` to `src/tests/`
- Added `[tool.filetreekg]` config section and pylint settings to `pyproject.toml`
- Updated `poetry.lock` to Poetry 2.3.2 format with revised optional-marker semantics

## [0.1.0] - 2026-03-15

### Added
- Initial release of FileTreeKG
