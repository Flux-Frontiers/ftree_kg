# Release Notes -- v0.18.1

> Released: 2026-11-02

FTreeKG 0.18.1 is a security release. FTreeKG reads image EXIF through
Pillow, and its range let a fresh install resolve Pillow 12.3.0 and its 41
advisories, some of them critical. Pillow 13.0.0 is now the floor. Nothing
about the graph, the tools or the index changes.

## What changed

**Pillow 13 is the floor.** The core dependency moves from `pillow>=10.0.0`
to `pillow>=13.0.0`, so the fix is in the package metadata and reaches every
pip install, not only this repo's lock.

**The lock is refreshed.** Pillow 13.0.0, certifi, filelock, setuptools and
virtualenv move to patched releases, which clears every open Dependabot
alert.

**The pipeline doc's dependency floors are current.** `docs/pipeline.md`
still listed kgmodule-utils 0.18.0, Pillow 10.0.0 and kg-rag 0.12.0; it now
matches `pyproject.toml`.

## Upgrading

`pip install -U ftree-kg`. pip moves Pillow to 13.x if needed. Existing
graphs stay valid.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
