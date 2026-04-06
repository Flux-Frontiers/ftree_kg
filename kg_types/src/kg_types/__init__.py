"""kg_types — Shared base types for the KGModule SDK."""

from kg_types.specs import EdgeSpec, NodeSpec, SnippetPack, QueryResult
from kg_types.extractor import KGExtractor
from kg_types.module import KGModule

__all__ = [
    "EdgeSpec",
    "KGExtractor",
    "KGModule",
    "NodeSpec",
    "QueryResult",
    "SnippetPack",
]
__version__ = "0.1.0"
