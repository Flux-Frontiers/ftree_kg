"""Shared Click option decorators for FTreeKG CLI commands.

Each symbol is a reusable decorator factory that can be stacked onto any
Click command to provide consistent option names, defaults, and help text::

    @cli.command()
    @repo_option
    @db_option
    def my_command(repo, db):
        ...
"""

import click
from kg_utils.embed import DEFAULT_MODEL

repo_option = click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True, file_okay=False),
    show_default=True,
    help="Repository or filesystem root directory.",
)

db_option = click.option(
    "--db",
    default=None,
    type=click.Path(),
    show_default=False,
    help="SQLite database path (default: <repo>/.filetreekg/graph.sqlite).",
)

lancedb_option = click.option(
    "--lancedb",
    default=None,
    type=click.Path(),
    show_default=False,
    help="LanceDB directory path (default: <repo>/.filetreekg/lancedb).",
)

model_option = click.option(
    "--model",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Sentence-transformer model name.",
)

k_option = click.option(
    "-k",
    "--k",
    default=8,
    type=int,
    show_default=True,
    help="Number of top results to return.",
)

include_option = click.option(
    "--include-dir",
    multiple=True,
    help="Top-level directory names to include in indexing. Can be used multiple times. "
    "When none are specified, all directories are indexed. "
    "Also reads [tool.filetreekg].include from pyproject.toml.",
)

exclude_option = click.option(
    "--exclude-dir",
    multiple=True,
    help="Directory names to exclude at every depth during indexing. Can be used multiple times. "
    "E.g. --exclude-dir archives --exclude-dir backups. "
    "Also reads [tool.filetreekg].exclude from pyproject.toml.",
)
