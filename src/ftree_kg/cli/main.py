"""Root Click group for the FTreeKG CLI.

Usage::

    ftreekg --help
    ftreekg --version
    ftreekg build --help

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

import ftree_kg.cli.cmd_analyze  # noqa: F401  # pylint: disable=unused-import
import ftree_kg.cli.cmd_build  # noqa: F401  # pylint: disable=unused-import
import ftree_kg.cli.cmd_hooks  # noqa: F401  # pylint: disable=unused-import
import ftree_kg.cli.cmd_query  # noqa: F401  # pylint: disable=unused-import
import ftree_kg.cli.cmd_snapshot  # noqa: F401  # pylint: disable=unused-import
import ftree_kg.cli.cmd_status  # noqa: F401  # pylint: disable=unused-import
from ftree_kg.cli.group import cli  # noqa: F401 — re-exported for entry point

if __name__ == "__main__":
    cli()
