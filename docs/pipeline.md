FTreeKG Pipeline - A Knowledge Graph for Filesystem Hierarchies

Version: 0.8.0
Author: Eric G. Suchanek, PhD

OVERVIEW

FTreeKG constructs a deterministic, queryable knowledge graph from a filesystem tree. It walks a directory, classifies every entry as a file, directory, or symlink, captures filesystem stat (size, mtime, mode, symlink target) and per-format metadata (image EXIF: camera, date, GPS, dimensions), persists the result to SQLite, and embeds canonical text per node into LanceDB for natural-language retrieval. Structure is treated as ground truth; semantic search is an acceleration layer. Every node maps to a concrete relative path under the repository root.

The system ships as: a Python library with a single FileTreeKG orchestrator, a Click-based CLI (ftreekg) with subcommands for build, query, pack, status, analyze, snapshot, and install-hooks, and a KGRAG adapter (FileTreeKGAdapter) that registers as kind="meta" alongside PyCodeKG (kind="code") and DocKG (kind="docs").

DESIGN PRINCIPLES

Structure is authoritative. Filesystem stat is authoritative. Per-format metadata accelerates semantic search but never invents structure. Every node has a stable, deterministic ID derived from kind and relative path. Indexing is idempotent. The vector index is derived and disposable; SQLite is canonical. Failures degrade gracefully - a corrupt image, a missing embedder, or an unreadable file does not abort the build.

LAYERED ARCHITECTURE

The system is organized into focused modules. FileTreeKG (orchestrator, module.py) owns the build, query, pack, stats, and analyze methods. FileTreeKGExtractor (extractor.py) walks the filesystem and yields NodeSpec/EdgeSpec objects. extract_metadata (metadata.py) is the per-format dispatcher that lifts image EXIF into a normalized dict. config.py loads include/exclude directory lists from pyproject.toml. snapshots.py provides SnapshotManager for temporal metric capture, listing, diffing, and pruning. FileTreeKGAdapter (adapter.py) bridges FTreeKG into KGRAG.

LAYER 1 - EXTRACTOR (extractor.py)

FileTreeKGExtractor subclasses kg_utils.types.KGExtractor. It walks the repository root with Path.rglob("*") and yields NodeSpec and EdgeSpec objects in a single pass. Node kinds: file, directory, symlink. Edge relations: CONTAINS (parent directory to child). For each path, it determines kind via path.is_symlink() / path.is_dir(), captures filesystem stat (size, mtime, mode, optional symlink target) into the docstring, and constructs a stable node ID of the form <kind>:<relative_path>:<basename>. CONTAINS edges link each parent directory to its immediate children. Coverage metric: fraction of meaningful nodes with non-empty docstrings.

Exclusion rules: paths containing any name from DEFAULT_SKIP_DIRS (venv, env, __pycache__, build, dist, egg-info, node_modules) or from the user-configured exclude list are dropped. Dotdirs (any path component starting with ".") are skipped unless explicitly listed in include_dirs. When include_dirs is non-empty, only paths whose components intersect that set are kept.

LAYER 2 - METADATA EXTRACTOR (metadata.py)

extract_metadata is a dispatcher that returns a normalized dict keyed by canonical names (camera_make, camera_model, lens, taken_at, description, artist, copyright, software, iso, f_number, exposure, focal_length, gps, dimensions). The image branch uses Pillow to open the file, read the EXIF block, decode the GPSInfo sub-IFD, and convert DMS coordinates to decimal degrees. Stubs for audio, video, and PDF return None. All extractors degrade gracefully: a missing optional library, a corrupt file, or an unsupported format yields None and never raises.

Two projection helpers consume the metadata dict. metadata_keywords(meta) flattens it into a list of lower-cased keyword tokens (camera_make, camera_model, year, year-month, description, gps:lat,lon) for the embed text. metadata_prose(meta) renders a multi-line "key: value" block for human-readable display in pack() output.

LAYER 3 - CONFIGURATION (config.py)

load_include_dirs(repo_root) and load_exclude_dirs(repo_root) read [tool.filetreekg].include and [tool.filetreekg].exclude lists from pyproject.toml. Both return set[str]; missing keys, missing files, invalid TOML, or non-list values yield empty sets. CLI flags (--include-dir, --exclude-dir) replace the config values when specified. DEFAULT_SKIP_DIRS is a hardcoded set of always-skipped non-dotdir names.

LAYER 4 - ORCHESTRATOR (module.py)

