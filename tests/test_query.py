"""tests/test_query.py

Tests for FileTreeKG query and pack.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("kg_utils", reason="kg_utils required for integration tests")

from ftree_kg.module import FileTreeKG  # noqa: E402


def _make_kg(tmp_path: Path, embed: bool = False) -> FileTreeKG:
    """Build a FileTreeKG over a small fixture filesystem.

    :param embed: Forwarded to ``build(embed=...)``. Default ``False`` so most
        tests run quickly without loading a sentence-transformer model.
    """
    (tmp_path / "dir1").mkdir()
    (tmp_path / "dir1" / "file1.txt").touch()
    (tmp_path / "dir2").mkdir()
    (tmp_path / "file2.txt").touch()

    instance = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / ".filetreekg" / "graph.sqlite",
        vectors_path=tmp_path / ".filetreekg" / "vectors.sqlite",
    )
    instance.build(wipe=True, embed=embed)
    return instance


@pytest.fixture
def kg(tmp_path: Path) -> FileTreeKG:
    """SQLite-only fixture (no embedding pass) — fast, used by most tests."""
    return _make_kg(tmp_path, embed=False)


@pytest.fixture
def kg_embedded(tmp_path: Path) -> FileTreeKG:
    """SQLite + sqlite-vec fixture (real embedding pass). Marked integration."""
    pytest.importorskip("sqlite_vec")
    pytest.importorskip("sentence_transformers")
    return _make_kg(tmp_path, embed=True)


def test_build_produces_nodes(kg: FileTreeKG) -> None:
    s = kg.stats()
    assert s["total_nodes"] > 0, "build should produce at least one node"


def test_query_returns_results(kg: FileTreeKG) -> None:
    # Use a term likely to match something in the fixture corpus
    result = kg.query("directory", k=5)
    assert result is not None
    assert isinstance(result.nodes, list)


def test_query_scores_in_range(kg: FileTreeKG) -> None:
    result = kg.query("directory", k=5)
    for node in result.nodes:
        assert 0.0 <= node.get("score", 0.0) <= 1.0


def test_pack_returns_snippets(kg: FileTreeKG) -> None:
    pack = kg.pack("file", k=3)
    assert pack is not None
    assert isinstance(pack.nodes, list) or isinstance(pack.warnings, list)


def test_pack_snippets_have_content(kg: FileTreeKG) -> None:
    pack = kg.pack("file", k=3)
    for node in pack.nodes:
        assert node.get("docstring") or node.get("qualname"), "each node should have metadata"
        # Both spellings are required, not either-or: ``id`` is the kg_utils
        # node contract, ``node_id`` the long-standing FTreeKG one. An ``or``
        # here is what let the missing ``id`` reach SnippetPack.to_markdown().
        assert node["id"] == node["node_id"], "each node must carry both id spellings"


# --------------------------------------------------------------------------
# query() semantic vs. lexical
# --------------------------------------------------------------------------


def test_query_lexical_fallback_when_no_vector_store(kg: FileTreeKG) -> None:
    """When the vector store is missing, query() must still return LIKE matches."""
    # Fixture build() does not populate the vector store, so semantic search returns []
    # and query() falls back to the lexical SQL LIKE path.
    result = kg.query("file", k=10)
    assert len(result.nodes) > 0, "lexical fallback should match 'file' kind"
    # Lexical path stamps every hit with score=1.0
    assert all(n["score"] == 1.0 for n in result.nodes)


def test_query_returns_dicts_with_expected_keys(kg: FileTreeKG) -> None:
    result = kg.query("file", k=3)
    expected = {"id", "node_id", "kind", "name", "qualname", "source_path", "docstring", "score"}
    for n in result.nodes:
        assert expected.issubset(n.keys()), f"missing keys: {expected - n.keys()}"


def test_query_no_match_returns_empty(kg: FileTreeKG) -> None:
    result = kg.query("xyz_no_such_string_anywhere_qqq", k=5)
    assert result.nodes == []
    assert result.seeds == 0
    assert result.returned_nodes == 0


def test_query_respects_k(kg: FileTreeKG) -> None:
    result = kg.query("file", k=2)
    assert len(result.nodes) <= 2


def test_lexical_query_direct(kg: FileTreeKG) -> None:
    """_lexical_query is the LIKE path; bypasses the vector store entirely."""
    nodes = kg._lexical_query("file", k=5)
    assert isinstance(nodes, list)
    assert all(n["score"] == 1.0 for n in nodes)


def test_semantic_query_empty_when_no_vector_store(kg: FileTreeKG) -> None:
    """_semantic_query must return [] (not raise) when the vector store is missing."""
    nodes = kg._semantic_query("file tree extractor", 5)
    assert nodes == []


def test_semantic_query_empty_when_vectors_file_missing(tmp_path: Path) -> None:
    """When the vectors file is missing, _semantic_query degrades cleanly."""
    instance = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / "graph.sqlite",
        vectors_path=tmp_path / "vectors_does_not_exist.sqlite",
    )
    instance.build(wipe=True, embed=False)
    nodes = instance._semantic_query("anything", 5)
    assert not nodes


# --------------------------------------------------------------------------
# pack() snippet shape and content
# --------------------------------------------------------------------------


def test_pack_populates_snippets_field(kg: FileTreeKG) -> None:
    """The new pack() implementation must populate SnippetPack.snippets."""
    pack = kg.pack("file", k=3)
    assert hasattr(pack, "snippets")
    assert isinstance(pack.snippets, list)
    assert len(pack.snippets) > 0


def test_pack_snippet_shape(kg: FileTreeKG) -> None:
    """Each snippet dict must carry the contract fields used by downstream wrappers."""
    pack = kg.pack("file", k=3)
    expected = {"node_id", "source_path", "content", "score", "kind", "name"}
    for s in pack.snippets:
        assert expected.issubset(s.keys()), f"missing snippet keys: {expected - s.keys()}"


def test_pack_snippet_content_has_metadata_header(kg: FileTreeKG) -> None:
    """Snippet content must start with 'kind: source_path' so consumers can locate the node."""
    pack = kg.pack("file", k=3)
    for s in pack.snippets:
        first_line = s["content"].splitlines()[0]
        assert first_line == f"{s['kind']}: {s['source_path']}", (
            f"unexpected first line: {first_line!r}"
        )


def test_pack_snippet_content_has_size_for_files(kg: FileTreeKG) -> None:
    """File snippets must include a 'size:' line; directories have no size."""
    # The fixture's two files (file1.txt, file2.txt) are empty (.touch()),
    # so size_bytes==0 and the 'size:' line is omitted. Build a non-empty
    # file to verify the size line appears when relevant.
    repo = Path(kg.repo_root)
    (repo / "non_empty.py").write_text("# content\n" * 10)
    kg.build(wipe=True, embed=False)
    pack = kg.pack("non_empty", k=3)
    sized = [s for s in pack.snippets if "size:" in s["content"]]
    assert len(sized) > 0, "non-empty file should yield a snippet with a 'size:' line"


def test_pack_snippets_aligned_with_nodes(kg: FileTreeKG) -> None:
    """SnippetPack.nodes and SnippetPack.snippets describe the same hits in order."""
    pack = kg.pack("file", k=5)
    assert len(pack.snippets) == len(pack.nodes)
    for snippet, node in zip(pack.snippets, pack.nodes, strict=True):
        assert snippet["node_id"] == node["node_id"]
        assert snippet["source_path"] == node["source_path"]
        assert snippet["score"] == node["score"]


def test_pack_no_match_returns_empty_snippets(kg: FileTreeKG) -> None:
    pack = kg.pack("xyz_no_such_string_anywhere_qqq", k=5)
    assert pack.snippets == []
    assert pack.nodes == []


# --------------------------------------------------------------------------
# Semantic search integration — populates a real sqlite-vec store
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# _embed_text — filesystem-native ontology
# --------------------------------------------------------------------------


def test_embed_text_file_format() -> None:
    from ftree_kg.module import _embed_text

    row = (
        "file:src/ftree_kg/cli/cmd_build.py:cmd_build.py",
        "file",
        "cmd_build.py",
        "src/ftree_kg/cli/cmd_build.py",
        "src/ftree_kg/cli/cmd_build.py",
        None,
        4096,
        None,  # metadata
    )
    text = _embed_text(row)
    lines = text.splitlines()
    assert len(lines) == 2
    assert lines[0] == "file cmd_build.py at src/ftree_kg/cli/cmd_build.py"
    assert lines[1].startswith("keywords: ")
    keywords = set(lines[1].removeprefix("keywords: ").split())
    # Path components, basename word-splits, and extension are all present.
    assert {"src", "ftree_kg", "cli", "cmd_build", "cmd", "build", "py"} <= keywords


def test_embed_text_directory_has_no_extension() -> None:
    from ftree_kg.module import _embed_text

    row = (
        "directory:src/ftree_kg/cli:cli",
        "directory",
        "cli",
        "src/ftree_kg/cli",
        "src/ftree_kg/cli",
        None,
        0,
        None,  # metadata
    )
    text = _embed_text(row)
    lines = text.splitlines()
    assert lines[0] == "directory cli at src/ftree_kg/cli"
    keywords = lines[1].removeprefix("keywords: ").split()
    # No extension token; directory name is a path component, not a stem split.
    assert "py" not in keywords
    assert "src" in keywords and "ftree_kg" in keywords and "cli" in keywords


def test_embed_text_drops_pythonic_fields() -> None:
    """The new ontology must not leak doc_kg's QUALNAME/MODULE/DOCSTRING vocabulary."""
    from ftree_kg.module import _embed_text

    row = ("nid", "file", "x.py", "x", "x.py", "fake-docstring-text", 0, None)
    text = _embed_text(row).upper()
    for stale in ("QUALNAME", "MODULE:", "DOCSTRING"):
        assert stale not in text, f"stale field {stale} leaked into embed text"
    # The fake docstring must not be in the embedding.
    assert "FAKE-DOCSTRING-TEXT" not in text


