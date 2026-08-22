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
