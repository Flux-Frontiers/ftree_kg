# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **`metadata.temporal_keys()` — the filesystem speaks the shared
  `kg_utils.temporal` contract, and it is where *occurred* and *recorded* come
  furthest apart.** A photograph taken on holiday in 1998 and copied onto this
  disk in 2024 occurred in 1998 and was recorded in 2024. A timeline that files
  it under 2024 is simply wrong about it, so FTreeKG now says both:
  `occurred_start` is the EXIF capture time where there is one, falling back to
  the modification time; `recorded_at` is always the modification time.

  The contract is merged into each file node's existing `metadata` blob
  alongside the format-specific fields, so nothing is displaced and the raw
  EXIF value is still there beside its normalised form.

  **EXIF datetimes needed converting, not just passing through.** EXIF writes
  `2024:01:15 10:30:00` — colon-separated in the date part, which
  `datetime.fromisoformat` rejects outright. Left alone, every photograph in a
  corpus would have failed to parse and dropped silently out of time-scoped
  queries, which is precisely the failure the contract exists to prevent.

  **Every file is dated, not only the ones with EXIF.** A tree where only
  photographs carry dates would answer "what changed in April" with
  photographs alone. This changes the metadata column for plain files from
  `NULL` to a temporal-only blob; `test_metadata_for_non_image_files_is_temporal_only`
  was updated from asserting `NULL` and now pins the new intent — temporal keys
  present, format-specific fields still absent.

  A malformed EXIF stamp falls back to the modification time rather than
  costing the file its date entirely.

### Fixed

- **The contract was written to disk and never handed to a caller.** Neither
  query path selected the `metadata` column — `_lexical_query` omitted it from
  its `SELECT` (it appeared only in the `WHERE`, for matching), and
  `_semantic_query` reads the vector store, which carries `_META_COLUMNS` and
  nothing else. So every filetree hit reached kg-rag's adapter undated, and any
  `QueryScope(time_range=...)` discarded the whole KG as having no dates.
  Storing the contract and surfacing it turn out to be two different jobs.

  Both paths now carry it: the lexical `SELECT` includes the column, and
  semantic hits come back to SQLite via `_attach_metadata()` rather than
  duplicating the blob into the vector index. `pack()` snippets carry it too,
  and `ftree_kg.adapter` forwards it onto its `CrossHit`s.

- **`build(wipe=False)` wiped.** The `DROP TABLE` statements lived inside the
  schema script, which ran on every build regardless of the flag, so an
  incremental build was indistinguishable from a full one and the parameter
  documented behaviour it had never had. Dropping is now conditional on `wipe`
  and the creates are `IF NOT EXISTS`.

- **`pack()` read the entire nodes table** to annotate at most `max_nodes` of
  them — a full scan of the tree per call, on a table with no indexes. Scoped
  to the nodes being rendered.

  Requires `kgmodule-utils>=0.18.0`; the floor moves with it.

## [0.13.2] - 2026-08-20

### Fixed

- **`--include-dir` matched a name at any depth, not just the top level, contradicting its own `--help` text ("Top-level directory names to include in indexing").** A nested directory that happened to share a name with an include entry pulled in its entire unrelated top-level parent. Building a fleet tree with `--include-dir proteusPy` also indexed `proteusPy_src/proteusPy/...` and `proteusPy_priv/paper/docs/proteusPy/...` -- neither is the fleet repo; each merely contains a subdirectory named `proteusPy` somewhere inside it. `exclude_dirs` and the dotdir rule are unchanged and still match at every depth, which is correct for them -- an excluded name should be excluded wherever it appears. `tests/test_build_scoping.py` adds coverage for the nested-collision case and for exclude staying any-depth.

## [0.13.1] - 2026-08-20

### Fixed

- **`ftreekg build` silently ignored `--include-dir` and `--exclude-dir`.**
  `cmd_build` parsed both flags, merged them with `[tool.filetreekg]`, echoed
  the merged sets to the terminal, and then built `FileTreeKG(repo_root=...,
  db_path=..., vectors_path=...)` without passing either one.
  `FileTreeKG.make_extractor()` re-read `pyproject.toml` unconditionally, so
  the flags could not reach the walk. Only the dotdir rule and
  `DEFAULT_SKIP_DIRS` narrowed anything.

  The failure is quiet and it looks like success: the build prints exactly the
  scope you asked for, then indexes something else. Building a 19-repo fleet
  tree over a directory of clones printed the right 19 names and produced
  314,935 file nodes spanning unrelated third-party checkouts -- `myML`
  (105,760 files), `python_packages` (85,260), `npsML` (67,846) -- plus the
  corpus directories the exclude list had named.

  `FileTreeKG.__init__` now takes `include_dirs` and `exclude_dirs`, and
  `make_extractor` prefers them. Either left as `None` still falls back to
  `pyproject.toml`, so the documented library behaviour is unchanged; an empty
  set now correctly means "no restriction" rather than "read the config".
  `tests/test_build_scoping.py` covers both the module API and the CLI wiring
  -- the CLI test is the one that would have caught this, since assertions made
  against the command's *output* passed throughout.

