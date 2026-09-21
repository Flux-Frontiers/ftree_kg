"""The MCP server's lifespan hook closes the graph's SQLite connection on
shutdown -- the resource-cleanup pattern genealogy_kg set and kgrag_priv's
FLEET_STANDARDS.md records (sweep item 5). FastMCP's ``lifespan=`` fires on
both the stdio and SSE transports, since both route through the same
underlying ``Server.run()``.

Drives the real server through ``mcp.shared.memory``'s in-process transport:
an actual ``Server.run()``/lifespan cycle, not a mock of ``close``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from ftree_kg import mcp_server
from ftree_kg.module import FileTreeKG

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_lifespan_closes_kg_on_server_shutdown(tmp_path: Path) -> None:
    # An unbuilt tree is enough -- what matters is that a connection is open
    # when the server shuts down. Unlike doc_kg, every FileTreeKG method opens
    # its own short-lived sqlite3 connection in a `with`, so no tool call
    # leaves the inherited GraphStore open; touch it directly instead. That
    # store is exactly what the deleted no-op `close()` override used to
    # strand, and what the lifespan now releases.
    kg = FileTreeKG(repo_root=tmp_path, db_path=tmp_path / "graph.sqlite")
    assert kg.store.con is not None  # opens the connection the lifespan must close
    mcp_server._kg = kg
    try:
        async with create_connected_server_and_client_session(mcp_server.mcp) as session:
            await session.call_tool("graph_stats", {})

        # The server task has fully unwound by the time the block above
        # exits, so the lifespan's `finally: kg.close()` has already run.
        assert kg._store is not None  # noqa: SLF001
        assert kg._store._con is None  # noqa: SLF001 - the lifespan closed it
    finally:
        mcp_server._kg = None


async def test_lifespan_is_a_noop_when_kg_was_never_set() -> None:
    # main() always sets _kg before mcp.run(), but the lifespan itself
    # must not blow up if it somehow runs first.
    assert mcp_server._kg is None
    async with create_connected_server_and_client_session(mcp_server.mcp):
        pass
    assert mcp_server._kg is None
