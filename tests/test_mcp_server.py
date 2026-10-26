"""tests/test_mcp_server.py

The FTreeKG MCP server on the fleet's shared base, ``kg_utils.mcp``.

Step 2 of kgrag_priv's MCP centralization plan: the five canonical tools under
the same names as every fleet server, then ``analyze_tree``; ``query`` and
``pack`` keep FileTreeKG's own search (substring fallback, metadata blocks) and
expand through CONTAINS with ``hop``; ``get_node`` and ``neighbors`` read
FileTreeKG's own schema; ``stats`` answers in the fleet shape; the manifest
answers without a graph; ``ftreekg``'s other commands do not import ``mcp``; a
tree with no graph is refused; and a real stdio subprocess serves.

Driven through a real MCP client: ``mcp.shared.memory``'s in-process session
for behaviour, a subprocess for stdio. No model is loaded: the graph is built
without embeddings, so ``query`` takes the substring path.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import anyio
import pytest
from click.testing import CliRunner
from kg_utils.mcp import CANONICAL_TOOLS, manifest
from kg_utils.stats import stats_problems
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session

import ftree_kg
from ftree_kg.cli import cli
from ftree_kg.mcp_server import EXTRA_TOOLS, build_server
from ftree_kg.module import FileTreeKG

_SRC = str(Path(ftree_kg.__file__).resolve().parents[1])


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    """A built tree -- one directory holding one file, and a file at the root."""
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").write_text("hello")
    (tmp_path / "file2.txt").touch()
    kg = FileTreeKG(repo_root=tmp_path)
    kg.build(wipe=True, embed=False)
    kg.close()
    return tmp_path


def _session(server, fn):
    async def main():
        async with create_connected_server_and_client_session(server) as client:
            return await fn(client)

    return anyio.run(main)


def _id_of(tree: Path, rel: str) -> str:
    """The node id FileTreeKG gave the path *rel*."""
    kg = FileTreeKG(repo_root=tree)
    try:
        hits = [n for n in kg.query(rel, k=50).nodes if n["source_path"] == rel]
    finally:
        kg.close()
    assert hits, f"no node for {rel}"
    return hits[0]["id"]


# ---------------------------------------------------------------------------
# Import level
# ---------------------------------------------------------------------------


def test_server_module_imports():
    """The module must import cleanly against the installed mcp release."""
    importlib.import_module("ftree_kg.mcp_server")


def test_entry_point_target_exists():
    """``ftreekg-mcp`` resolves to ftree_kg.mcp_server:main."""
    assert callable(importlib.import_module("ftree_kg.mcp_server").main)


# ---------------------------------------------------------------------------
# The tool surface
# ---------------------------------------------------------------------------


def test_canonical_tools_then_the_extras(tmp_path):
    names = [t["name"] for t in manifest(build_server(tmp_path))["tools"]]
    assert names == [*CANONICAL_TOOLS, *(fn.__name__ for fn in EXTRA_TOOLS)]
    assert names[len(CANONICAL_TOOLS) :] == ["analyze_tree"]


def test_old_tool_names_are_gone(tmp_path):
    names = {t["name"] for t in manifest(build_server(tmp_path))["tools"]}
    assert not names & {"query_tree", "pack_tree", "graph_stats"}


def test_manifest_kind_is_filetree(tmp_path):
    assert manifest(build_server(tmp_path))["kind"] == "filetree"


def test_graph_tools(tree):
    file1 = _id_of(tree, "dir1/file1.txt")
    dir1 = _id_of(tree, "dir1")

    async def calls(client: ClientSession):
        return (
            await client.call_tool("stats", {}),
            await client.call_tool("get_node", {"node_id": file1}),
            await client.call_tool("neighbors", {"node_id": dir1, "direction": "out"}),
            await client.call_tool("neighbors", {"node_id": file1, "direction": "in"}),
            await client.call_tool("get_node", {"node_id": "nope"}),
            await client.call_tool("analyze_tree", {}),
        )

    stats, node, out, parent, missing, report = _session(build_server(tree), calls)
    assert not stats.isError and stats_problems(stats.structuredContent) == []
    assert stats.structuredContent["kind"] == "filetree"
    assert stats.structuredContent["nodes"]["by_kind"]["file"] == 2
    assert "total_size_bytes" in stats.structuredContent
    assert not node.isError and node.structuredContent["source_path"] == "dir1/file1.txt"
    assert node.structuredContent["size_bytes"] == 5
    assert file1 in [n["id"] for n in out.structuredContent["nodes"]]
    assert {e["rel"] for e in out.structuredContent["edges"]} <= {"CONTAINS", "PARENT_OF"}
    assert dir1 in [n["id"] for n in parent.structuredContent["nodes"]]
    assert missing.isError and "no node with id 'nope'" in missing.content[0].text
    assert report.content[0].text.startswith("# FileTreeKG Analysis")


def test_query_and_pack(tree):
    async def calls(client: ClientSession):
        return (
            await client.call_tool("query", {"q": "file1", "k": 5}),
            await client.call_tool("query", {"q": "dir1", "k": 1, "hop": 1}),
            await client.call_tool("pack", {"q": "file", "k": 3, "max_nodes": 3}),
        )

    found, expanded, packed = _session(build_server(tree), calls)
    node = found.structuredContent["nodes"][0]
    # ``id`` is the kg_utils contract; ``node_id`` is the FTreeKG spelling.
    assert node["id"] == node["node_id"]
    assert found.structuredContent["hop"] == 0 and found.structuredContent["edges"] == []
    paths = [n["source_path"] for n in expanded.structuredContent["nodes"]]
    assert "dir1/file1.txt" in paths, paths
    assert expanded.structuredContent["edges"]
    assert "## Nodes" in packed.content[0].text
    assert "- id: `" in packed.content[0].text


def test_out_of_range_hop_is_a_tool_error(tree):
    result = _session(build_server(tree), lambda c: c.call_tool("query", {"q": "x", "hop": 9}))
    assert result.isError and "hop" in result.content[0].text


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def test_banner_reports_the_store_actually_serving(tree, capsys):
    _session(build_server(tree), lambda c: c.call_tool("stats", {}))
    err = capsys.readouterr().err
    assert "ftreekg: serving" in err
    assert f"db      : {tree.resolve() / '.filetreekg' / 'graph.sqlite'}" in err


def test_a_tree_without_a_graph_is_refused_not_served_empty(tmp_path):
    with pytest.raises(BaseException) as info:
        _session(build_server(tmp_path), lambda c: c.call_tool("stats", {}))
    assert "no graph at" in repr(info.value) or any(
        "no graph at" in str(e) for e in getattr(info.value, "exceptions", ())
    )
    assert not (tmp_path / ".filetreekg" / "graph.sqlite").exists()


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


def test_manifest_answers_without_a_graph_and_creates_nothing(tmp_path):
    result = CliRunner().invoke(cli, ["mcp", "--repo", str(tmp_path), "--manifest"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["canonical"] == list(CANONICAL_TOOLS)
    assert not (tmp_path / ".filetreekg").exists()


def test_both_entry_points_are_the_same_command(tmp_path):
    via_cli = CliRunner().invoke(cli, ["mcp", "--repo", str(tmp_path), "--manifest"]).output
    via_script = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ftree_kg.mcp_server import main; main()",
            "--repo",
            str(tmp_path),
            "--manifest",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert json.loads(via_cli) == json.loads(via_script)


def test_sse_is_gone(tmp_path):
    result = CliRunner().invoke(
        cli, ["mcp", "--repo", str(tmp_path), "--transport", "sse", "--manifest"]
    )
    assert result.exit_code == 2


def test_other_commands_do_not_import_mcp():
    out = subprocess.run(
        [sys.executable, "-c", "import sys, ftree_kg.cli; print('mcp' in sys.modules)"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert out == "False"


def test_stdio_subprocess_serves(tree):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from ftree_kg.mcp_server import main; main()", "--repo", str(tree)],
        env={**os.environ, "PYTHONPATH": _SRC},
    )

    async def run():
        with open(tree / "stderr.log", "w", encoding="utf-8") as errlog:
            async with stdio_client(params, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as client:
                    init = await client.initialize()
                    tools = await client.list_tools()
                    stats = await client.call_tool("stats", {})
                    return init, tools, stats

    init, tools, stats = anyio.run(run)
    assert (init.serverInfo.name, init.serverInfo.version) == ("ftreekg", ftree_kg.__version__)
    assert [t.name for t in tools.tools][: len(CANONICAL_TOOLS)] == list(CANONICAL_TOOLS)
    assert stats.structuredContent["kind"] == "filetree"