## [0.13.0] - 2026-08-15

### Added

- **An MCP server — `ftreekg-mcp` (`src/ftree_kg/mcp_server.py`).** FTreeKG was
  the only indexing KGModule in the fleet without one, so the filetree graph was
  unreachable from agents that reach PyCodeKG and DocKG over MCP. Four tools:
  `query_tree`, `pack_tree`, `graph_stats`, and `analyze_tree`, over stdio or
  SSE. `.mcp.json` now serves all three graphs.
- **`mcp>=1.0.0,<2` as a core dependency.** Upper-bounded for the same reason as
  doc-kg and pycode-kg: mcp 2.0 split `FastMCP` into a standalone package, and
  `mcp_server.py` imports it from `mcp` at module scope.

### Fixed

- **`SnippetPack.to_markdown()` raised `KeyError: 'id'` on FTreeKG packs.**
  Query nodes carried only the FTreeKG `node_id` spelling, but the `kg_utils`
  node contract (and every other fleet module) uses `id`. Both keys are now
  emitted, so existing consumers of `node_id` are unaffected. The CLI's `pack`
  renders via rich and never called `to_markdown()`, which is why this went
  unnoticed until the MCP server exercised it.
- **`snapshots.py`'s docstring named the wrong package.** It described itself as
  a thin layer over `kg_rag.snapshots`, but the module has imported
  `kg_utils.snapshots` for some time. Harmless at runtime, but it read as though
  a core module depended on the optional `[adapter]` extra — backwards, since
  `kg_rag` is imported only by `adapter.py`.

## [0.12.0] - 2026-08-15

The fleet dev-group migration, plus a currency sweep of the dependency floors.
As with 0.11.0, nothing under `src/` changes behaviour — but the published
metadata loses two extras, so this is a minor rather than a patch.

### Added

- **`[tool.poetry.group.dev]`, carrying the dev toolchain** — `detect-secrets`,
  `ty>=0.0.44`, `pre-commit`, `pylint`, `pytest>=9.0.3`, `pytest-cov`, and
  `ruff>=0.4.0,<0.16`. The group is `optional = true`, so a bare
  `poetry install` still gets the runtime only; `poetry install --with dev`
  is the new dev setup. This is the fleet rule from `FLEET_STANDARDS.md`:
  extras are user-facing features, optional Poetry groups are repo tooling.

### Changed

- **`kgmodule-utils` floor raised `>=0.9.0` → `>=0.13.2`.** The intermediate
  stops — 0.12.0 for the `viz3d.organic` growth engine, 0.12.1, then 0.13.2 —
  landed as separate fleet-sweep commits.
- **`kg-rag` floor (the `[adapter]` extra) raised `>=0.11.0` → `>=0.12.0`**, and
  the maintainer `kg` group's floors to `doc-kg>=0.21.2` and
  `pycode-kg>=0.23.1`.
- **CI installs dev tooling with `--with dev` instead of `--extras dev`** across
  the lint, typecheck, and test jobs, following the extras-to-group move.
- **`ruff-pre-commit` pinned to `v0.15.22`** (was `v0.9.10`), and the hook id
  renamed `ruff` → `ruff-check` to match. The `<0.16` cap in the dev group is
  what keeps the resolved ruff aligned with what the hook config declares —
  0.16 reformats Markdown.

### Removed

- **The `dev` and `all` extras.** `pip install "ftree-kg[dev]"` and
  `[all]` no longer resolve; the dev toolchain now lives in the Poetry group
  above and never ships in the wheel. `all` listed nothing *but* dev tools, so
  it advertised them as pip-installable regardless of where they actually
  lived — the same defect that survived the `doc_kg` and `Metabo_kg` group
  migrations. `adapter` is now the only feature extra.
- **`Last Revision:` header lines** from every module under `src/ftree_kg/` and
  from `pyproject.toml`. They were hand-maintained and had drifted; git records
  the same thing accurately.

### Fixed

