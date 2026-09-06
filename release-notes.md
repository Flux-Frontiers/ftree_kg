# Release Notes — v0.15.0

> Released: 2026-09-06

FTreeKG finally receives the fleet's snapshot key fix, and drops a layer of
hand-rolled type conversion that had been standing in the way of it.

## What changed

**Snapshots are keyed on a release tag or timestamp, not a git tree hash —
for real, this time.** The floor on `kgmodule-utils` had read `>=0.19.0`
since the fleet's key-scheme change, but the lock was still resolving
0.18.0, so this repo never actually received the fix even though it was
believed to have inherited it for free. A tree hash is read before `git
add` stages the snapshot, so it names a tree that is never committed and
cannot be resolved afterward — the root cause behind only 63 of 605 fleet
snapshot keys ever resolving. With the floor now genuinely enforced,
`ftreekg snapshot save VERSION` keys the snapshot on VERSION, which the
command accepted and silently ignored before. A new `--subject` option
records what was measured (`repo:ftree-kg`, or a tree path for a non-repo
corpus), separate from the version, which names the measuring tool.

**The hydrate/dehydrate layer is gone.** FTreeKG used to overwrite a
snapshot's `metrics`, `vs_previous`, and `vs_baseline` with typed dataclass
instances after every load and convert them back before every save, so
that callers could use attribute access. That forced overrides of
`load_snapshot`, `save_snapshot`, and `diff_snapshots` that had nothing to
do with filesystem trees — the same shape of problem that, in three
sibling repos, hid a real bug where the snapshot key silently got dropped
on save. A snapshot's structured fields are now plain dicts, matching
every other KG module; `SnapshotMetrics` and `SnapshotDelta` remain
available as converters for code that wants attribute access.

## Upgrading

Existing snapshots keyed on a tree hash stay addressable by that key — the
manifest loader reads both shapes. New snapshots from a release should
pass the tag explicitly: `ftreekg snapshot save 0.15.0 --subject
repo:ftree-kg`. If your code accessed `snapshot.metrics.total_nodes` as an
attribute, switch to `snapshot.metrics["total_nodes"]` or convert with
`metrics_from_dict(snapshot.metrics)`.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
