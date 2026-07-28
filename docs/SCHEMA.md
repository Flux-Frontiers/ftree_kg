# FTreeKG Knowledge Graph Schema

The complete reference for nodes, edges, identifiers, and the on-disk
storage layout. For day-to-day query recipes see
[CHEATSHEET.md](CHEATSHEET.md); for the build pipeline that produces this
schema see [pipeline.md](pipeline.md).

---

## Design summary

FTreeKG models a filesystem as a typed, directed graph. Every entry on disk
becomes a single node carrying its identifying path, kind, and the cheap
filesystem stat already exposed by the OS. The structural skeleton is
captured by a single edge type that mirrors the parent-child relationship
in the directory tree. A second axis — **per-format metadata** — sits
alongside the structural data, lifting things like image EXIF into a
JSON blob so semantic search can hit content the path alone never reveals.

The SQLite database (`graph.sqlite`) is **canonical** and self-contained.
The sqlite-vec store (`vectors.sqlite`) is a **derived, disposable** vector
index built from the SQLite rows; deleting it and re-running `ftreekg
build` reproduces it byte-equivalent up to embedder noise.

---

## Node kinds

There are exactly three node kinds in v0.9 — one per filesystem
classification rule (`Path.is_symlink()` → `Path.is_dir()` → file).

| Kind        | Description                              | Notes                                                          |
|-------------|------------------------------------------|----------------------------------------------------------------|
| `file`      | A regular file                           | `size_bytes` populated; per-format `metadata` may be present   |
| `directory` | A directory                              | `size_bytes = 0`; the synthetic root is `directory:.:`         |
| `symlink`   | A symbolic link                          | Target stored in `docstring`; not followed during the walk     |

A fourth kind — `module` — is reserved in `FileTreeKGExtractor.node_kinds()`
for future logical groupings but is not emitted today.

---

## Edge types

| Relation   | Direction              | Meaning                                              |
|------------|------------------------|------------------------------------------------------|
| `CONTAINS` | parent → immediate child | Directory contains the file/dir/symlink directly under it |

Only one relation is emitted in v0.9. There is deliberately no `CHILD_OF`
or `PARENT_OF` — the inverse is recoverable from `CONTAINS` with a
single SQL flip, and storing it explicitly would double the edge table
without adding information.

---

## Node ID format

Every node has a stable, deterministic identifier:

```
<kind>:<relative_path>:<basename>
```

### Examples

| Path on disk                       | Node ID                                             |
|------------------------------------|-----------------------------------------------------|
| `src/ftree_kg/module.py`           | `file:src/ftree_kg/module.py:module.py`             |
| `src/ftree_kg`                     | `directory:src/ftree_kg:ftree_kg`                   |
| `bin/python` (symlink)             | `symlink:bin/python:python`                         |
| repository root                    | `directory:.:` (synthetic; only used as edge source)|

IDs reproduce across builds: same path + same kind = same ID. Renaming
or moving a file changes the ID; modifying the file's contents does not.

---

## SQLite layout

The on-disk store is a single file at
`<repo>/.filetreekg/graph.sqlite` (overridable with `--db`). Two tables
hold everything:

### `nodes`

| Column        | Type    | Description                                                             |
|---------------|---------|-------------------------------------------------------------------------|
| `node_id`     | TEXT PK | Stable ID (see format above)                                            |
| `kind`        | TEXT    | `file`, `directory`, or `symlink`                                       |
| `name`        | TEXT    | Basename (e.g. `module.py`)                                             |
| `qualname`    | TEXT    | Repo-relative path (e.g. `src/ftree_kg/module.py`)                      |
| `source_path` | TEXT    | Same as `qualname` in v0.9 (kept distinct for KGModule API parity)      |
| `docstring`   | TEXT    | Filesystem stat as Markdown bullets — size, mtime, mode, symlink target |
| `size_bytes`  | INTEGER | File size in bytes; `0` for directories and symlinks                    |
| `metadata`    | TEXT    | JSON blob from per-format extraction, or `NULL`                         |