- **`pytest` floor raised to `>=9.0.3`** for GHSA-6w46-j5rx-g56g.
- **Locked `cryptography` bumped 49.0.0 → 50.0.0** for the OSV.dev advisory
  against the pinned version. The existing `>=3.4.0` floor already permitted
  the fix, so this is a lockfile-only change.

## [0.11.0] - 2026-08-03

Dependency-declaration corrections. No changes under `src/` — but the package's
published metadata changes in both directions, which is why this is a minor
rather than a patch.

### Added

- **`[adapter]` extra, declaring `kg-rag`.** `src/ftree_kg/adapter.py` imports
  `kg_rag` at module scope, and `kg-rag` was declared nowhere. It worked only
  because anything that reached that module had kg-rag installed for other
  reasons; a bare `pip install ftree-kg` followed by
  `import ftree_kg.adapter` raised `ModuleNotFoundError`.

  It is an extra rather than a core dependency deliberately: kg-rag already
  depends on ftree-kg, so declaring it core would create a genuine resolution
  cycle.

- **`[tool.poetry.group.kg]`, carrying `doc-kg>=0.21.1` and
  `pycode-kg>=0.21.4`.** These are development tooling — the local pre-commit
  hook rebuilds both indices, `.mcp.json` serves both MCP servers, and
  `.claude/CLAUDE.md` documents `pycodekg build` / `dockg build` as the dev
  workflow. A Poetry group is locked and installable but is never written into
  wheel metadata, so contributors get the CLIs while consumers get nothing
  extra:

  ```bash
  poetry install --with kg
  ```

### Removed

- **The `kgdeps` extra, and `doc-kg` / `pycode-kg` from `[all]`.** Extras are
  published metadata, so `pip install ftree-kg[all]` was pulling two sibling KG
  packages into a consumer's environment for tooling they would never run — and
  putting the whole KG fleet into a single resolution graph. Neither package is
  imported anywhere under `src/`.

  Nothing depends on the removed extra: kg-rag requires bare `ftree-kg`, not
  `ftree-kg[kgdeps]`. Contributors who used it want `poetry install --with kg`.

## [0.10.1] - 2026-07-31

Packaging and documentation only — no changes under `src/`.

This release exists mainly to make the version number identify one artifact
again. **The 0.10.0 wheel published to PyPI was built from `main` after both
fixes below had merged, not from the `v0.10.0` tag**, so it carries the capped
`rich` constraint and the corrected DOI badges while the tag, the GitHub
Release assets, and the Zenodo deposit (record `21724586`) do not. Two distinct
artifacts therefore circulate as "0.10.0". PyPI does not permit re-uploading a
version, so 0.10.1 is the reconciliation: from here the tag, the PyPI wheel,
the Release assets, and the archived snapshot are the same thing again.
Functionally, anyone on PyPI 0.10.0 already has everything in this release.

### Fixed

- **The DOI badge and the citation text disagreed.** Both badges used the
  repo-id form `zenodo.org/badge/1182124358.svg`, which redirects to whichever
  *version* DOI is newest — so archiving v0.10.0 re-pointed them at
  `10.5281/zenodo.21724586` while the APA and BibTeX blocks two lines below
  still cited the concept DOI `10.5281/zenodo.19742541`. Both resolved, but the
  block showed two different numbers for the same work. Both badges are now
  pinned to the concept DOI, matching the citation text and `CITATION.cff`, and
  will not drift again on future releases.

- **`poetry.lock` was ambiguous about `rich`, so installs were not
  reproducible.** The lock carried two `rich` entries — 14.3.4 and 15.0.0 —
  both in the `main` group with no markers to tell them apart, and consecutive
  `poetry install --all-extras` runs genuinely settled on different versions.
  The cause was a missing ceiling: this package declared `rich>=13.0.0` while
  `doc-kg` (`<15.0.0`) and `pycode-kg` (`<15`) both cap it. Because those two
  live in the optional `kgdeps` extra, the resolver had two valid answers — 15.x
  without the extra, 14.x with it — and recorded both. Capping at `<15.0.0` to
  match the siblings collapses the lock to a single `rich` entry.

## [0.10.0] - 2026-07-31

No changes to FTreeKG's own API. The minor bump reflects the dependency floors:
installing the `semantic` extra now pulls transformers 5.x where it previously
resolved to 4.x.

### Security

