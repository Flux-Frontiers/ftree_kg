# Release Notes — v0.11.0

> Released: 2026-08-03

Nothing under `src/` changed. What changed is what this package *says* it
depends on — and it was wrong in both directions at once.

## A dependency that was imported but never declared

`src/ftree_kg/adapter.py` imports `kg_rag` at module scope. `kg-rag` appeared
nowhere in `pyproject.toml`. That worked only by luck: anything reaching that
module already had kg-rag installed for other reasons. A clean
`pip install ftree-kg` followed by `import ftree_kg.adapter` raised
`ModuleNotFoundError`.

It is now declared as an `[adapter]` extra:

```bash
pip install 'ftree-kg[adapter]'
```

An extra rather than a core dependency, deliberately — kg-rag already depends
on ftree-kg, so declaring it core would create a real resolution cycle.

Worth knowing: KGRAG federation does **not** need this extra. kg-rag ships its
own `FTreeKGAdapter` and imports this package, not the other way round. The
module in question is not exported from `__init__.py`, nothing in the fleet
imports it, and no test covers it. It may well be vestigial; this release
declares its dependency rather than deciding its fate.

## Two dependencies that were declared but never imported

`doc-kg` and `pycode-kg` were in the `kgdeps` and `all` extras. FTreeKG imports
neither. They are development tooling: the local pre-commit hook rebuilds both
indices, `.mcp.json` serves both MCP servers, and `.claude/CLAUDE.md` documents
them as the dev workflow.

Because extras are published metadata, `pip install ftree-kg[all]` was pulling
two sibling knowledge-graph packages — and their transitive weight — into the
environment of anyone who wanted the visualizer or the test tools. It also put
the entire KG fleet into one resolution graph, so a version bump in any sibling
could constrain this package.

They moved to a Poetry group, which is locked and installable but never written
into the wheel:

```bash
poetry install --with kg      # contributors get the dockg / pycodekg CLIs
poetry install                # everyone else gets nothing extra
```

## Upgrading

If you install `ftree-kg` or `ftree-kg[viz]`, nothing changes.

If you were installing **`ftree-kg[kgdeps]`**, that extra no longer exists. You
almost certainly wanted the contributor setup — clone the repo and run
`poetry install --with kg`. Nothing in the fleet referenced it: kg-rag depends
on bare `ftree-kg`.

If you import `ftree_kg.adapter`, install `ftree-kg[adapter]` to get kg-rag
declared properly. Your existing environment already satisfies it.

See [CHANGELOG.md](CHANGELOG.md) for the itemised list.
