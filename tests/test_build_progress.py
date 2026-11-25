"""Progress output from ``FileTreeKG.build`` and the ``ftreekg build`` CLI.

A real build of a small temporary tree; the embedder is the real one, so the
embedding test is skipped where sentence-transformers is not installed.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

import ftree_kg.module as module
from ftree_kg.cli.group import cli
from ftree_kg.module import FileTreeKG


def _tree(root: Path, n_files: int = 12) -> None:
    """Write a small tree: two folders holding *n_files* files between them."""
    for i in range(n_files):
        folder = root / ("alpha" if i % 2 else "beta")
        folder.mkdir(exist_ok=True)
        (folder / f"f{i}.txt").write_text(f"file {i}\n")


def _kg(root: Path) -> FileTreeKG:
    return FileTreeKG(
        repo_root=root,
        db_path=root / ".filetreekg" / "graph.sqlite",
        vectors_path=root / ".filetreekg" / "vectors.sqlite",
    )


def test_build_is_quiet_by_default(tmp_path: Path, capsys) -> None:
    _tree(tmp_path)
    _kg(tmp_path).build(wipe=True, embed=False)
    out = capsys.readouterr().out
    assert "Scanning" not in out and "Sizing files" not in out


def test_build_with_progress_reports_each_pass(tmp_path: Path, capsys) -> None:
    _tree(tmp_path)
    _kg(tmp_path).build(wipe=True, embed=False, progress=True)
    out = capsys.readouterr().out
    for label in ("Scanning", "Sizing files", "Reading metadata"):
        assert label in out


def test_cli_build_shows_progress(tmp_path: Path) -> None:
    _tree(tmp_path)
    result = CliRunner().invoke(cli, ["build", "--repo", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Scanning" in result.output and "Embedding" in result.output


def test_chunked_embedding_writes_every_node(tmp_path: Path, monkeypatch) -> None:
    """With chunks smaller than the node count, every node still gets a vector."""
    pytest.importorskip("sqlite_vec")
    pytest.importorskip("sentence_transformers")
    monkeypatch.setattr(module, "_EMBED_CHUNK", 5)
    _tree(tmp_path)
    kg = _kg(tmp_path)
    stats = kg.build(wipe=True, embed=True, progress=True)
    with sqlite3.connect(kg.db_path) as conn:
        nodes = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    assert nodes > 5
    assert stats.indexed_rows == nodes