@pytest.mark.integration
def test_build_populates_vector_store(kg_embedded: FileTreeKG) -> None:
    """build(embed=True) must write a populated sqlite-vec store."""
    from kg_utils.vector_backend import SqliteVecBackend

    from ftree_kg.module import _META_COLUMNS

    assert kg_embedded.vectors_path is not None
    assert Path(kg_embedded.vectors_path).exists()
    backend = SqliteVecBackend(kg_embedded.vectors_path, meta_columns=_META_COLUMNS)
    backend.open()
    try:
        assert backend.count() == kg_embedded.stats()["total_nodes"]
    finally:
        backend.close()


@pytest.mark.integration
def test_semantic_query_routes_through_vector_store_after_build(kg_embedded: FileTreeKG) -> None:
    """After build(embed=True), query() should produce non-trivial scores (semantic, not LIKE=1.0)."""
    result = kg_embedded.query("source code file", k=3)
    assert result.nodes
    # The lexical fallback would stamp every score at 1.0; the semantic path
    # produces real cosine-derived scores in (0, 1).
    assert any(n["score"] != 1.0 for n in result.nodes)


def test_pack_renders_markdown(kg: FileTreeKG) -> None:
    """SnippetPack.to_markdown() must render — regression for a missing ``id``.

    kg_utils reads ``n['id']`` when rendering; FTreeKG emitted only ``node_id``,
    so this raised ``KeyError: 'id'``. Nothing caught it because the CLI renders
    packs via rich and never calls ``to_markdown()``.
    """
    md = kg.pack("file", k=3).to_markdown()
    assert "## Nodes" in md
    assert "- id: `" in md