FileTreeKG subclasses kg_utils.types.KGModule. It owns the SQLite database path (default <repo>/.filetreekg/graph.sqlite) and the LanceDB directory path (default <repo>/.filetreekg/lancedb). The kind() method returns "meta", classifying it as structural metadata in the KGRAG taxonomy.

Methods: build(wipe=True, embed=True, metadata=True) for the full pipeline, stats() returning a dict with total_nodes, total_edges, node_counts, edge_counts, total_size_bytes, and size_by_top_dir, query(q, k=8) returning a QueryResult of ranked nodes, pack(q, k=8, max_nodes=15) returning a SnippetPack with per-node metadata blocks, analyze() returning a Markdown report, close() to release any resources.

LAYER 5 - SNAPSHOTS (snapshots.py)

SnapshotManager captures, lists, loads, diffs, and prunes temporal metric snapshots. Each snapshot is keyed by git tree hash (auto-detected via git write-tree on the staged index, or supplied via --tree-hash). Snapshot data includes: total_nodes, total_edges, total_files, total_dirs, node_counts, edge_counts, dir_node_counts (counts per top-level directory), branch, version, timestamp. Stored as one JSON file per tree hash under .filetreekg/snapshots/, with a manifest.json index.

prune_snapshots cleans three categories: metric-duplicates (interior snapshots whose metrics match neighbors), broken manifest entries (manifest references with missing JSON files), and orphan files (JSON files not referenced by the manifest). Oldest (baseline) and newest (latest) are always kept.

LAYER 6 - KGRAG ADAPTER (adapter.py)

FileTreeKGAdapter wraps FileTreeKG so it registers cleanly with the KGRAG federated retrieval system. kind="meta" distinguishes filesystem/structural metadata from kind="code" (PyCodeKG) and kind="docs" (DocKG). Federated queries via kgrag.query(q, kinds=["code","docs","meta"]) reach all three knowledge graphs simultaneously.

BUILD PIPELINE

Pass 1 - Filesystem walk and graph extraction. FileTreeKGExtractor.extract() walks the repository root, applies the include/exclude/dotdir rules, and yields NodeSpec / EdgeSpec objects. The orchestrator inserts each spec into the SQLite nodes / edges tables. Initial size_bytes is zero, metadata is NULL.

Pass 2 - Size collection. The orchestrator queries all file nodes from SQLite, calls path.stat() for each, and updates size_bytes via executemany. Failures (missing files, permission errors) silently set size to zero.

Pass 2.5 - Per-format metadata extraction. For each file node, extract_metadata is called with the absolute path. Results are JSON-serialized and stored in the metadata column. The dispatcher returns immediately for files outside the supported extension set, so the pass is cheap on non-image trees. Per-file failures are silently swallowed - one bad image cannot abort the build.

Pass 3 - Embedding. For every node (file, directory, symlink), the orchestrator builds a canonical text document of the form: "{kind} {basename} at {source_path}\nkeywords: {tokens}". Tokens include path components, the filename stem, the stem split on _/-/., the extension, and any metadata-projected keywords (camera_make, camera_model, year, year-month, description, gps coordinates). Texts are embedded in batches via kg_utils.embedder.get_embedder() (default model: BAAI/bge-small-en-v1.5, 384-dim) and written to LanceDB as a kg_nodes table with columns id, kind, name, qualname, module_path, text, vector. If the embedder or LanceDB is unavailable, the pass prints a warning to stderr and is skipped; SQLite remains complete and queries fall back to lexical matching.

QUERY PIPELINE

Phase 1 - Semantic seeding. FileTreeKG.query(q, k) embeds the query string via the same embedder used at build time, opens the kg_nodes LanceDB table, and runs a vector search limited to the top k hits. Each hit is converted into a node dict with id, kind, name, qualname, source_path, docstring, and a score derived from the LanceDB cosine distance (score = max(0, 1 - distance / 2)).

Phase 2 - Lexical fallback. When the LanceDB table is missing, empty, or the embedder fails to load, _lexical_query runs a substring LIKE match over qualname, kind, docstring, and metadata in SQLite. This guarantees query() always returns something useful, even on a freshly-extracted tree with no embeddings.

There is no graph expansion phase. Filesystem nodes have only one edge type (CONTAINS), which is purely structural and not semantically meaningful for hop-style retrieval. Results are returned as-is, ranked by vector score (or LIKE match order in the fallback path).

