"""tests/test_build_scoping.py

Tests that ``ftreekg build`` honours ``--include-dir`` and ``--exclude-dir``.

Regression guard for the 0.13.0 bug in which ``cmd_build`` computed both sets,
echoed them to the user, and then constructed :class:`FileTreeKG` without
passing either.  ``make_extractor`` re-read ``pyproject.toml`` unconditionally,
so both flags were silently dead: only the dotdir rule and ``DEFAULT_SKIP_DIRS``
narrowed the walk.  Building the 19-repo fleet tree with a correct-looking
include list indexed 315k nodes of unrelated third-party clones.
"""

from __future__ import annotations

from pathlib import Path

from ftree_kg.module import FileTreeKG


def _tree(root: Path) -> None:
    """Create three sibling directories, each holding one file."""
    for name in ("keep_me", "drop_me", "also_drop"):
        (root / name).mkdir()
        (root / name / f"{name}.txt").write_text(name)


def _indexed_dirs(kg: FileTreeKG) -> set[str]:
    """Return the set of top-level directory names the extractor yielded."""
    return {
        spec.source_path.split("/")[0]
        for spec in kg.make_extractor().extract()
        if getattr(spec, "source_path", None)
    }


def test_include_dirs_restricts_the_walk(tmp_path: Path) -> None:
    _tree(tmp_path)
    kg = FileTreeKG(repo_root=tmp_path, include_dirs={"keep_me"})
    assert _indexed_dirs(kg) == {"keep_me"}


def test_exclude_dirs_removes_a_directory(tmp_path: Path) -> None:
    _tree(tmp_path)
    kg = FileTreeKG(repo_root=tmp_path, exclude_dirs={"also_drop"})
    assert "also_drop" not in _indexed_dirs(kg)
    assert {"keep_me", "drop_me"}.issubset(_indexed_dirs(kg))


def test_include_and_exclude_apply_together(tmp_path: Path) -> None:
    _tree(tmp_path)
    kg = FileTreeKG(
        repo_root=tmp_path,
        include_dirs={"keep_me", "also_drop"},
        exclude_dirs={"also_drop"},
    )
    assert _indexed_dirs(kg) == {"keep_me"}


def test_empty_include_set_means_no_restriction(tmp_path: Path) -> None:
    """An empty set is 'index everything', distinct from None ('read pyproject')."""
    _tree(tmp_path)
    kg = FileTreeKG(repo_root=tmp_path, include_dirs=set())
    assert _indexed_dirs(kg) == {"keep_me", "drop_me", "also_drop"}


def test_none_falls_back_to_pyproject(tmp_path: Path) -> None:
    """Leaving both as None preserves the documented pyproject.toml behaviour."""
    _tree(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.filetreekg]\ninclude = ["keep_me"]\n',
    )
    kg = FileTreeKG(repo_root=tmp_path)
    assert _indexed_dirs(kg) == {"keep_me"}


def test_cli_build_passes_both_flags_to_the_module(tmp_path: Path, monkeypatch) -> None:
    """The CLI must hand its parsed flags to FileTreeKG, not just echo them.

    This is the test that would have caught the original bug.  ``cmd_build``
    printed the correct include/exclude sets and then dropped them on the floor,
    so any assertion made against its *output* passed while the build indexed
    everything.
    """
    import click.testing

    import ftree_kg.cli.cmd_build as cmd_build
    from ftree_kg.cli.group import cli

    _tree(tmp_path)
    captured: dict[str, object] = {}

    class _Spy:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def build(self, wipe: bool = True) -> None:
            captured["built"] = True

        def stats(self) -> dict[str, object]:
            return {"total_nodes": 0, "total_edges": 0, "node_counts": {}}

    monkeypatch.setattr(cmd_build, "FileTreeKG", _Spy)

    result = click.testing.CliRunner().invoke(
        cli,
        [
            "build",
            "--repo",
            str(tmp_path),
            "--include-dir",
            "keep_me",
            "--exclude-dir",
            "also_drop",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured.get("include_dirs") == {"keep_me"}
    assert captured.get("exclude_dirs") == {"also_drop"}
    assert captured.get("built") is True
