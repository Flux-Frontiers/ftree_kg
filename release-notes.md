# Release Notes — v0.12.0

> Released: 2026-08-15

Nothing under `src/` changed behaviour. As in 0.11.0, what changed is the
package's declared dependencies — this time by moving the development toolchain
out of the published metadata entirely, and by bringing every floor current with
the rest of the KGRAG fleet.

## The dev toolchain is no longer part of the package

`pip install 'ftree-kg[dev]'` and `pip install 'ftree-kg[all]'` no longer
resolve. Both extras are gone.

The rule the fleet settled on is that **extras are user-facing features and
Poetry groups are repo tooling**. A PEP 621 extra is written into the wheel, so
declaring `dev` there advertised pytest, ruff, ty, pylint, pre-commit, and
detect-secrets as things an *installer* of this package could ask for. Nobody
installing a filesystem knowledge graph wants a linter, and shipping the offer
in the wheel meant the metadata promised an install path the project had no
interest in supporting.

`all` was the worse of the two. It aggregated nothing but dev tools — so it kept
advertising them as pip-installable no matter where the dev dependencies
themselves lived. That is precisely the defect that survived the equivalent
migrations in `doc_kg` and `Metabo_kg`, which is why it is called out here rather
than quietly dropped.

The toolchain now lives in an optional Poetry group, locked and installable but
absent from the wheel:

```bash
poetry install                # runtime only, unchanged
poetry install --with dev     # pytest, ruff, ty, pylint, pre-commit
```

`adapter` is now the only extra this package publishes.

## Dependency floors caught up

The `kgmodule-utils` floor had been sitting at `>=0.9.0` while the shared SDK
moved on considerably; it is now `>=0.13.2`. It got there in stages across
several fleet sweeps — 0.12.0 brought the `viz3d.organic` growth engine, then
0.12.1, then 0.13.2. The `[adapter]` extra's `kg-rag` floor moves to `>=0.12.0`,
and the maintainer `kg` group tracks `doc-kg>=0.21.2` and `pycode-kg>=0.23.1`.

Two of the bumps are security floors rather than preferences. `pytest` is pinned
`>=9.0.3` for GHSA-6w46-j5rx-g56g, and the locked `cryptography` moved 49.0.0 →
50.0.0 for an OSV.dev advisory against the pinned version — a lockfile-only
change, since the existing `>=3.4.0` floor already allowed the fix.

One floor is deliberately capped instead: `ruff>=0.4.0,<0.16`. Ruff 0.16
reformats Markdown, and while the `*.md` exclusion under `[tool.ruff]` blunts
that, the cap is what actually keeps the resolved ruff aligned with the
`v0.15.22` pin in `.pre-commit-config.yaml`.

## `Last Revision` headers are gone

Every module under `src/ftree_kg/` carried a hand-maintained
`Last Revision: <date>` line, and they had drifted. They are deleted rather than
restamped, because the field cannot be kept honest: correcting one *is* a change
to the file, which moves git's last-change date to today and makes the header
wrong again immediately. A fleet-wide count on 2026-08-15 found 81 of 113 such
headers inaccurate. `Author:` and `License:` stay — those are real provenance and
do not decay.

## Upgrading

If you install `ftree-kg` or `ftree-kg[adapter]`, nothing changes and no rebuild
is needed. There are no schema, node-ID, or index-format changes, so existing
`.filetreekg/` indices remain valid.

If you were installing **`ftree-kg[dev]`** or **`ftree-kg[all]`**, those extras
are gone and the install will now fail. You wanted the contributor setup: clone
the repo and run `poetry install --with dev`. For the full maintainer
environment, including the DocKG and PyCodeKG CLIs, use
`poetry install --all-extras --with dev,kg`.

Contributors already working in a clone should re-run `poetry install --with dev`
— CI now installs with `--with dev` rather than `--extras dev`, and the
pre-commit ruff hook was renamed `ruff` → `ruff-check` to match ruff 0.15.

See [CHANGELOG.md](CHANGELOG.md) for the itemised list.
