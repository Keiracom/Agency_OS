"""KEI-208 — tests for drive_strategic_indexer.

Drive client + Weaviate HTTP both mocked. Tests focus on:
  - heading-boundary chunker emits one section per HEADING_*
  - intro text (before first heading) lands in synthetic "(intro)" section
  - build_object output shape matches the StrategicDocuments schema
  - deterministic UUID stable across runs for same (doc_id, section)
  - empty sections (no body text) dropped
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))

import drive_strategic_indexer as dsi  # noqa: E402


def _para(text: str, *, heading: str | None = None) -> dict:
    """Build a fake Docs API paragraph element."""
    style: dict = {}
    if heading is not None:
        style = {"namedStyleType": heading}
    return {
        "paragraph": {
            "paragraphStyle": style,
            "elements": [{"textRun": {"content": text + "\n"}}],
        }
    }


# ─── parse_doc_sections ──────────────────────────────────────────────────


def test_parse_emits_one_section_per_heading():
    body = [
        _para("Intro paragraph before any heading."),
        _para("Section A", heading="HEADING_1"),
        _para("Body of section A line 1."),
        _para("Body of section A line 2."),
        _para("Section B", heading="HEADING_2"),
        _para("Body of section B."),
    ]
    sections = dsi.parse_doc_sections(
        body,
        doc_id="doc-1",
        doc_url="https://docs.google.com/document/d/doc-1",
        doc_title="Test Doc",
        updated_at="2026-05-18",
        ratified_by="dave",
        ratified_at="2026-05-18",
    )
    assert [s.section for s in sections] == ["(intro)", "Section A", "Section B"]
    assert "Intro paragraph" in sections[0].content
    assert "section A line 1" in sections[1].content
    assert "section A line 2" in sections[1].content
    assert "Body of section B" in sections[2].content


def test_parse_drops_empty_sections():
    """Heading with no body text after it (followed immediately by another
    heading) is NOT emitted — the chunker emits only sections with content."""
    body = [
        _para("Section A", heading="HEADING_1"),
        _para("Section B", heading="HEADING_2"),
        _para("Only B has body."),
    ]
    sections = dsi.parse_doc_sections(
        body,
        doc_id="x",
        doc_url="u",
        doc_title="t",
        updated_at="2026-05-18",
        ratified_by="dave",
        ratified_at="2026-05-18",
    )
    # Section A had no body → dropped. Section B has body → emitted.
    assert [s.section for s in sections] == ["Section B"]


def test_parse_handles_no_intro():
    """Doc that starts with a heading directly — no (intro) section emitted."""
    body = [
        _para("Section A", heading="HEADING_1"),
        _para("Body."),
    ]
    sections = dsi.parse_doc_sections(
        body,
        doc_id="x",
        doc_url="u",
        doc_title="t",
        updated_at="2026-05-18",
        ratified_by="dave",
        ratified_at="2026-05-18",
    )
    assert [s.section for s in sections] == ["Section A"]


def test_parse_h1_h2_h3_all_split():
    """Heading levels 1, 2, 3 all create new sections."""
    body = [
        _para("Big", heading="HEADING_1"),
        _para("Body 1."),
        _para("Mid", heading="HEADING_2"),
        _para("Body 2."),
        _para("Small", heading="HEADING_3"),
        _para("Body 3."),
    ]
    sections = dsi.parse_doc_sections(
        body,
        doc_id="x",
        doc_url="u",
        doc_title="t",
        updated_at="2026-05-18",
        ratified_by="dave",
        ratified_at="2026-05-18",
    )
    assert [s.section for s in sections] == ["Big", "Mid", "Small"]


# ─── build_object shape ──────────────────────────────────────────────────


def test_build_object_matches_schema():
    section = dsi.DriveSection(
        doc_id="doc-1",
        doc_url="https://docs.google.com/document/d/doc-1",
        doc_title="Roadmap",
        section="Phase 0.5",
        content="Build NATS, spawn Nova, flip v2.",
        updated_at="2026-05-18",
        ratified_by="dave",
        ratified_at="2026-05-18",
    )
    indexer = dsi.DriveStrategicIndexer()
    obj = indexer.build_object(section)
    assert obj["class"] == "StrategicDocuments"
    assert "id" in obj
    props = obj["properties"]
    assert props["doc_id"] == "doc-1"
    assert props["title"] == "Roadmap"
    assert props["section"] == "Phase 0.5"
    assert props["content"].startswith("Build NATS")
    assert props["ratified_by"] == "dave"


def test_build_object_id_is_deterministic():
    """Same (doc_id, section) → same UUID across runs (idempotent upsert)."""
    section_a = dsi.DriveSection(
        doc_id="doc-1",
        doc_url="x",
        doc_title="t",
        section="Phase 0.5",
        content="body",
        updated_at="2026-05-18",
        ratified_by="d",
        ratified_at="2026-05-18",
    )
    section_b = dsi.DriveSection(
        doc_id="doc-1",
        doc_url="x",
        doc_title="t",
        section="Phase 0.5",
        content="DIFFERENT BODY",  # content differs but identity is same
        updated_at="2026-05-18",
        ratified_by="d",
        ratified_at="2026-05-18",
    )
    indexer = dsi.DriveStrategicIndexer()
    assert indexer.build_object(section_a)["id"] == indexer.build_object(section_b)["id"]


def test_build_object_id_differs_per_section():
    """Different (doc_id, section) → different UUID."""
    s1 = dsi.DriveSection(
        doc_id="doc-1",
        doc_url="x",
        doc_title="t",
        section="Phase 0.5",
        content="b",
        updated_at="2026-05-18",
        ratified_by="d",
        ratified_at="2026-05-18",
    )
    s2 = dsi.DriveSection(
        doc_id="doc-1",
        doc_url="x",
        doc_title="t",
        section="Phase 1",
        content="b",
        updated_at="2026-05-18",
        ratified_by="d",
        ratified_at="2026-05-18",
    )
    indexer = dsi.DriveStrategicIndexer()
    assert indexer.build_object(s1)["id"] != indexer.build_object(s2)["id"]


# ─── class schema sanity ─────────────────────────────────────────────────


def test_class_schema_uses_openai_vectorizer():
    """Per KEI-208 spec: text2vec-openai vectorizer on StrategicDocuments."""
    schema = dsi.DriveStrategicIndexer().class_schema
    assert schema["class"] == "StrategicDocuments"
    assert schema["vectorizer"] == "text2vec-openai"
    property_names = {p["name"] for p in schema["properties"]}
    assert {
        "doc_id",
        "doc_url",
        "title",
        "section",
        "content",
        "updated_at",
        "ratified_by",
        "ratified_at",
    } <= property_names


# ─── config loader integration ───────────────────────────────────────────


def test_config_loader_with_repo_default(tmp_path):
    """Indexer reads doc list from drive_index_targets.json — verify our
    real repo config parses + contains the 5 spec docs."""
    real_config = REPO_ROOT / "config" / "drive_index_targets.json"
    assert real_config.exists(), "config/drive_index_targets.json missing"
    with real_config.open() as fh:
        data = json.load(fh)
    docs = data.get("documents", [])
    assert len(docs) >= 5, f"expected >=5 docs in config, got {len(docs)}"
    for doc in docs:
        assert "doc_id" in doc
        assert "title" in doc


def test_config_loader_empty_returns_no_sections(tmp_path, monkeypatch):
    """Empty config → fetch_all_sections returns []."""
    cfg = tmp_path / "drive_index_targets.json"
    cfg.write_text(json.dumps({"documents": []}))
    indexer = dsi.DriveStrategicIndexer(config_path=cfg)

    def _should_not_be_called() -> None:
        raise AssertionError("should not be called")

    monkeypatch.setattr(dsi, "_docs_client", _should_not_be_called)
    assert indexer._fetch_all_sections() == []
