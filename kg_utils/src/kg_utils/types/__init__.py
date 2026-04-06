"""kg_utils.types — Core dataclasses and base classes for the KGModule SDK."""

from kg_utils.types.specs import EdgeSpec, NodeSpec, QueryResult, SnippetPack
from kg_utils.types.extractor import KGExtractor
from kg_utils.types.module import KGModule

__all__ = [
    "EdgeSpec",
    "KGExtractor",
    "KGModule",
    "NodeSpec",
    "QueryResult",
    "SnippetPack",
]
