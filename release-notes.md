# Release Notes -- v0.14.0

> Released: 2026-08-22

FTreeKG now speaks the shared `kg_utils.temporal` contract, giving every
node both an *occurred* and a *recorded* date -- and a follow-on audit of
why that contract wasn't reaching queries turned up four defects in the
query and build paths, all fixed here.

## What changed

**Files finally know when something happened, not just when it was
touched.** A photograph taken on holiday in 1998 and copied onto disk in
2024 occurred in 1998 and was recorded in 2024; filing it under 2024 alone
is wrong. Every file node now carries `occurred_start` (EXIF capture time,
falling back to mtime) and `recorded_at` (always mtime), merged into the
existing `metadata` blob alongside format-specific fields. EXIF's
colon-separated date format is converted rather than passed through raw --
left alone it would have failed `datetime.fromisoformat` and silently
dropped every photograph out of time-scoped queries, which is exactly the
failure this contract exists to prevent. A malformed EXIF stamp falls back
to the modification time instead of costing the file its date entirely.

**The contract was being written but never handed to a caller.** Neither
query path actually selected the `metadata` column -- the lexical query
used it only in the `WHERE` clause for matching, and the semantic query
reads the vector store, which never carried it at all. Every filetree hit
reached kg-rag's adapter undated, so a `time_range` scope discarded the
whole KG. Both paths now carry metadata through: the lexical `SELECT`
includes the column, and semantic hits are re-attached to it from SQLite.
`pack()` snippets carry it too.

**`build(wipe=False)` wiped anyway.** The `DROP TABLE` statements lived in
the schema script and ran unconditionally, so an incremental build was
indistinguishable from a full rebuild. Once that was fixed, a second
defect went live: the `edges` table had no primary key and used a bare
`INSERT`, so preserved rows meant duplicated edges across successive
incremental builds -- 3, then 6, then 9. `edges` now carries a composite
primary key and inserts use `INSERT OR REPLACE`; an existing database
built with `wipe=False` should be wiped once to clear any duplicates
already written.

**Performance and coverage tightened up in the same pass.** `pack()` used
to read the entire nodes table just to annotate the handful it renders;
it's now scoped to the nodes actually being packed. The graph itself
carried zero indexes -- every query, `stats()` call, and `pack()` lookup
was a full table scan -- so `nodes(kind)`, `nodes(name)`,
`nodes(source_path)`, and all three `edges` columns are now indexed.

## Upgrading

No API breaks. The indexing change requires `kgmodule-utils>=0.18.0`, and
`pyproject.toml`/`poetry.lock` already reflect that floor. If you've been
running incremental builds (`wipe=False`) against an existing database,
wipe it once to clear any duplicate edges written before this release.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
