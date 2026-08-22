"""ftree_kg/metadata.py — Per-format metadata extraction for filesystem nodes.

This module is the second axis of FileTreeKG's ontology: filesystem nodes
carry not only a path and basic stat info but rich format-specific metadata
that can lift semantic search well beyond filename matching.

The dispatcher :func:`extract_metadata` returns a normalised dict keyed by
canonical names (``"camera_make"``, ``"taken_at"``, ``"description"``, ...)
so downstream consumers don't need to know which extractor produced the data.

Currently implemented:

* Image EXIF (JPEG, TIFF, PNG with EXIF, WebP) via Pillow.

Stubs (return ``None`` for now):

* Audio ID3, Video metadata, PDF metadata.

All extractors degrade gracefully — a missing optional library, a corrupt
file, or an unsupported format returns ``None``, never raises.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kg_utils.temporal import temporal_metadata

# Extensions per format family. Lowercase, with leading dot.
IMAGE_EXTS: frozenset[str] = frozenset(
    {".jpg", ".jpeg", ".tiff", ".tif", ".png", ".webp", ".heic", ".heif"}
)
AUDIO_EXTS: frozenset[str] = frozenset({".mp3", ".flac", ".ogg", ".m4a", ".wav"})
VIDEO_EXTS: frozenset[str] = frozenset({".mp4", ".mov", ".mkv", ".avi", ".webm"})
PDF_EXTS: frozenset[str] = frozenset({".pdf"})


# ---------------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------------


def extract_metadata(path: Path) -> dict[str, Any] | None:
    """Dispatch to the right extractor based on file extension.

    Returns ``None`` for unsupported types, missing files, or extraction
    failures. This is the single entry point that ``FileTreeKG.build`` calls.

    :param path: Absolute path to the file.
    :return: Canonical metadata dict, or ``None`` if no extractor applied.
    """
    if not path.is_file():
        return None
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return extract_image_metadata(path)
    # Future: AUDIO_EXTS, VIDEO_EXTS, PDF_EXTS
    return None


# ---------------------------------------------------------------------------
# Image EXIF
# ---------------------------------------------------------------------------

# EXIF tag names (per PIL.ExifTags.TAGS) we care about, mapped to canonical keys.
_EXIF_FIELDS: dict[str, str] = {
    "Make": "camera_make",
    "Model": "camera_model",
    "LensModel": "lens",
    "DateTimeOriginal": "taken_at",
    "DateTime": "taken_at",  # fallback if DateTimeOriginal missing
    "ImageDescription": "description",
    "Artist": "artist",
    "Copyright": "copyright",
    "Software": "software",
    "ISOSpeedRatings": "iso",
    "FNumber": "f_number",
    "ExposureTime": "exposure",
    "FocalLength": "focal_length",
}


def extract_image_metadata(path: Path) -> dict[str, Any] | None:
    """Extract EXIF + dimensions from an image via Pillow.

    Returns ``None`` if Pillow is unavailable, the file cannot be opened,
    or no EXIF block is present (dimensions are still returned in the
    no-EXIF case).

    :param path: Absolute path to an image file.
    :return: Dict with ``dimensions`` plus any EXIF fields that were
             present, or ``None`` on failure.
    """
    try:
        from PIL import Image  # pylint: disable=import-outside-toplevel
        from PIL.ExifTags import GPSTAGS, TAGS  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None

    try:
        with Image.open(path) as img:
            width, height = img.width, img.height
            exif_obj = img.getexif()
            exif = dict(exif_obj) if exif_obj else {}
            # GPSInfo lives in a sub-IFD; getattr to fetch the structured form.
            gps_ifd: dict[Any, Any] = {}
            try:
                gps_ifd_id = next((k for k, v in TAGS.items() if v == "GPSInfo"), None)
                if gps_ifd_id and gps_ifd_id in exif:
                    gps_ifd = exif_obj.get_ifd(gps_ifd_id) or {}
            except Exception:  # pylint: disable=broad-exception-caught
                gps_ifd = {}
    except Exception:  # pylint: disable=broad-exception-caught
        return None

    out: dict[str, Any] = {"dimensions": f"{width}x{height}"}
    for tag_id, value in exif.items():
        tag_name = TAGS.get(tag_id)
        if tag_name is None:
            continue
        canonical = _EXIF_FIELDS.get(tag_name)
        if canonical is None:
            continue
        # Avoid clobbering DateTimeOriginal with the less-specific DateTime.
        if canonical in out and tag_name == "DateTime":
            continue
        out[canonical] = _stringify(value)

    if gps_ifd:
        gps: dict[str, Any] = {}
        for k, v in gps_ifd.items():
            name = GPSTAGS.get(k, k)
            if isinstance(name, str):
                gps[name] = v
        latlon = _gps_to_decimal(gps)
        if latlon is not None:
            out["gps"] = {"lat": latlon[0], "lon": latlon[1]}

    return out


# ---------------------------------------------------------------------------
# Embed-text projection
# ---------------------------------------------------------------------------


def metadata_keywords(meta: dict[str, Any] | None) -> list[str]:
    """Project metadata into a flat list of keyword tokens for embedding.

    Returns an empty list when *meta* is None/empty. The output order is
    stable (camera, date, description, location) so embeddings are
    deterministic for the same input.

    :param meta: Metadata dict from :func:`extract_metadata`.
    :return: Lower-case keyword tokens suitable for the embed-text keywords line.
    """
    if not meta:
        return []
    tokens: list[str] = []
    if "camera_make" in meta:
        tokens.append(str(meta["camera_make"]))
    if "camera_model" in meta:
        tokens.append(str(meta["camera_model"]))
    if "lens" in meta:
        tokens.append(str(meta["lens"]))
    taken = meta.get("taken_at")
    if taken:
        # "2023:07:15 12:00:00" → year + month tokens
        s = str(taken)
        if len(s) >= 7 and s[4] in ":-":
            tokens.append(s[:4])  # year
            tokens.append(f"{s[:4]}-{s[5:7]}")  # year-month
    desc = meta.get("description")
    if desc:
        tokens.append(str(desc))
    if "gps" in meta:
        gps = meta["gps"]
        tokens.append(f"gps:{gps['lat']:.4f},{gps['lon']:.4f}")
    return [_normalise(t) for t in tokens if t]


def metadata_prose(meta: dict[str, Any] | None) -> str:
    """Render metadata as a multi-line human-readable block for ``pack()``.

    :param meta: Metadata dict from :func:`extract_metadata`.
    :return: Multi-line string (one ``key: value`` line per field), or
             empty string if *meta* is None/empty.
    """
    if not meta:
        return ""
    order = (
        "dimensions",
        "camera_make",
        "camera_model",
        "lens",
        "taken_at",
        "description",
        "artist",
        "copyright",
        "software",
        "iso",
        "f_number",
        "exposure",
        "focal_length",
        "gps",
    )
    lines: list[str] = []
    for key in order:
        if key not in meta:
            continue
        val = meta[key]
        if key == "gps" and isinstance(val, dict):
            val = f"{val['lat']:.6f}, {val['lon']:.6f}"
        lines.append(f"{key}: {val}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _stringify(value: Any) -> str:
    """Coerce arbitrary EXIF values to a clean string.

    Handles bytes (decoded as UTF-8 with replacement), Pillow ``IFDRational``
    (rendered as ``num/den`` or decimal), and tuples (joined with commas).
    """
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace").strip("\x00").strip()
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        try:
            return f"{float(value):.4g}"
        except (ZeroDivisionError, TypeError, ValueError):
            return str(value)
    if isinstance(value, tuple):
        return ", ".join(_stringify(v) for v in value)
    return str(value).strip()


def _gps_to_decimal(gps: dict[str, Any]) -> tuple[float, float] | None:
    """Convert EXIF GPS rationals (DMS) to decimal (lat, lon).

    :param gps: Dict from ``GPSInfo`` IFD with keys like
                ``"GPSLatitude"`` (tuple of three rationals) and
                ``"GPSLatitudeRef"`` (``"N"``/``"S"``).
    :return: ``(lat, lon)`` decimal degrees, or ``None`` if either axis
             is missing or malformed.
    """
    try:
        lat_dms = gps["GPSLatitude"]
        lat_ref = gps.get("GPSLatitudeRef", "N")
        lon_dms = gps["GPSLongitude"]
        lon_ref = gps.get("GPSLongitudeRef", "E")
    except KeyError:
        return None
    try:
        lat = _dms_to_decimal(lat_dms)
        lon = _dms_to_decimal(lon_dms)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if lat_ref in ("S", b"S"):
        lat = -lat
    if lon_ref in ("W", b"W"):
        lon = -lon
    return (lat, lon)


def _dms_to_decimal(dms: tuple[Any, Any, Any]) -> float:
    """Degrees/minutes/seconds → decimal degrees."""
    deg, minutes, seconds = (float(v) for v in dms)
    return deg + minutes / 60.0 + seconds / 3600.0


def _normalise(s: str) -> str:
    """Strip whitespace, collapse internal runs, lower-case."""
    return " ".join(s.split()).lower()


# ---------------------------------------------------------------------------
# Shared temporal contract
# ---------------------------------------------------------------------------

#: EXIF stores datetimes as ``YYYY:MM:DD HH:MM:SS`` — colon-separated in the
#: date part, which is not ISO-8601 and which ``datetime.fromisoformat``
#: rejects outright. Converting is the whole reason this module, rather than
#: the caller, owns the mapping onto the contract.
_EXIF_DT_RE = re.compile(r"^(\d{4}):(\d{2}):(\d{2})[ T](\d{2}:\d{2}:\d{2})")


def _exif_to_iso(value: Any) -> str | None:
    """Convert an EXIF datetime string to ISO-8601, if it looks like one.

    :param value: Raw EXIF value, typically ``"2024:01:15 10:30:00"``.
    :return: ISO-8601 text, or ``None`` when there is nothing usable.
    """
    if not value:
        return None
    text = str(value).strip()
    if m := _EXIF_DT_RE.match(text):
        year, month, day, clock = m.groups()
        return f"{year}-{month}-{day}T{clock}"
    return text or None


def temporal_keys(path: Path, meta: dict[str, Any] | None = None) -> dict[str, str]:
    """Derive the shared :mod:`kg_utils.temporal` contract for a filesystem node.

    A file is one of the clearest cases for keeping *occurred* and *recorded*
    apart. A photograph taken on holiday in 1998 and copied onto this disk in
    2024 occurred in 1998 and was recorded in 2024, and a timeline that files it
    under 2024 is simply wrong about it. So:

    - ``occurred_start`` — the EXIF capture time when the file has one, falling
      back to the modification time for everything else. For a plain file the
      two coincide, which is truthful rather than redundant: when the content
      was last written *is* when it came to be.
    - ``recorded_at`` — always the modification time, which is when this
      filesystem learned about the content.

    Derived, never authored: both values come from the file itself, so nothing
    here can drift out of step with the filesystem or the EXIF block.

    :param path: Absolute path to the file.
    :param meta: Format-specific metadata from :func:`extract_metadata`, if any.
    :return: The contract keys, or ``{}`` when the file yields no usable date.
    """
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    except (OSError, ValueError, OverflowError):
        mtime = None

    taken = _exif_to_iso((meta or {}).get("taken_at"))

    try:
        return temporal_metadata(occurred_start=taken or mtime, recorded_at=mtime)
    except (ValueError, TypeError):
        # A malformed EXIF stamp must not cost the file its modification time.
        try:
            return temporal_metadata(occurred_start=mtime, recorded_at=mtime)
        except (ValueError, TypeError):
            return {}