- **Lifted the `kgmodule-utils` floor to `>=0.9.0`, clearing two high-severity
  `transformers` advisories.** kgmodule-utils 0.9.0 replaced its
  `transformers>=4.40.0,<4.57` cap with `>=5.5.0,<6`. The old cap held the stack
  at 4.56.2, which is exposed to a remote-code-execution advisory (fixed in
  transformers 5.3.0) and an arbitrary-code-execution flaw in the LightGlue
  model-loading path (fixed in 5.5.0). Because this package declares
  `kgmodule-utils[semantic,sqlite-vec]` as a core runtime dependency, every
  `ftree-kg` install inherited the capped — and vulnerable — transformers.

  **This forces a transformers 4.x → 5.x upgrade in existing environments.**
  Upstream verified embeddings are bitwise identical across the boundary on
  bge-small, bge-large, and nomic-embed, and that queries against a 4.x-built
  index return identical rankings — **no re-index is required**. The full FTreeKG
  suite, including the real-embedder semantic query tests, passes on
  transformers 5.14.1.

### Changed

- **Dependency floors raised for the `kgdeps` extra**: `doc-kg>=0.20.0` (was
  `>=0.18.1`) and `pycode-kg>=0.21.2` (was `>=0.20.0`). Both siblings dropped
  `lancedb` from their published wheels over this range, so the optional KG
  integration path no longer drags it in.
- `src/ftree_kg/__init__.py` now carries `__version__ = "0.10.0"`. It had been
  left at 0.9.0 and is exported from the package root, so library consumers
  reading `ftree_kg.__version__` saw a stale value. The CLI was unaffected — it
  reads `importlib.metadata.version("ftree-kg")`.

### Fixed

- **The citation DOI was dead.** The APA and BibTeX blocks both carried
  `10.5281/zenodo.1182124358`, which returns 404. That number is the GitHub
  repository id — correct inside the Zenodo badge URL, and pasted into the
  citation text as though it were a DOI. This repo is public, so anyone citing
  FTreeKG from the README got a dead link.

  Replaced with the **concept DOI** `10.5281/zenodo.19742541`, which resolves
  and tracks the latest deposit rather than pinning one snapshot. The badge is
  unchanged; its repo-id form is correct and resolves.

- **`CITATION.cff` had no `doi` field**, and its `date-released` was v0.6.0's
  date (2026-04-24) paired with version 0.9.0. Both corrected.

- **Four README links pointed at `Flux-Frontiers/FTreeKG`**, including the CI
  and Version badges. The repository is `ftree_kg`, which is what the git remote
  and `CITATION.cff` already record; the other name differs by more than case,
  so it depends on a rename redirect that badge endpoints are not a reliable
  place to lean on.

- **`ruff format --check .` rewrote prose documentation.** ruff 0.16 formats
  Python code blocks inside Markdown as stable behaviour where 0.15 gated it
  behind preview, so CI began failing on files unrelated to whatever change
  triggered the relock. Markdown is now excluded, matching doc_kg. Verified
  Python coverage is unaffected: ruff still formats and lints every `.py` file,
  and no `.md` reaches the formatter even with `--preview`.

## [0.9.0] - 2026-07-28

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
- `docs/SCHEMA.md` — complete schema reference moved out of the README: node kinds, edge types, node-ID format, full SQLite and LanceDB column tables, per-format EXIF field reference, the embed-text format with a worked iPhone-photo example, snapshots layout, KGRAG `kind` rationale, and schema versioning policy
- `docs/MCP.md` — MCP integration document explaining the local `.mcp.json` (PyCodeKG + DocKG sister-server wiring), why FTreeKG itself does not ship an MCP server in v0.8, the shape a future `ftreekg mcp` would take, and the KGRAG federation alternative available today
- Author / Last Revision / License headers added to every module under `src/ftree_kg/` and `src/ftree_kg/cli/`

### Changed
- **BREAKING: vector store migrated from LanceDB to sqlite-vec.** `FileTreeKG` now pins `vector_backend="sqlite-vec"` rather than inheriting `"auto"`, and declares `_default_dir = ".filetreekg"` so the base class derives its own paths. Vectors live in a single `.filetreekg/vectors.sqlite` file instead of a `.filetreekg/lancedb/` directory. **Migration: delete `.filetreekg/lancedb/` and run `ftreekg build` once** — the index rebuilds in seconds, there is no conversion step.
  - `FileTreeKG(repo_root, db_path, vectors_path)` — the `lancedb_path` parameter is renamed to `vectors_path` and now names a *file*.
  - CLI: `--lancedb` → **`--vectors`** on `build` / `query` / `pack` / `analyze` / `snapshot`.
  - The domain-specific embedding text (`_embed_text` — path-component tokens, basename splits, extension, EXIF prose) is **unchanged**; only the storage layer moved. `text` is carried as an extra sqlite-vec metadata column because `_semantic_query` surfaces it as each result's `docstring`.
  - `FileTreeKGAdapter` now reads `KGEntry.vectors_path`, tolerating `None` on registry entries written before the migration.
  - **Scores are unaffected, but the arithmetic changed.** The old LanceDB table was created without an explicit metric, so it returned *squared L2*; sqlite-vec returns *cosine*. For normalised embeddings squared-L2 = 2·(1 − cos), so the score formula moves from `1 - d/2` to `1 - d`. Verified against a same-day LanceDB control: identical ranking **and** identical scores across four real queries.
