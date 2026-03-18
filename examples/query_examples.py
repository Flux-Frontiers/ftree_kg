"""
FTreeKG Query Examples

Shows how to use the FileTreeKG module to query and analyze file trees.
"""

from pathlib import Path
from src.module import FileTreeKG


def basic_queries():
    """Run basic natural-language queries against a file tree."""
    kg = FileTreeKG(repo_root=Path("."))

    # Build indices if not already built
    kg.build()

    # Query examples
    queries = [
        "Python source files",
        "test directories",
        "configuration files",
        "source code modules",
        "Python modules under src",
        "files with .py extension",
    ]

    for query in queries:
        print(f"\n=== Query: {query} ===")
        results = kg.query(query, k=5)
        for hit in results:
            print(f"  {hit.name} ({hit.kind}): {hit.score:.3f}")
            print(f"    Path: {hit.source_path}")


def pack_snippets():
    """Get metadata snippets for file tree nodes."""
    kg = FileTreeKG(repo_root=Path("."))
    kg.build()

    print("\n=== Getting Snippets ===")
    snippets = kg.pack("all Python modules", k=10)
    for snippet in snippets:
        print(f"  {snippet.name}")
        print(f"    Path: {snippet.source_path}")
        print(f"    Metadata: {snippet.summary[:100]}...")


def stats():
    """Get statistics about the file tree graph."""
    kg = FileTreeKG(repo_root=Path("."))
    kg.build()

    print("\n=== File Tree Statistics ===")
    stats = kg.stats()
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Total edges: {stats['total_edges']}")
    print("  Node counts by kind:")
    for kind, count in stats.get("node_counts", {}).items():
        print(f"    {kind}: {count}")


def analyze():
    """Generate a full analysis report."""
    kg = FileTreeKG(repo_root=Path("."))
    kg.build()

    print("\n=== File Tree Analysis ===")
    report = kg.analyze()
    print(report)


if __name__ == "__main__":
    basic_queries()
    pack_snippets()
    stats()
    analyze()
