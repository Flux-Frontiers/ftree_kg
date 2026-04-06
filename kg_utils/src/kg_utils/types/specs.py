"""kg_utils/types/specs.py — Core dataclasses shared by all KG modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NodeSpec:
    """Specification for a knowledge-graph node.

    :param node_id: Unique identifier, typically ``<kind>:<path>:<qualname>``.
    :param kind: Node kind (e.g. "file", "function", "class", "directory").
    :param name: Short display name.
    :param qualname: Fully-qualified name or relative path.
    :param source_path: Path to the source file (relative to repo root).
    :param docstring: Semantic content for vector indexing.
    """

    node_id: str
    kind: str
    name: str
    qualname: str
    source_path: str
    docstring: str = ""


@dataclass
class EdgeSpec:
    """Specification for a knowledge-graph edge.

    :param source_id: Node ID of the edge source.
    :param target_id: Node ID of the edge target.
    :param relation: Relation type (e.g. "CONTAINS", "CALLS", "IMPORTS").
    """

    source_id: str
    target_id: str
    relation: str


@dataclass
class QueryResult:
    """Result container returned by KGModule.query().

    :param nodes: List of matched node dicts.
    :param edges: List of matched edge dicts.
    :param seeds: Number of seed nodes from vector search.
    :param expanded_nodes: Number of nodes after graph expansion.
    :param returned_nodes: Number of nodes actually returned.
    :param hop: Number of hops used in graph expansion.
    :param rels: Relation types used in expansion.
    """

    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    seeds: int = 0
    expanded_nodes: int = 0
    returned_nodes: int = 0
    hop: int = 0
    rels: list[str] = field(default_factory=list)


@dataclass
class SnippetPack:
    """Result container returned by KGModule.pack().

    :param query: The original query string.
    :param seeds: Number of seed nodes from vector search.
    :param expanded_nodes: Number of nodes after graph expansion.
    :param returned_nodes: Number of nodes actually returned.
    :param hop: Number of hops used in expansion.
    :param rels: Relation types used in expansion.
    :param model: Embedding model identifier.
    :param nodes: Node dicts included in the pack.
    :param edges: Edge dicts included in the pack.
    :param snippets: Source-code snippets (for code KGs).
    """

    query: str
    seeds: int = 0
    expanded_nodes: int = 0
    returned_nodes: int = 0
    hop: int = 0
    rels: list[str] = field(default_factory=list)
    model: str = ""
    nodes: list[Any] = field(default_factory=list)
    edges: list[Any] = field(default_factory=list)
    snippets: list[Any] = field(default_factory=list)
