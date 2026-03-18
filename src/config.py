"""Configuration utilities for FTreeKG.

Reads and parses FTreeKG configuration from pyproject.toml.
"""

from __future__ import annotations

import tomllib
from pathlib import Path


# Built-in directories to always skip
DEFAULT_SKIP_DIRS = {
    # Version control and git
    ".git",
    ".github",
    ".gitignore",
    # Python environments and packages
    ".venv",
    ".env",
    "venv",
    "env",
    # Python caches
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # Build artifacts
    "build",
    "dist",
    ".tox",
    "egg-info",
    ".egg-info",
    # IDEs and editors
    ".vscode",
    ".idea",
    ".vim",
    ".emacs",
    ".sublime",
    # Knowledge graphs
    ".codekg",
    ".dockg",
    ".filetreekg",
    # Node/npm
    "node_modules",
    ".npm",
    # macOS
    ".DS_Store",
}


def _load_dir_list(repo_root: Path | str, key: str) -> set[str]:
    """Load a directory name list from ``[tool.filetreekg].<key>`` in pyproject.toml.

    :param repo_root: Repository root directory.
    :param key: Key name under ``[tool.filetreekg]`` (e.g. ``"include"`` or ``"exclude"``).
    :return: Set of directory names, or an empty set if not found.
    """
    repo_root = Path(repo_root)
    pyproject_path = repo_root / "pyproject.toml"

    if not pyproject_path.exists():
        return set()

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
    except (OSError, ValueError):
        # OSError: file read error, ValueError: invalid TOML
        return set()

    value = data.get("tool", {}).get("filetreekg", {}).get(key, [])
    if isinstance(value, list):
        return {d.rstrip("/") for d in value if isinstance(d, str)}
    return set()


def load_include_dirs(repo_root: Path | str) -> set[str]:
    """Load include directory patterns from pyproject.toml.

    Looks for [tool.filetreekg].include in pyproject.toml at repo_root.
    If not found, returns an empty set (meaning all non-excluded directories are indexed).

    Example::

        # pyproject.toml
        [tool.filetreekg]
        include = ["src", "docs"]

    :param repo_root: Repository root directory.
    :return: Set of directory names to include (e.g., {"src", "docs"}).
             An empty set means no filter — all directories are indexed.
    """
    return _load_dir_list(repo_root, "include")


def load_exclude_dirs(repo_root: Path | str) -> set[str]:
    """Load exclude directory patterns from pyproject.toml.

    Looks for [tool.filetreekg].exclude in pyproject.toml at repo_root.
    Excluded directory names are pruned at every level during the file walk,
    in addition to DEFAULT_SKIP_DIRS.

    Example::

        # pyproject.toml
        [tool.filetreekg]
        exclude = ["archives", "backups"]

    :param repo_root: Repository root directory.
    :return: Set of directory names to exclude (e.g., {"archives", "backups"}).
             An empty set means no extra exclusions beyond DEFAULT_SKIP_DIRS.
    """
    return _load_dir_list(repo_root, "exclude")
