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


# ─── main()/daemon contract — regression lock for KEI-208 follow-up ──────


def test_indexer_exposes_ensure_target_class_not_ensure_class():
    """Regression: main() called indexer.ensure_class() — AttributeError on
    DriveStrategicIndexer because BaseIndexer defines ensure_target_class().
    Class never got created in Weaviate as a result (Agency_OS-4f0o)."""
    indexer = dsi.DriveStrategicIndexer()
    assert hasattr(indexer, "ensure_target_class"), (
        "BaseIndexer contract method missing — main() will AttributeError."
    )
    assert not hasattr(indexer, "ensure_class"), (
        "`ensure_class` is the module-level helper, NOT an instance method. "
        "If main() calls indexer.ensure_class() the script crashes before any "
        "Weaviate write — that was the KEI-208 follow-up bug (Agency_OS-4f0o)."
    )


def test_daemon_loop_helper_exists_and_is_signal_safe():
    """Regression: main() called indexer.run_forever(...) which doesn't exist
    on BaseIndexer. The fix replaces it with _run_daemon_loop() helper in
    drive_strategic_indexer; daemon mode would AttributeError without this."""
    assert hasattr(dsi, "_run_daemon_loop"), (
        "_run_daemon_loop helper missing — daemon mode (no --once) will "
        "AttributeError on indexer.run_forever()."
    )
    # Calling it doesn't blow up on signal handler registration even when
    # already in a worker thread (tests run under pytest's main thread).
    import inspect

    sig = inspect.signature(dsi._run_daemon_loop)
    assert "poll_seconds" in sig.parameters
    assert "batch_size" in sig.parameters


def test_main_once_path_runs_without_attribute_error(monkeypatch, tmp_path):
    """End-to-end regression: main(--once) used to crash with AttributeError
    on indexer.ensure_class() before any Drive read or Weaviate POST. Mocks
    out Drive + Weaviate; success criterion is "no AttributeError"."""
    # Config: one fake doc; sections fetched via _fetch_all_sections is mocked.
    cfg = tmp_path / "drive_targets.json"
    cfg.write_text(json.dumps({"documents": [{"doc_id": "fake-doc", "title": "T"}]}))

    fake_section = dsi.DriveSection(
        doc_id="fake-doc",
        doc_url="https://docs.google.com/document/d/fake-doc",
        doc_title="T",
        section="(intro)",
        content="some text",
        updated_at="2026-05-18",
        ratified_by="dave",
        ratified_at="2026-05-18",
    )

    def _fake_fetch_all(self):
        return [fake_section]

    monkeypatch.setattr(dsi.DriveStrategicIndexer, "_fetch_all_sections", _fake_fetch_all)

    # Stub Weaviate HTTP: ensure_class GET 404 → POST schema; POST objects → 200.
    ensure_calls: list[tuple[str, str]] = []
    post_calls: list[tuple[str, dict]] = []

    def _fake_ensure_class(name, schema):
        ensure_calls.append((name, schema["class"]))

    def _fake_post_object(obj):
        post_calls.append((obj["class"], obj))
        return True

    # `ensure_class` + `post_object` live on indexer_base; patch there.
    # drive_strategic_indexer does not re-import ensure_class so patching
    # `dsi.ensure_class` would AttributeError.
    import indexer_base  # noqa: PLC0415

    monkeypatch.setattr(indexer_base, "ensure_class", _fake_ensure_class)
    monkeypatch.setattr(indexer_base, "post_object", _fake_post_object)
    monkeypatch.setattr(dsi, "aggregate_count", lambda _c: len(post_calls))
    monkeypatch.setattr(sys, "argv", ["drive_strategic_indexer", "--once", "--config", str(cfg)])

    rc = dsi.main()

    assert rc == 0, f"main(--once) returned non-zero: {rc}"
    assert ensure_calls == [("StrategicDocuments", "StrategicDocuments")], (
        f"ensure_target_class did not invoke module ensure_class with the "
        f"StrategicDocuments schema; got: {ensure_calls}"
    )
    assert len(post_calls) == 1, f"one section should map to one POST; got {len(post_calls)}"
    assert post_calls[0][0] == "StrategicDocuments"


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