@pytest.mark.integration
def test_semantic_query_nodes_carry_both_id_spellings(kg_embedded: FileTreeKG) -> None:
    """The vector path builds its own node dicts, so it needs its own check.

    ``_semantic_query`` and ``_lexical_query`` construct dicts independently —
    fixing one does not fix the other.
    """
    result = kg_embedded.query("source code file", k=3)
    assert result.nodes
    for n in result.nodes:
        assert n["id"] == n["node_id"]


@pytest.mark.integration
def test_semantic_pack_renders_markdown(kg_embedded: FileTreeKG) -> None:
    """to_markdown() must also survive the semantic path, not just the fallback."""
    md = kg_embedded.pack("source code file", k=3).to_markdown()
    assert "- id: `" in md


# --------------------------------------------------------------------------
# Per-format metadata pipeline (EXIF for images)
# --------------------------------------------------------------------------


def _kg_with_image(tmp_path: Path, embed: bool = False) -> FileTreeKG:
    """Build a small fixture filesystem that contains a JPEG with EXIF tags."""
    pytest.importorskip("PIL")
    from PIL import Image
    from PIL.ExifTags import IFD, TAGS

    (tmp_path / "photos").mkdir()
    img_path = tmp_path / "photos" / "vacation.jpg"
    img = Image.new("RGB", (16, 16), color="blue")
    exif = img.getexif()
    tag_id = {n: t for t, n in TAGS.items()}
    exif[tag_id["Make"]] = "Apple"
    exif[tag_id["Model"]] = "iPhone 14 Pro"
    exif[tag_id["DateTime"]] = "2023:07:15 12:34:56"
    exif.get_ifd(IFD.Exif)[tag_id["DateTimeOriginal"]] = "2023:07:15 12:34:56"
    exif[tag_id["ImageDescription"]] = "Beach at sunset"
    img.save(img_path, "JPEG", exif=exif)

    instance = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / ".filetreekg" / "graph.sqlite",
        vectors_path=tmp_path / ".filetreekg" / "vectors.sqlite",
    )
    instance.build(wipe=True, embed=embed, metadata=True)
    return instance


