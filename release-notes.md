# Release Notes — v0.10.1

> Released: 2026-07-31

A packaging and documentation patch. Nothing under `src/` changed, and if you installed
FTreeKG 0.10.0 from PyPI you already have everything here — the point of this release is to
make the version number identify a single artifact again.

## What changed

**0.10.0 shipped as two different artifacts, and this fixes that.** The wheel published to
PyPI was built from `main` after the two fixes below had already merged, rather than from the
`v0.10.0` tag. So the PyPI wheel carries the capped `rich` constraint and the corrected DOI
badges, while the git tag, the GitHub Release assets, and the Zenodo deposit do not. Both are
labelled 0.10.0. PyPI does not allow re-uploading a version, so 0.10.1 is the reconciliation:
from here the tag, the published wheel, the Release assets, and the archived snapshot all
describe the same thing. This matters more than usual for a package that carries a DOI — a
citation should resolve to what people actually install.

**`rich` is capped at `<15`, which makes the lock reproducible.** `poetry.lock` had been
carrying two `rich` entries — 14.3.4 and 15.0.0 — in the same group with no markers to tell
them apart, and consecutive installs genuinely settled on different versions. The cause was a
missing ceiling rather than a stale floor: FTreeKG declared `rich>=13.0.0` with no upper
bound, while `doc-kg` and `pycode-kg` both cap it below 15. Because those two live in the
optional `kgdeps` extra, the resolver had two legitimate answers and recorded both. Matching
the siblings' cap leaves exactly one.

**The citation block no longer contradicts itself.** Both DOI badges used the repo-id form,
which redirects to whichever *version* DOI is newest — so archiving 0.10.0 silently re-pointed
them at `10.5281/zenodo.21724586` while the APA and BibTeX text two lines below still cited
the concept DOI `10.5281/zenodo.19742541`. Both resolved, but a reader saw two different
numbers for the same work. The badges are now pinned to the concept DOI, which already tracks
the latest deposit, so they will not drift again.

## Upgrading

`pip install --upgrade ftree-kg`. No migration, no re-index, no API change.

If you are already on PyPI 0.10.0, upgrading changes nothing functionally — the dependency
metadata and README you have are already the ones in this release.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
