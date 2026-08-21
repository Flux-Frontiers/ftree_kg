# Release Notes -- v0.13.2

> Released: 2026-08-20

A follow-on patch to yesterday's fix: `--include-dir` now matches only the
top-level directory name it documents, not any path component at any depth.

## What changed

v0.13.1 made `--include-dir` and `--exclude-dir` actually reach the
filesystem walk, but the include check itself matched a name against every
path component, not just the top one -- contradicting its own `--help` text,
which promises "top-level directory names to include in indexing." A nested
directory that happened to share a name with an include entry pulled in its
entire unrelated top-level parent.

This surfaced immediately when building the fleet tree with `--include-dir
proteusPy`: the index also picked up `proteusPy_src/proteusPy/...` and
`proteusPy_priv/paper/docs/proteusPy/...`. Neither is the actual `proteusPy`
repo -- both are unrelated top-level directories that each happen to contain
a subdirectory named `proteusPy` somewhere inside.

## The fix

The include check now looks only at the first path component: a path is kept
when its top-level directory is in `include_dirs`, full stop. `exclude_dirs`
and the dotdir rule are unchanged and still match at any depth, which is the
correct behavior for them -- an excluded name should be excluded wherever it
appears, but an included name should not pull in an unrelated tree just
because a same-named subdirectory happens to live inside it somewhere.

## Tests

`tests/test_build_scoping.py` adds coverage for the nested-name-collision
case and for exclude staying any-depth. Full suite: 87 passed.

## Upgrading

No API breaks. If you use `--include-dir`, rebuild your graph: an index built
with v0.13.1 may have pulled in unrelated directories that merely contained a
same-named subdirectory.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
