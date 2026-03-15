"""Pytest configuration for FTreeKG tests.

Available fixtures:
- sample_filesystem: Creates a sample file tree structure in tmp_path
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_filesystem(tmp_path: Path) -> Path:
    """Create a sample filesystem structure for testing.

    Creates a directory tree at tmp_path with the following structure:
    ```
    tmp_path/
    ├── src/
    │   └── modules/
    │       ├── core.py
    │       └── utils.py
    ├── tests/
    │   └── test_core.py
    ├── config.toml
    └── README.md
    ```

    :param tmp_path: Temporary directory from pytest.
    :return: Path to the sample filesystem root (resolved absolute path).
    """
    # Create directory structure
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "modules").mkdir()
    (tmp_path / "src" / "modules" / "core.py").touch()
    (tmp_path / "src" / "modules" / "utils.py").touch()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_core.py").touch()
    (tmp_path / "config.toml").touch()
    (tmp_path / "README.md").touch()

    return tmp_path.resolve()