PACK PIPELINE

FileTreeKG.pack(q, k, max_nodes) reuses query() to obtain ranked nodes, then for each node assembles a per-node "snippet" - a metadata block of the form: kind: path, size: human-readable, docstring (filesystem stat), prose-rendered metadata (camera, taken_at, GPS, dimensions). Both SnippetPack.nodes and SnippetPack.snippets are populated; consumers of either work. There is no source-line extraction (filesystem nodes have no source body) and no overlapping-span deduplication.

ANALYZE PIPELINE

FileTreeKG.analyze() pulls stats() and the full nodes table, then renders a Markdown report containing: a summary table (total paths, links, files, directories, symlinks, total size); a size-by-top-level directory ASCII bar chart proportional to byte counts; an ASCII directory tree pretty-printed to depth ≤ 3 with at most 12 children per directory (truncation indicated as "… (N more)"); a path breakdown table (count by node kind); a link breakdown table (count by edge relation). The report is suitable for release notes, onboarding docs, or input to diagram generators.

STATUS DASHBOARD

ftreekg status renders a Rich-formatted terminal panel summarizing live graph state. It shows the package version, build timestamp from the SQLite mtime, DB path and size in MB, LanceDB presence (kg_nodes.lance file existence), include/exclude config, total nodes and edges with per-kind/per-relation breakdown tables side-by-side, total indexed file size, and a size-by-top-level directory bar chart. Exits 1 with a "run ftreekg build" hint when the graph is missing.

GIT HOOK

ftreekg install-hooks writes a pre-commit hook to .git/hooks/pre-commit. On every commit the hook captures the tree hash of the staged index via git write-tree, rebuilds the FTreeKG index, captures a metrics snapshot keyed by that tree hash, stages .filetreekg/snapshots/, then runs the pre-commit framework if installed (ruff, mypy, etc.). Skip with FTREEKG_SKIP_SNAPSHOT=1. The hook keeps the index and snapshot history atomically synchronized with committed source.

NODE ID FORMAT

Every node has a stable, deterministic ID: <kind>:<relative_path>:<basename>. Examples: file:src/ftree_kg/module.py:module.py, directory:src/ftree_kg:ftree_kg, symlink:bin/python:python. IDs reproduce across builds when the path and kind are unchanged.

EDGE FORMAT

Edges are minimal three-tuples: source_id, target_id, relation. The only relation in v0.8 is CONTAINS, emitted from each parent directory to each immediate child. The repository root itself is referenced as the synthetic node "directory:.:" when needed for top-level CONTAINS edges.

PER-NODE COLUMNS (SQLite)

The nodes table has columns: node_id (TEXT PRIMARY KEY), kind (file / directory / symlink), name (basename), qualname (relative path), source_path (same as qualname), docstring (filesystem stat as Markdown bullets), size_bytes (INTEGER), metadata (TEXT, JSON-serialized per-format dict or NULL).

PER-NODE COLUMNS (LanceDB)

The kg_nodes table has columns: id (matches node_id), kind, name, qualname, module_path (matches source_path), text (the embedded canonical document), vector (384-dim embedding).

DATA FLOW

repository root
to FileTreeKGExtractor.extract() walking the tree, applying include/exclude/dotdir rules, yielding NodeSpec/EdgeSpec
to SQLite nodes and edges tables (Pass 1 via INSERT OR REPLACE)
to size_bytes population by re-statting each file (Pass 2 via UPDATE executemany)
to per-format metadata extraction via extract_metadata, JSON-serialized into the metadata column (Pass 2.5)
to canonical embed-text construction per node (kind + basename + path components + extension + metadata keywords)
to kg_utils.embedder.get_embedder().embed_texts() producing 384-dim vectors
to LanceDB kg_nodes table (Pass 3, derived and disposable)
to FileTreeKG.query() embedding the query, vector-searching kg_nodes, ranking by cosine distance
or to FileTreeKG._lexical_query() running substring LIKE over qualname/kind/docstring/metadata when LanceDB is unavailable
to QueryResult ranked node list
to FileTreeKG.pack() producing per-node metadata blocks (kind + path + size + docstring + prose-rendered metadata)
or to FileTreeKG.analyze() producing a Markdown report (summary, size chart, directory tree, breakdowns)
or to ftreekg status rendering a Rich terminal dashboard
or to FileTreeKGAdapter exposing FTreeKG to KGRAG as kind="meta" alongside PyCodeKG (code) and DocKG (docs)