def test_metadata_column_populated_for_images(tmp_path: Path) -> None:
    """build(metadata=True) must populate the metadata column for image files."""
    import json
    import sqlite3

    kg = _kg_with_image(tmp_path, embed=False)
    assert kg.db_path is not None
    with sqlite3.connect(kg.db_path) as conn:
        rows = conn.execute(
            "SELECT name, metadata FROM nodes WHERE name = 'vacation.jpg'"
        ).fetchall()
    assert rows, "image node missing"
    name, meta_json = rows[0]
    assert meta_json is not None, "metadata column should be populated for the image"
    meta = json.loads(meta_json)
    assert meta["camera_make"] == "Apple"
    assert meta["camera_model"] == "iPhone 14 Pro"
    assert meta["taken_at"].startswith("2023:07:15")


def test_metadata_column_null_for_non_image_files(tmp_path: Path) -> None:
    """A .py / .txt file must have NULL metadata, not an empty dict."""
    import sqlite3

    kg = _kg_with_image(tmp_path, embed=False)
    # Add a plain text file and rebuild
    (tmp_path / "notes.txt").write_text("hi")
    kg.build(wipe=True, embed=False, metadata=True)
    assert kg.db_path is not None
    with sqlite3.connect(kg.db_path) as conn:
        row = conn.execute("SELECT metadata FROM nodes WHERE name = 'notes.txt'").fetchone()
    assert row is not None
    assert row[0] is None, "non-image files must not have a metadata blob"


def test_metadata_skipped_when_metadata_false(tmp_path: Path) -> None:
    """build(metadata=False) must leave the column untouched (NULL)."""
    import sqlite3

    pytest.importorskip("PIL")
    from PIL import Image

    img_path = tmp_path / "photo.jpg"
    Image.new("RGB", (8, 8), "red").save(img_path, "JPEG")

    kg = FileTreeKG(
        repo_root=tmp_path,
        db_path=tmp_path / ".filetreekg" / "graph.sqlite",
        vectors_path=tmp_path / ".filetreekg" / "vectors.sqlite",
    )
    kg.build(wipe=True, embed=False, metadata=False)
    assert kg.db_path is not None
    with sqlite3.connect(kg.db_path) as conn:
        row = conn.execute("SELECT metadata FROM nodes WHERE name = 'photo.jpg'").fetchone()
    assert row[0] is None


def test_embed_text_includes_image_metadata_tokens(tmp_path: Path) -> None:
    """_embed_text must fold camera/year/description into the keyword line."""
    import sqlite3

    from ftree_kg.module import _embed_text

    kg = _kg_with_image(tmp_path, embed=False)
    assert kg.db_path is not None
    with sqlite3.connect(kg.db_path) as conn:
        row = conn.execute(
            "SELECT node_id, kind, name, qualname, source_path, docstring,"
            " size_bytes, metadata FROM nodes WHERE name = 'vacation.jpg'"
        ).fetchone()
    text = _embed_text(row).lower()
    assert "apple" in text, "camera make missing from embed text"
    assert "iphone 14 pro" in text, "camera model missing from embed text"
    assert "2023" in text, "capture year missing from embed text"
    assert "beach at sunset" in text, "description missing from embed text"


