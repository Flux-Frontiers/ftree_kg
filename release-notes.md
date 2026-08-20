# Release Notes -- v0.13.1

> Released: 2026-08-20

A single-bug patch, but the bug was load-bearing: `ftreekg build` accepted
`--include-dir` and `--exclude-dir`, printed them back, and then ignored both.

## What changed

`cmd_build` parsed the flags, merged them with `[tool.filetreekg]`, echoed the
merged sets, and constructed `FileTreeKG` without passing either. The module's
`make_extractor()` then re-read `pyproject.toml` unconditionally. Nothing the
caller typed could reach the filesystem walk; only the dotdir rule and
`DEFAULT_SKIP_DIRS` narrowed it.

What makes this worth a release rather than a footnote is the shape of the
failure. It is quiet, and it looks like success -- the build reports exactly the
scope you asked for and then indexes something else entirely. Building a
19-repo fleet tree over a directory of clones printed the right 19 repository
names and wrote 314,935 file nodes, most of them from third-party checkouts
that were never in the include list: `myML` at 105,760 files, `python_packages`
at 85,260, `npsML` at 67,846. The corpus directories that the exclude list
named explicitly were indexed too.

## The fix

`FileTreeKG.__init__` now accepts `include_dirs` and `exclude_dirs`, and
`make_extractor` prefers them over the config file. Passing `None` -- the
default -- still falls back to `pyproject.toml`, so library callers relying on
the documented config behaviour see no change. The two states are now
distinguishable: `None` means "read the config", an empty set means "no
restriction". Collapsing them is what made the flags dead in the first place.

## Tests

`tests/test_build_scoping.py` adds six tests covering the module API, the
`pyproject.toml` fallback, the empty-set case, and the CLI wiring itself.

The CLI test is the one that matters. Every assertion made against the build
command's *output* passed while the bug was live, because the output was
correct -- it was the behaviour behind it that was not. The new test asserts on
what `FileTreeKG` actually receives.

## Upgrading

No API breaks. If you build with `--include-dir` or `--exclude-dir`, or with
`[tool.filetreekg]` include/exclude keys and a CLI override, rebuild your graph
after upgrading: any index built with 0.13.0 or earlier was scoped by the
dotdir rule and `DEFAULT_SKIP_DIRS` alone, whatever the build log claimed.
