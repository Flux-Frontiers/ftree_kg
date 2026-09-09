# Release Notes -- v0.16.0

> Released: 2026-09-08

FTreeKG's snapshot module now leans on the shared `SnapshotManager` for the
work it used to duplicate, and the tooling pins that had fallen several
releases behind are caught up.

## What changed

**`snapshots.py` no longer overrides `capture()` or `diff_snapshots()`.**
Both overrides existed only to bend the shared manager around this module's
two filesystem-specific metrics. `kgmodule-utils` 0.20.0 supplies extension
points that make them unnecessary: a `_domain_metrics(stats)` hook derives
`total_files` and `total_dirs` from the node counts and collects the
per-directory counts from SQLite, and a `dict_metric_deltas` class attribute
names `dir_node_counts` so the base emits `dir_node_counts_delta` containing
only the directories whose count changed. The module shrinks from about 400
lines to about 290, and the delta logic is now the same code every other KG
module runs. The `__init__` override stays, because it is the one in the
fleet with a real job: it probes `importlib.metadata` for the installed
version and falls back from `ftree-kg` to the legacy `filetreekg` name.

**The floor on `kgmodule-utils` is now a hard `>=0.20.0`.** Against 0.19.x
the manager has no `_domain_metrics` hook, so `total_files`, `total_dirs`
and `dir_node_counts` would silently vanish from every new snapshot. The
lock already resolves 0.20.0; the pin makes it a requirement rather than a
coincidence.

**`capture(stats_dict=...)` is deprecated.** It was this repo's private alias
for `graph_stats_dict` and lived on the removed `capture()` override. It
still routes correctly, and now raises a `DeprecationWarning`, declared
through the base's `capture_aliases`. That declaration matters: the base
signature ends in `**extra_metrics`, so without it an old caller's
`stats_dict` would have been quietly recorded as a metric of that name while
the real graph stats went missing.

**The `doc-kg` and `pycode-kg` tooling pins were four and five releases
behind.** They now floor on doc-kg 0.26.0 and pycode-kg 0.27.0, the releases
in which those packages retired their own snapshot overrides, so
`poetry install --with kg` cannot resolve a dockg or pycodekg that predates
the shared extension points into an environment that depends on them. The
`kg-rag` floor is unchanged; it has not taken this SDK bump yet.

## Upgrading

Nothing to rebuild. `poetry install` picks up the `kgmodule-utils` floor. If
any of your code calls `capture(stats_dict=...)`, rename the argument to
`graph_stats_dict`; the old name keeps working for now but warns. Existing
snapshots are unaffected, and new ones carry the same fields as before.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
