# Release Notes -- v0.17.0

> Released: 2026-09-21

FTreeKG's MCP server now releases its database handle when it shuts down, and a
`close()` override that quietly prevented that has been removed. Nothing in the
query, build or snapshot paths changes, and no index needs rebuilding.

## What changed

**The MCP server closes the graph on shutdown.** `ftreekg-mcp` wires an
`asynccontextmanager` into `FastMCP(lifespan=...)`, so the graph's SQLite
connection is closed when the server stops rather than left to process exit.
One hook covers both the stdio and SSE transports, because both route through
the same underlying `Server.run()`. This is the resource-cleanup pattern the
fleet standardised on, and FTreeKG is the seventh module to adopt it.

**A `close()` override that was doing harm is gone.** `FileTreeKG.close()` was
a no-op whose docstring read "No persistent connections to release." That was
true of FTreeKG's own methods -- each opens a short-lived connection in a
`with` block -- but not of the shared graph store its base class opens on
demand. Because the override replaced the base implementation, any code path
that did reach that store kept its handle until the process exited. The base
implementation now runs, which is also what gives the new lifespan hook
something to do.

The lifespan test fails without that deletion, which is how the override was
found rather than reasoned about.

## Upgrading

Nothing to do. No index, snapshot or configuration change, and the CLI is
unaffected. If you run `ftreekg-mcp` from a long-lived process, it will now
leave no SQLite handle behind on shutdown.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