The `docstring` column is human-readable; representative content for a
file:

```
**Size:** 2812 bytes
**Modified:** 2026-04-30T23:41:26
**Mode:** -rw-r--r--
```

### `edges`

| Column      | Type | Description                                  |
|-------------|------|----------------------------------------------|
| `source_id` | TEXT | Parent node ID                                |
| `target_id` | TEXT | Child node ID                                 |
| `relation`  | TEXT | Always `CONTAINS` in v0.9                    |

Edges are emitted in a single pass with no uniqueness constraint — the
extractor produces one row per (parent, child) pair and never revisits
the same path twice during a build.

---

## Per-format metadata

Pass 2.5 of the build runs `extract_metadata(path)` for every file node.
The dispatcher returns a normalized `dict[str, Any]` keyed by canonical
field names; the dict is JSON-serialized and stored verbatim in
`nodes.metadata`. Both the `pack` command and the lexical fallback in
`query` read this column.

### Image EXIF (implemented)

Triggered for extensions in `IMAGE_EXTS`: `.jpg`, `.jpeg`, `.tiff`,
`.tif`, `.png`, `.webp`, `.heic`, `.heif`. Pillow opens the file and
reads the EXIF block plus the GPSInfo sub-IFD.

| Canonical key   | EXIF source              | Notes                                            |
|-----------------|--------------------------|--------------------------------------------------|
| `dimensions`    | image size               | `"WIDTHxHEIGHT"` string (always present on success) |
| `camera_make`   | `Make`                   |                                                  |
| `camera_model`  | `Model`                  |                                                  |
| `lens`          | `LensModel`              |                                                  |
| `taken_at`      | `DateTimeOriginal` / `DateTime` | `DateTimeOriginal` preferred                     |
| `description`   | `ImageDescription`       |                                                  |
| `artist`        | `Artist`                 |                                                  |
| `copyright`     | `Copyright`              |                                                  |
| `software`      | `Software`               |                                                  |
| `iso`           | `ISOSpeedRatings`        |                                                  |
| `f_number`      | `FNumber`                | Decimal string (e.g. `"2.8"`)                    |
| `exposure`      | `ExposureTime`           |                                                  |
| `focal_length`  | `FocalLength`            |                                                  |
| `gps`           | `GPSLatitude` + `GPSLongitude` (DMS, decoded) | `{"lat": float, "lon": float}` |

GPS conversion: degrees/minutes/seconds rationals are converted to
decimal via `_dms_to_decimal`; the `GPSLatitudeRef`/`GPSLongitudeRef`
fields negate the result for `S`/`W`.

### Reserved (stubs)

`AUDIO_EXTS` (`.mp3 .flac .ogg .m4a .wav`), `VIDEO_EXTS`
(`.mp4 .mov .mkv .avi .webm`), and `PDF_EXTS` (`.pdf`) are recognised by
the dispatcher but the extractor returns `None` today. The hooks are in
place — wiring them to mutagen / ffprobe / pypdf is a future change
that won't alter the schema.

---

## sqlite-vec layout

The vector index lives at `<repo>/.filetreekg/vectors.sqlite` (overridable
with `--vectors`) — a single SQLite file, not a directory. It holds two
tables the module reads directly, plus sqlite-vec's own shadow tables.

### `vec_meta`

Per-node metadata, keyed 1:1 against the canonical graph.

| Column        | Type   | Description                                   |
|---------------|--------|-----------------------------------------------|
| `id`          | TEXT   | Primary key; matches `nodes.node_id` 1:1      |
| `kind`        | TEXT   | Mirror of `nodes.kind`                        |
| `name`        | TEXT   | Mirror of `nodes.name`                        |
| `qualname`    | TEXT   | Mirror of `nodes.qualname`                    |
| `module_path` | TEXT   | Mirror of `nodes.source_path`                 |
| `text`        | TEXT   | The canonical embed-text document (see below) |

