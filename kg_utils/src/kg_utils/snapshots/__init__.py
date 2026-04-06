"""kg_utils.snapshots — Shared snapshot infrastructure for KG modules.

Provides the canonical data models and manager for capturing, storing, and
comparing temporal metric snapshots. Individual KG backends (pycode_kg, doc_kg,
ftree_kg, etc.) import from here instead of maintaining their own copies.
"""

from kg_utils.snapshots.models import PruneResult, Snapshot, SnapshotManifest
from kg_utils.snapshots.manager import SnapshotManager

__all__ = [
    "PruneResult",
    "Snapshot",
    "SnapshotManifest",
    "SnapshotManager",
]
