# Release Notes — v0.9.0

> Released: 2026-07-28

FTreeKG 0.9.0 is a required upgrade. The 0.8.0 wheel on PyPI is broken against current
kgmodule-utils and fails at import time, so every `ftreekg` command in a fresh install
raises `ModuleNotFoundError`. This release fixes that, moves the vector store from LanceDB
to sqlite-vec, and adds per-format file metadata — including image EXIF — to both the graph
and the semantic index.

## What changed

**0.8.0 from PyPI is unusable — upgrade.** kgmodule-utils 0.8.0 split `kg_utils.types` into
`kg_utils.specs` and `kg_utils.extractor`. FTreeKG still imported the removed module, and
because the published 0.8.0 wheel declared only `kgmodule-utils>=0.2.4`, pip happily paired
it with a kgmodule-utils that no longer had the module it needed. The imports now target the
new paths and the dependency floor is pinned at `>=0.8.0`, so the pairing cannot recur. If
you are on 0.8.0, nothing works, and there is no workaround short of upgrading.

**The vector store is now sqlite-vec, and this one is breaking.** Vectors live in a single
`.filetreekg/vectors.sqlite` file rather than a `.filetreekg/lancedb/` directory. The
`lancedb_path` parameter is now `vectors_path` and names a file, and the `--lancedb` flag
becomes `--vectors` across `build`, `query`, `pack`, `analyze`, and `snapshot`. Scores are
unchanged, though the arithmetic behind them is not: LanceDB was returning squared L2 while
sqlite-vec returns cosine, so the score formula moved from `1 - d/2` to `1 - d`. Ranking and
scores were verified identical against a same-day LanceDB control across four real queries.

**Files now carry metadata, and search can see it.** A new per-format extractor reads image
EXIF via Pillow — camera make and model, lens, capture time, ISO, aperture, exposure, focal
length, and GPS decoded from DMS to decimal — and stores it as a JSON blob on each file node.
That metadata is projected into the text that gets embedded, so a query like "iPhone photos
from the beach" reaches the right files through the semantic index rather than through
filename matching. Audio, video, and PDF stubs are in place but not yet implemented.

**`kind()` returns `"filetree"`, not `"meta"`.** This is the second breaking change. Any
KGRAG registry entry, federation query, or assertion using the literal `"meta"` needs
updating; `kgrag.query(q, kinds=["filetree"])` is the new spelling. `KGKind.FILETREE` already
existed — using `META` was simply wrong, and would have collided with a genuinely meta-level
module later.

**Documentation was substantially expanded.** The schema reference moved out of the README
into `docs/SCHEMA.md`, joined by a CLI flag reference, a query cheatsheet, an architecture
and data-flow walkthrough, and a document explaining the MCP situation. The README is now
narrative prose pointing at those five.

## Upgrading

Install 0.9.0 — on 0.8.0 from PyPI, nothing runs at all.

If you have an existing index, delete `.filetreekg/lancedb/` and run `ftreekg build` once.
The index rebuilds in seconds and there is no conversion step. Replace any `--lancedb` flags
with `--vectors`, and any `lancedb_path=` argument with `vectors_path=` pointing at a file
rather than a directory. If you query FTreeKG through KGRAG, change `kinds=["meta"]` to
`kinds=["filetree"]`.

To pick up EXIF metadata on an existing corpus, rebuild — metadata is written during the
build pass and is not backfilled into an existing database.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