def test_lexical_fallback_matches_exif_description(tmp_path: Path) -> None:
    """Without an embedding index, query() must still find images via EXIF text."""
    kg = _kg_with_image(tmp_path, embed=False)
    # 'sunset' doesn't appear in any path or filename — only in EXIF description
    result = kg.query("sunset", k=5)
    assert any(n["name"] == "vacation.jpg" for n in result.nodes), (
        "lexical fallback should match the JPEG via its EXIF description"
    )


def test_pack_snippet_surfaces_image_metadata(tmp_path: Path) -> None:
    """pack() snippet content must include a readable metadata block for images."""
    kg = _kg_with_image(tmp_path, embed=False)
    pack = kg.pack("vacation", k=3)
    matched = [s for s in pack.snippets if s["name"] == "vacation.jpg"]
    assert matched, "image snippet should match"
    content = matched[0]["content"]
    assert "camera_make: Apple" in content
    assert "camera_model: iPhone 14 Pro" in content
    assert "taken_at:" in content
    assert "description: Beach at sunset" in content


@pytest.mark.integration
def test_semantic_query_finds_image_by_camera(tmp_path: Path) -> None:
    """End-to-end: build with embeddings, query 'iPhone photo', image ranks first."""
    pytest.importorskip("sqlite_vec")
    pytest.importorskip("sentence_transformers")
    kg = _kg_with_image(tmp_path, embed=True)
    result = kg.query("iPhone photo from 2023", k=5)
    assert result.nodes
    top = result.nodes[0]
    assert top["name"] == "vacation.jpg", f"expected vacation.jpg as top hit, got {top['name']!r}"


@pytest.mark.integration
def test_semantic_query_with_real_index(kg: FileTreeKG) -> None:
    """End-to-end: hand-build a sqlite-vec store over the fixture nodes, then query."""
    pytest.importorskip("sqlite_vec")
    pytest.importorskip("sentence_transformers")
    # Pull every node from the SQLite graph and embed its canonical text.
    import sqlite3

    from kg_utils.embedder import get_embedder
    from kg_utils.vector_backend import SqliteVecBackend

    from ftree_kg.module import _META_COLUMNS

    assert kg.db_path is not None
    with sqlite3.connect(kg.db_path) as conn:
        rows = conn.execute(
            "SELECT node_id, kind, name, qualname, source_path, docstring FROM nodes"
        ).fetchall()
    assert rows, "fixture must contain at least one node"

    embedder = get_embedder()
    docs = []
    for node_id, kind, name, qualname, source_path, docstring in rows:
        text = f"{kind}: {qualname}\n{docstring or ''}"
        vec = embedder.embed_query(text)
        docs.append(
            {
                "id": node_id,
                "kind": kind,
                "name": name,
                "qualname": qualname,
                "module_path": source_path,
                "text": text,
                "vector": vec,
            }
        )

    assert kg.vectors_path is not None
    backend = SqliteVecBackend(
        kg.vectors_path, dim=len(docs[0]["vector"]), meta_columns=_META_COLUMNS
    )
    backend.open(wipe=True)
    try:
        backend.upsert(docs)
    finally:
        backend.close()

    # Semantic phrase that no node's qualname/docstring contains literally.
    nodes = kg._semantic_query("python source module file", k=5)
    assert len(nodes) > 0, "semantic query should rank fixture nodes by similarity"
    # Scores must be in [0, 1]; ranking must be descending by cosine distance.
    scores = [n["score"] for n in nodes]
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)
    # Top-level query() should now use the semantic path (not the LIKE fallback).
    qresult = kg.query("python source module file", k=3)
    assert qresult.nodes
    # Lexical fallback assigns score=1.0; semantic path produces non-trivial scores.
    assert any(n["score"] != 1.0 for n in qresult.nodes)


def test_analyze_returns_markdown(kg: FileTreeKG) -> None:
    report = kg.analyze()
    assert report.startswith("#"), "analyze() must return Markdown starting with a heading"
    assert "FileTreeKG" in report or "Analysis" in report
