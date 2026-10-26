"""The server opens the graph per session and closes it after.

kg_utils.mcp's lifespan replaces the module-level ``_kg`` this file used to
patch: the graph is opened when a session starts and closed when it ends, the
resource-cleanup pattern genealogy_kg set and kgrag_priv's FLEET_STANDARDS.md
records (sweep item 5).

Drives the real server through ``mcp.shared.memory``'s in-process transport:
an actual ``Server.run()``/lifespan cycle, not a mock of the lifecycle.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from ftree_kg.mcp_server import build_server
from ftree_kg.module import FileTreeKG

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_the_session_opens_the_graph_and_closes_it(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "a.txt").touch()
    kg = FileTreeKG(repo_root=tmp_path)
    kg.build(wipe=True, embed=False)
    kg.close()

    closed: list[FileTreeKG] = []
    real_close = FileTreeKG.close

    def counting_close(self: FileTreeKG) -> None:
        closed.append(self)
        real_close(self)

    monkeypatch.setattr(FileTreeKG, "close", counting_close)
    async with create_connected_server_and_client_session(build_server(tmp_path)) as session:
        result = await session.call_tool("stats", {})
        assert not result.isError
        assert closed == [], "the graph stays open for the whole session"

    # The server task has unwound by the time the block exits.
    assert len(closed) == 1
