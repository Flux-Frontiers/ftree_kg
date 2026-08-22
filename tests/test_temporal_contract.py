"""FTreeKG's adoption of the shared kg_utils.temporal contract.

A filesystem is where *occurred* and *recorded* come apart most visibly. A
photograph taken on holiday in 1998 and copied onto this disk in 2024 occurred
in 1998 and was recorded in 2024, and a timeline that files it under 2024 is
simply wrong about it.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from kg_utils.temporal import parse_temporal, read_span

from ftree_kg.metadata import _exif_to_iso, temporal_keys

# 2024-04-01T19:33:20Z
_MTIME = 1712000000


@pytest.fixture
def dated_file(tmp_path: Path) -> Path:
    f = tmp_path / "plain.txt"
    f.write_text("contents")
    os.utime(f, (_MTIME, _MTIME))
    return f


class TestExifDateConversion:
    """EXIF stores `YYYY:MM:DD`, which `fromisoformat` rejects outright.

    Without the conversion every photo in the corpus would silently fail to
    parse and drop out of time-scoped queries — the exact failure mode the
    contract is meant to prevent.
    """

    def test_converts_exif_colons_to_iso(self):
        assert _exif_to_iso("2024:01:15 10:30:00") == "2024-01-15T10:30:00"

    def test_passes_through_iso_text(self):
        assert _exif_to_iso("2024-01-15T10:30:00") == "2024-01-15T10:30:00"

    def test_empty_values_yield_none(self):
        assert _exif_to_iso(None) is None
        assert _exif_to_iso("") is None

    def test_converted_value_actually_parses(self):
        """The point of converting: the contract must accept the result."""
        assert parse_temporal(_exif_to_iso("2024:01:15 10:30:00")) is not None


class TestPlainFile:
    def test_mtime_fills_both_keys(self, dated_file):
        t = temporal_keys(dated_file)
        assert t["occurred_start"] == t["recorded_at"]

    def test_mtime_is_the_files_own(self, dated_file):
        t = temporal_keys(dated_file)
        assert parse_temporal(t["occurred_start"])[0].year == 2024

    def test_every_file_is_dated(self, dated_file):
        """Not just the ones with EXIF — otherwise 'what changed in April'
        would answer with photographs alone."""
        assert temporal_keys(dated_file) != {}

    def test_missing_file_yields_nothing(self, tmp_path):
        assert temporal_keys(tmp_path / "gone.txt") == {}


class TestOccurredVersusRecorded:
    """The distinction doing real work."""

    def test_photo_is_dated_by_capture_not_copy(self, dated_file):
        t = temporal_keys(dated_file, {"taken_at": "1998:07:04 14:22:31"})
        assert parse_temporal(t["occurred_start"])[0].year == 1998
        assert parse_temporal(t["recorded_at"])[0].year == 2024

    def test_photo_matches_the_year_it_was_taken(self, dated_file):
        span = read_span(temporal_keys(dated_file, {"taken_at": "1998:07:04 14:22:31"}))
        assert span.overlaps("1998-07-01", "1998-07-31")

    def test_photo_is_not_filed_under_the_year_it_was_copied(self, dated_file):
        span = read_span(temporal_keys(dated_file, {"taken_at": "1998:07:04 14:22:31"}))
        assert not span.overlaps("2024-01-01", "2024-12-31")

    def test_malformed_exif_falls_back_to_mtime(self, dated_file):
        """A bad EXIF stamp must not cost the file its modification time."""
        t = temporal_keys(dated_file, {"taken_at": "one summer afternoon"})
        assert parse_temporal(t["occurred_start"])[0].year == 2024
        assert "recorded_at" in t

    def test_metadata_without_a_date_still_dates_the_file(self, dated_file):
        t = temporal_keys(dated_file, {"camera_make": "Canon"})
        assert parse_temporal(t["occurred_start"])[0].year == 2024


class TestMergedIntoNodeMetadata:
    """The contract is merged alongside format fields, not instead of them."""

    def test_contract_does_not_displace_exif_fields(self, dated_file):
        meta = {"camera_make": "Canon", "taken_at": "1998:07:04 14:22:31"}
        merged = {**meta, **temporal_keys(dated_file, meta)}
        assert merged["camera_make"] == "Canon"
        assert merged["taken_at"] == "1998:07:04 14:22:31"  # raw EXIF preserved
        assert merged["occurred_start"].startswith("1998-07-04")

    def test_raw_exif_and_contract_denote_the_same_moment(self, dated_file):
        """Two renderings, one date — the same rule diary_kg follows."""
        meta = {"taken_at": "1998:07:04 14:22:31"}
        t = temporal_keys(dated_file, meta)
        assert parse_temporal(_exif_to_iso(meta["taken_at"])) == parse_temporal(t["occurred_start"])


class TestQueryResultsSurfaceMetadata:
    """Every path that returns a node must carry its metadata.

    FTreeKG wrote the contract to disk and then never handed it to a caller:
    neither query path selected the column, so through kg-rag's adapter every
    filetree hit arrived undated and any ``time_range`` scope discarded the
    whole KG. Storing it and surfacing it are two different jobs.
    """

    def _kg(self, tmp_path):
        from ftree_kg.module import FileTreeKG

        (tmp_path / "notes.txt").write_text("hello")
        kg = FileTreeKG(
            repo_root=tmp_path,
            db_path=tmp_path / ".ft" / "graph.sqlite",
            vectors_path=tmp_path / ".ft" / "vectors.sqlite",
        )
        kg.build(wipe=True, embed=False, metadata=True)
        return kg

    def test_lexical_query_carries_metadata(self, tmp_path):
        kg = self._kg(tmp_path)
        nodes = kg._lexical_query("notes", k=5)
        assert nodes, "fixture should match"
        assert all("metadata" in n for n in nodes)

    def test_lexical_metadata_holds_the_contract(self, tmp_path):
        kg = self._kg(tmp_path)
        files = [n for n in kg._lexical_query("notes", k=5) if n["kind"] == "file"]
        assert files
        assert "occurred_start" in files[0]["metadata"]

    def test_query_results_are_readable_as_spans(self, tmp_path):
        """The end-to-end claim: a hit can be time-scoped."""
        kg = self._kg(tmp_path)
        files = [n for n in kg.query("notes", k=5).nodes if n.get("kind") == "file"]
        assert files
        span = read_span(files[0].get("metadata"))
        assert span is not None, "a filetree hit must be datable"

    def test_pack_snippets_carry_metadata(self, tmp_path):
        kg = self._kg(tmp_path)
        pack = kg.pack("notes", k=5)
        assert pack.snippets
        assert all("metadata" in s for s in pack.snippets)

    def test_undated_nodes_still_return_a_dict(self, tmp_path):
        """Directories have no metadata; the key must exist and be empty."""
        kg = self._kg(tmp_path)
        nodes = kg._lexical_query("directory", k=10)
        for n in nodes:
            assert isinstance(n["metadata"], dict)


class TestBuildWipeSemantics:
    """`wipe=False` must not wipe.

    The DROP statements lived in the schema script, which ran on every build
    regardless of the flag — so an incremental build was indistinguishable from
    a full one, and the parameter documented behaviour it never had.
    """

    def _kg(self, tmp_path):
        from ftree_kg.module import FileTreeKG

        (tmp_path / "a.txt").write_text("a")
        kg = FileTreeKG(
            repo_root=tmp_path,
            db_path=tmp_path / ".ft" / "graph.sqlite",
            vectors_path=tmp_path / ".ft" / "vectors.sqlite",
        )
        kg.build(wipe=True, embed=False, metadata=False)
        return kg

    def _sentinel(self, kg):
        import sqlite3

        with sqlite3.connect(kg.db_path) as conn:
            conn.execute(
                "INSERT INTO nodes (node_id, kind, name, source_path) VALUES (?,?,?,?)",
                ("sentinel", "file", "s", "a.txt"),
            )

    def _sentinel_present(self, kg) -> bool:
        import sqlite3

        with sqlite3.connect(kg.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM nodes WHERE node_id = 'sentinel'").fetchone()
        return bool(row[0])

    def test_wipe_false_preserves_existing_rows(self, tmp_path):
        kg = self._kg(tmp_path)
        self._sentinel(kg)
        kg.build(wipe=False, embed=False, metadata=False)
        assert self._sentinel_present(kg)

    def test_wipe_true_clears_existing_rows(self, tmp_path):
        kg = self._kg(tmp_path)
        self._sentinel(kg)
        kg.build(wipe=True, embed=False, metadata=False)
        assert not self._sentinel_present(kg)

    def test_wipe_false_still_refreshes_real_nodes(self, tmp_path):
        """Incremental must still upsert the tree, not just skip work."""
        kg = self._kg(tmp_path)
        (tmp_path / "b.txt").write_text("b")
        kg.build(wipe=False, embed=False, metadata=False)
        names = {n["name"] for n in kg._lexical_query("b.txt", k=10)}
        assert "b.txt" in names