`text` is carried beyond the `kg_utils` default column set on purpose:
`_semantic_query` surfaces it as each result's `docstring`. A filesystem
node has no real docstring, so this embedded locator line is what callers
see — dropping the column blanks the query output.

### `vec_nodes`

```sql
CREATE VIRTUAL TABLE vec_nodes USING vec0(embedding float[384] distance_metric=cosine);
```

The embedding is produced by `kg_utils.embedder.get_embedder()` (default
D = 384, `BAAI/bge-small-en-v1.5`). The metric is **cosine**, so
`query()` derives its score as `1 - distance`. The pre-0.8.0 LanceDB
table was created without an explicit metric and so defaulted to squared
L2, which needed `1 - distance / 2`; for normalised embeddings the two
formulas agree exactly.

### Embed-text format

Two lines, deterministic for the same input:

```
{kind} {basename} at {source_path}
keywords: {tokens}
```

`tokens` is a deduplicated, space-joined sequence built from:

1. Every path component (so `src/ftree_kg/cli/cmd_build.py` contributes
   `src ftree_kg cli cmd_build`)
2. The basename stem (`cmd_build`)
3. The stem split on `_`/`-`/`.` (`cmd build`)
4. The extension as its own token (`py`)
5. Per-format metadata projection from `metadata_keywords(meta)` —
   camera make/model, year, year-month, description, GPS coordinates

Worked example for `photos/IMG_0042.jpg` with EXIF showing an iPhone 14
Pro photo from 2023-07-15 at GPS 37.77, -122.42:

```
file IMG_0042.jpg at photos/IMG_0042.jpg
keywords: photos img_0042 img 0042 jpg apple iphone 14 pro 2023 2023-07 gps:37.7749,-122.4194
```

That single line is what makes `"iPhone photos from 2023"` retrieve the
node even though neither the path nor the basename mentions any of
those terms.

---

## Snapshots layout

`<repo>/.filetreekg/snapshots/` holds JSON-serialized graph metric
snapshots, indexed by a manifest file:

```
.filetreekg/snapshots/
  manifest.json          # tree-hash → metadata index
  <tree-hash>.json       # one file per snapshot
  <tree-hash>.json
  ...
```

Each snapshot file carries: `key` (tree hash), `branch`, `version`,
`timestamp`, `metrics` (total nodes/edges/files/dirs, node and edge
counts by kind/relation, dir-node counts per top-level directory), and
optional `vs_previous` / `vs_baseline` deltas. See `SnapshotManager` in
`src/ftree_kg/snapshots.py` for the full Pydantic-style structure.

---

## KGRAG kind

`FileTreeKG.kind()` returns `"filetree"` (the `KGKind.FILETREE` enum
value defined in `kg_rag.primitives`). This places FTreeKG alongside
other purpose-built kinds — `code` (PyCodeKG), `doc` (DocKG), `diary`,
`memory`, `agent`, `verse`, `disulfide`, `pdbfile`, `legal`, `person` —
rather than sharing the catch-all `meta` slot.

`FileTreeKGAdapter` reports `KGKind.FILETREE` on every `CrossHit` and
`CrossSnippet` it returns to KGRAG, so federated queries can target
filesystem context specifically:

```python
result = kgrag.query("how do we ship releases", kinds=["code", "doc", "filetree"])
```

---

## Versioning

The schema is at v0.9 and is **not yet stable**. Breaking changes will
bump the minor version and be called out in
[CHANGELOG.md](../CHANGELOG.md). The two axes most likely to grow:

- **Edge types** — a future `LINKS_TO` for symlink targets that resolve
  inside the indexed tree, and a `RESOLVES_TO` for cross-tree references
  if/when the extractor walks multiple roots.
- **Per-format metadata** — audio/video/PDF extractors will be wired
  into the existing dispatcher, contributing new canonical keys without
  changing the table layout.

The node ID format and the SQLite column set are considered stable
within v0.x.