- **Dependency floors lifted to the currently published releases** — `kgmodule-utils>=0.8.0`, `doc-kg>=0.18.1`, `pycode-kg>=0.20.0`; lock regenerated. kgmodule-utils 0.8.0 defaults `vector_backend` to `"auto"`: sqlite-vec for fresh or already-migrated stores, LanceDB only when an un-migrated store already exists on disk, so existing corpora keep working untouched.
- `FileTreeKG.query()` — now performs semantic vector search first (LanceDB + embedder), with the lexical LIKE search as a graceful fallback when the vector index is missing or the embedder cannot load
- `pyproject.toml` — `lancedb>=0.29.0` and `pillow>=10.0.0` added as core dependencies (semantic search and EXIF are now first-class); `kg-snapshot` git dep removed in favour of `kg_utils.snapshots`; `kgmodule-utils` bumped to `>=0.8.0`; `kgdeps` extra now resolves `pycode-kg` and `doc-kg` from PyPI; `all` extra bumped to `pycode-kg>=0.17.0` and `doc-kg>=0.12.0`; `[tool.dockg].exclude` list trimmed (built-in skips no longer need to be enumerated); `black` removed (ruff handles formatting); `[tool.ruff.lint]` and `[tool.pytest.ini_options]` blocks added; pylint config switched to disable-all-then-enable to surface only the rules we care about
- `ftree_kg.snapshots` — imports `Snapshot`, `SnapshotManifest`, `SnapshotManager`, and `PruneResult` from `kg_utils.snapshots` (was `kg_snapshot.snapshots`); `import importlib.metadata` lifted to module top
- `cmd_status.py` — `datetime.timezone` import replaced with `datetime.UTC`
- `README.md` — rewritten as flowing narrative prose with a single "technical reading list" cross-referencing the five docs files; schema and MCP details split out into `docs/SCHEMA.md` and `docs/MCP.md` respectively; KGRAG-federation example updated to the new `kinds=["code", "doc", "filetree"]` form
- `.github/workflows/ci.yml` — `pytest` invocation now passes `-m "not integration"` so CI skips tests that require a real embedder / LanceDB
- **BREAKING:** `FileTreeKG.kind()` now returns `"filetree"` instead of `"meta"`, and `FileTreeKGAdapter` reports `KGKind.FILETREE` on every `CrossHit` / `CrossSnippet` (was `KGKind.META`); the `stats()` dict's `"kind"` value is also now `"filetree"`. The dedicated `KGKind.FILETREE` enum value already existed in `kg_rag.primitives` — using `META` was incorrect and would have collided with any future genuinely-meta KGModule. Any KGRAG registry entry, federation query (`kinds=[...]`), or assertion on the literal `"meta"` must be updated; `kgrag.query(q, kinds=["filetree"])` is the new spelling.
- `docs/CHEATSHEET.md`, `docs/pipeline.md`, `docs/guide.md` — KGRAG examples and prose updated for the `kind="filetree"` rename

### Fixed
- **`ImportError` on every entry point when installed from PyPI.** kgmodule-utils 0.8.0 split `kg_utils.types` into `kg_utils.specs` (NodeSpec/EdgeSpec) and `kg_utils.extractor` (KGExtractor), but `ftree_kg.extractor` and `ftree_kg.module` still imported the removed module, and the published 0.8.0 wheel declared only `kgmodule-utils>=0.2.4` — so a fresh install resolved kgmodule-utils 0.8.0 and every `ftreekg` command died with `ModuleNotFoundError: No module named 'kg_utils.types'`. Imports now target the new module paths and the floor is pinned at `kgmodule-utils>=0.8.0`. **Anyone on 0.8.0 from PyPI must upgrade to 0.9.0** — 0.8.0 is unusable against current kgmodule-utils.
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
