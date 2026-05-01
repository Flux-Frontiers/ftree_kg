"""filetreekg.cli — Click-based CLI entry points.

Public API
----------
The root Click group is importable from either location::

    from filetreekg.cli import cli
    from filetreekg.cli.main import cli

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

from ftree_kg.cli import (
    cmd_analyze,  # noqa: F401  — registers analyze
    cmd_build,  # noqa: F401  — registers build
    cmd_hooks,  # noqa: F401  — registers install-hooks
    cmd_query,  # noqa: F401  — registers query, pack
    cmd_snapshot,  # noqa: F401  — registers snapshot
    cmd_status,  # noqa: F401  — registers status
)
from ftree_kg.cli.group import cli

__all__ = ["cli"]