CLI ENTRY POINTS

Primary interface: ftreekg (the main Click CLI). Five subcommands also ship as standalone script aliases.

ftreekg build (alias: ftreekg-build): full pipeline (filesystem walk + SQLite + metadata + LanceDB), wipes by default.
ftreekg query (alias: ftreekg-query): semantic query, formatted text output.
ftreekg pack (alias: ftreekg-pack): metadata snippet pack.
ftreekg analyze (alias: ftreekg-analyze): Markdown analysis report.
ftreekg snapshot (alias: ftreekg-snapshot): save / list / show / diff / prune temporal snapshots.
ftreekg status: live Rich dashboard (no script alias).
ftreekg install-hooks: install the pre-commit auto-snapshot hook (no script alias).

All subcommands live in src/ftree_kg/cli/. Shared options (repo, db, lancedb, model, k, include-dir, exclude-dir) live in cli/options.py; the root Click group is defined in cli/group.py.

INTERFACES

CLI: ftreekg + the five script aliases above.

Python API: from ftree_kg import FileTreeKG; kg = FileTreeKG(repo_root); kg.build(); kg.query(q); kg.pack(q); kg.stats(); kg.analyze().

KGRAG: FileTreeKGAdapter registers as kind="meta". Federated queries via kgrag.query(q, kinds=["code","docs","meta"]) include FTreeKG results alongside PyCodeKG and DocKG.

DEPENDENCIES

Core (required): click 8.1.0+, kgmodule-utils 0.2.1+, lancedb 0.29.0+, pillow 10.0.0+, rich 13.0.0+. Embedding model retrieval is brokered by kg_utils.embedder.get_embedder() (default: BAAI/bge-small-en-v1.5 from sentence-transformers).

Optional kgdeps extra: doc-kg 0.11.0+ and pycode-kg 0.16.0+ for KGRAG cross-graph integration.

Python 3.12 to 3.13 (exclusive of 3.14).

SOURCE LAYOUT

src/ftree_kg/: __init__.py (re-exports FileTreeKG), module.py (FileTreeKG orchestrator, _embed_text, _ascii_tree, _fmt_size, _size_bar), extractor.py (FileTreeKGExtractor), metadata.py (extract_metadata, extract_image_metadata, metadata_keywords, metadata_prose), config.py (DEFAULT_SKIP_DIRS, load_include_dirs, load_exclude_dirs), snapshots.py (SnapshotManager, SnapshotMetrics, SnapshotDelta), adapter.py (FileTreeKGAdapter for KGRAG), cli/ (Click CLI: group.py, options.py, cmd_build.py, cmd_query.py, cmd_analyze.py, cmd_status.py, cmd_snapshot.py, cmd_hooks.py, main.py).

tests/: test suite for extractor, module, metadata, config, snapshots, and adapter.

docs/: README.md (project overview), CHEATSHEET.md (query patterns and recipes), CLI.md (full flag reference), pipeline.md (this file - architecture and data flow), guide.md (Python API guide).

DIAGRAM HINTS

For a single-image architecture diagram, the canonical layout is left-to-right:

1. Source: the filesystem tree (left edge).
2. Extractor: the first vertical band - walks the tree, classifies entries (file / directory / symlink), captures stat, applies include/exclude/dotdir rules.
3. Per-format metadata: a small parallel band feeding off the file branch - Pillow EXIF for images, with stubs for audio/video/PDF.
4. SQLite (canonical store): center band labeled .filetreekg/graph.sqlite with two tables (nodes, edges). This is authoritative.
5. LanceDB (derived index): adjacent to SQLite, labeled .filetreekg/lancedb/kg_nodes.lance, with an arrow from SQLite indicating "embedded canonical text + metadata keywords".
6. Query path: right-side band branching into ftreekg query, ftreekg pack, ftreekg analyze, ftreekg status, and the KGRAG adapter (kind="meta"). Snapshots are a small loop hanging off SQLite.
7. Time axis: snapshots over commits, captured by the pre-commit hook, keyed by git tree hash.

Color coding: filesystem in green, extractor in blue, metadata extractor in purple (a sub-color of blue), SQLite in orange (canonical), LanceDB in yellow (derived), CLI/API consumers in gray. Arrows from SQLite to LanceDB should be dashed (derived/disposable). Arrows into KGRAG should be a different style (federation). The whole pipeline reads left-to-right with the consumers fanning out on the right.
