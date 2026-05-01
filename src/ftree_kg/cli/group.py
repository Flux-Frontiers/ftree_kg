"""Defines the root Click group for the FTreeKG CLI.

All command modules import ``cli`` from here to avoid circular imports.
``main.py`` imports both this group and all command modules to register them.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-30 23:41:26
License: Elastic 2.0
"""

import importlib.metadata

import click


@click.group()
@click.version_option(version=importlib.metadata.version("ftree-kg"))
def cli() -> None:
    """FTreeKG — knowledge graph tools for filesystem trees."""
