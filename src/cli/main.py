"""Root Click group for the FTreeKG CLI.

Usage::

    ftreekg --help
    ftreekg --version
    ftreekg build --help
"""

import importlib.metadata

import click


@click.group()
@click.version_option(version=importlib.metadata.version("filetreekg"))
def cli() -> None:
    """FTreeKG — knowledge graph tools for filesystem trees."""


if __name__ == "__main__":
    cli()
