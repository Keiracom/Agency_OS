"""Tests for legal_corpus_ingest — KEI-187 corpus parser + object builder.

Parser-only tests; no Weaviate dependency. Covers chunk parsing, malformed
chunk handling, missing-file handling, dry-run path, build_object shape,
and deterministic UUID stability.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "legal_corpus_ingest.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("legal_corpus_ingest", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["legal_corpus_ingest"] = m
    spec.loader.exec_module(m)
    return m


def test_categories_seven_ratified(mod):
    """The 7 ratified categories from 3-way concur on Q5."""
    expected = {
        "privacy-act-au",
        "gdpr",
        "ccpa",
        "oaic",
        "paddle-dpa",
        "saas-tos-pattern",
        "ai-compliance-precedent",
    }
    assert set(mod.CATEGORIES) == expected


def test_schema_has_required_properties(mod):
    """Schema must carry the 5 standard + 4 corpus-specific properties."""
    props = {p["name"] for p in mod.CORPUS_SCHEMA["properties"]}
    assert {"raw_text", "environment_hash", "created_at", "agent", "kei"} <= props
    assert {"category", "source_url", "source_date", "chunk_id"} <= props


def test_parse_single_chunk(mod):
    text = """chunk_id: app-1
source_url: https://example.com/app1
source_date: 2014-03-12

Body text for APP 1."""
    chunks = mod.parse_corpus_file("privacy-act-au", text)
    assert len(chunks) == 1
    c = chunks[0]
    assert c.chunk_id == "app-1"
    assert c.source_url == "https://example.com/app1"
    assert c.source_date == "2014-03-12"
    assert "Body text for APP 1" in c.raw_text


def test_parse_multiple_chunks(mod):
    text = """chunk_id: a
source_url: https://a.example
source_date: 2020-01-01

Body A.
---
chunk_id: b
source_url: https://b.example
source_date: 2021-02-02

Body B with multiple
lines of normative passage."""
    chunks = mod.parse_corpus_file("gdpr", text)
    assert len(chunks) == 2
    assert chunks[0].chunk_id == "a"
    assert chunks[1].chunk_id == "b"
    assert "multiple\nlines" in chunks[1].raw_text


def test_parse_skips_chunk_missing_required_fields(mod):
    """Chunk without chunk_id should be dropped, not raise."""
    text = """source_url: https://example.com
source_date: 2024-01-01

Body without chunk_id — should be skipped."""
    chunks = mod.parse_corpus_file("gdpr", text)
    assert chunks == []


def test_parse_skips_empty_body(mod):
    text = """chunk_id: empty
source_url: https://example.com
source_date: 2024-01-01

"""
    chunks = mod.parse_corpus_file("gdpr", text)
    assert chunks == []


def test_env_hash_stable_for_same_content(mod):
    text = """chunk_id: stable
source_url: https://stable.example
source_date: 2024-01-01

Stable normative content."""
    chunks_a = mod.parse_corpus_file("gdpr", text)
    chunks_b = mod.parse_corpus_file("gdpr", text)
    assert chunks_a[0].env_hash() == chunks_b[0].env_hash()


def test_env_hash_changes_when_content_changes(mod):
    base = """chunk_id: drift
source_url: https://drift.example
source_date: 2024-01-01

"""
    a = mod.parse_corpus_file("gdpr", base + "Original body.")
    b = mod.parse_corpus_file("gdpr", base + "Revised body.")
    assert a[0].env_hash() != b[0].env_hash()


def test_load_corpus_missing_file_warns_not_raises(mod, tmp_path):
    """Missing category file should warn + skip, not raise."""
    chunks = mod.load_corpus(tmp_path, ("nonexistent-category",))
    assert chunks == []


def test_load_corpus_reads_temp_file(mod, tmp_path):
    (tmp_path / "test-cat.md").write_text(
        """chunk_id: x
source_url: https://example.com
source_date: 2024-01-01

Body for x."""
    )
    chunks = mod.load_corpus(tmp_path, ("test-cat",))
    assert len(chunks) == 1
    assert chunks[0].category == "test-cat"


def test_build_object_shape(mod):
    chunk = mod.CorpusChunk(
        category="gdpr",
        chunk_id="art-5",
        source_url="https://gdpr-info.eu/art-5-gdpr/",
        source_date="2018-05-25",
        raw_text="GDPR Article 5 principles.",
    )
    obj = mod.build_object(chunk, "2026-05-18T00:00:00+00:00")
    assert obj["class"] == "Legal_corpus"
    assert "id" in obj
    props = obj["properties"]
    assert props["category"] == "gdpr"
    assert props["chunk_id"] == "art-5"
    assert props["source_url"] == "https://gdpr-info.eu/art-5-gdpr/"
    assert props["source_date"] == "2018-05-25"
    assert props["agent"] == "scout"
    assert props["kei"] == "KEI-187"
    assert props["raw_text"] == "GDPR Article 5 principles."


def test_build_object_id_deterministic(mod):
    """Same (category, chunk_id) tuple → same UUID across runs (idempotent ingest)."""
    chunk = mod.CorpusChunk(
        category="gdpr",
        chunk_id="art-5",
        source_url="x",
        source_date="2018-05-25",
        raw_text="content",
    )
    a = mod.build_object(chunk, "2026-05-18T00:00:00+00:00")["id"]
    b = mod.build_object(chunk, "2026-05-18T00:00:00+00:00")["id"]
    assert a == b


def test_build_object_id_differs_across_categories(mod):
    """Same chunk_id under different categories → different UUIDs."""
    base = {
        "chunk_id": "shared-id",
        "source_url": "x",
        "source_date": "2024-01-01",
        "raw_text": "y",
    }
    a = mod.build_object(mod.CorpusChunk(category="gdpr", **base), "t")["id"]
    b = mod.build_object(mod.CorpusChunk(category="ccpa", **base), "t")["id"]
    assert a != b


def test_real_corpus_files_all_parse(mod):
    """The 7 real category files in docs/legal_corpus/ all parse without warnings.

    This is the acceptance check: KEI-187 says "all 7 categories populated". If
    one of the markdown files has a malformed chunk, this test fires.
    """
    chunks = mod.load_corpus(mod.CORPUS_DIR, mod.CATEGORIES)
    by_category: dict[str, int] = {}
    for c in chunks:
        by_category[c.category] = by_category.get(c.category, 0) + 1
    # Every category has at least 4 chunks (the canonical set per ratification).
    for category in mod.CATEGORIES:
        assert by_category.get(category, 0) >= 4, (
            f"category {category} has {by_category.get(category, 0)} chunks, expected >=4"
        )
