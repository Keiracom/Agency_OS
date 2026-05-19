"""KEI-232 — tests for scripts/orchestrator/external_knowledge_ingester.py.

Covers (no live network, no Weaviate):
  - html_to_text: strips script/style/nav; keeps heading + paragraph structure
  - chunk_text: splits on H2/H3 boundaries; respects CHUNK_MIN_CHARS;
    splits oversized sections at blank-line then hard-cut
  - SOURCES registry covers all 14+ named sources from Dave directive
  - class_schema includes the 6 required fields + text2vec-openai vectorizer
  - SourceOutcome.to_dict shape
  - main() exits non-zero on silent-drop (zero chunks AND zero failures)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "external_knowledge_ingester.py"


@pytest.fixture(scope="module")
def mod():
    # _heartbeat_shim sits next to the script in scripts/orchestrator/ — add to path
    # before import so indexer_base import side-effects find it.
    sys.path.insert(0, str(REPO_ROOT / "scripts" / "orchestrator"))
    spec = importlib.util.spec_from_file_location("external_knowledge_ingester", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["external_knowledge_ingester"] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# html_to_text.
# ---------------------------------------------------------------------------


def test_html_strips_script_and_style(mod) -> None:
    html = "<html><head><style>p { color: red }</style></head>"
    html += "<body><script>alert('x')</script><p>visible text</p></body></html>"
    out = mod.html_to_text(html)
    assert "visible text" in out
    assert "color" not in out
    assert "alert" not in out


def test_html_strips_nav_footer_aside(mod) -> None:
    html = (
        "<html><body>"
        "<nav><a href='/x'>NAV-LINK</a></nav>"
        "<main><p>main content</p></main>"
        "<footer>FOOTER-TEXT</footer>"
        "</body></html>"
    )
    out = mod.html_to_text(html)
    assert "main content" in out
    assert "NAV-LINK" not in out
    assert "FOOTER-TEXT" not in out


def test_html_preserves_heading_marker(mod) -> None:
    html = "<h2>Section Title</h2><p>body</p>"
    out = mod.html_to_text(html)
    # html_to_text injects '## ' before headings so chunk_text can split on them.
    assert "## " in out
    assert "Section Title" in out
    assert "body" in out


# ---------------------------------------------------------------------------
# chunk_text.
# ---------------------------------------------------------------------------


def test_chunk_text_splits_on_h2(mod) -> None:
    text = "## First\n" + ("alpha " * 30) + "\n## Second\n" + ("beta " * 30)
    chunks = mod.chunk_text(text, default_title="default")
    titles = [t for t, _ in chunks]
    assert "First" in titles
    assert "Second" in titles


def test_chunk_text_drops_short_residue(mod) -> None:
    # CHUNK_MIN_CHARS = 80 — a 20-char body should be dropped.
    text = "## Title\nshort body."
    chunks = mod.chunk_text(text, default_title="default")
    assert chunks == []


def test_chunk_text_splits_oversized_at_blank_line(mod) -> None:
    long_para = "x" * (mod.CHUNK_MAX_CHARS - 100)
    text = f"## OneSec\n{long_para}\n\n{long_para}\n\n{long_para}"
    chunks = mod.chunk_text(text, default_title="default")
    assert len(chunks) >= 2  # forced split — single section blew the cap
    for _title, body in chunks:
        assert len(body) <= mod.CHUNK_MAX_CHARS


def test_chunk_text_hard_cut_on_oversized_paragraph(mod) -> None:
    # Single paragraph that exceeds CHUNK_MAX_CHARS — must hard-cut.
    text = "## Title\n" + ("z" * (mod.CHUNK_MAX_CHARS * 3))
    chunks = mod.chunk_text(text, default_title="default")
    assert len(chunks) >= 3
    for _title, body in chunks:
        assert len(body) <= mod.CHUNK_MAX_CHARS


def test_chunk_text_empty_returns_empty(mod) -> None:
    assert mod.chunk_text("", default_title="x") == []
    assert mod.chunk_text("   \n\n  ", default_title="x") == []


def test_chunk_text_uses_default_title_for_intro_body(mod) -> None:
    # Body before any heading uses default_title.
    text = ("alpha " * 30).strip() + "\n## After Heading\n" + ("beta " * 30).strip()
    chunks = mod.chunk_text(text, default_title="introduction")
    titles = [t for t, _ in chunks]
    assert "introduction" in titles
    assert "After Heading" in titles


# ---------------------------------------------------------------------------
# Source registry.
# ---------------------------------------------------------------------------


def test_sources_cover_all_required_domains(mod) -> None:
    """Verbatim from Dave directive 2026-05-19 — every named source present."""
    required = {
        "NATS",
        "Valkey",
        "Weaviate",
        "Cognee",
        "LiteLLM",
        "Supabase",
        "FastAPI",
        "asyncpg",
        "psycopg3",
        "Docker",
        "systemd",
        "LinearAPI",
        "BetterStack",
        "ClaudeCode",
    }
    present = {s[0] for s in mod.SOURCES}
    assert required <= present, f"missing sources: {required - present}"


def test_sources_include_github_repos(mod) -> None:
    repo_sources = [s for s in mod.SOURCES if s[1] == "repo"]
    assert (
        len(repo_sources) >= 4
    )  # nats.py + nats-architecture + valkey-py + weaviate-client + cognee + litellm
    for _name, _kind, target in repo_sources:
        assert target.startswith("https://github.com/")


# ---------------------------------------------------------------------------
# class_schema.
# ---------------------------------------------------------------------------


def test_class_schema_required_fields(mod) -> None:
    schema = mod.class_schema()
    assert schema["class"] == "ExternalKnowledge"
    assert schema["vectorizer"] == "text2vec-openai"
    names = {p["name"] for p in schema["properties"]}
    required = {"url", "source_name", "section_title", "content", "chunk_index", "ingested_at"}
    assert names == required


def test_class_schema_only_content_is_vectorized(mod) -> None:
    """The vectorizer should embed `content`; metadata fields are skip=True."""
    schema = mod.class_schema()
    for prop in schema["properties"]:
        skip = (prop.get("moduleConfig") or {}).get("text2vec-openai", {}).get("skip", False)
        if prop["name"] in ("url", "source_name", "chunk_index", "ingested_at"):
            assert skip is True, f"{prop['name']} should skip vectorization"


# ---------------------------------------------------------------------------
# SourceOutcome.
# ---------------------------------------------------------------------------


def test_source_outcome_to_dict(mod) -> None:
    o = mod.SourceOutcome(source_name="NATS", kind="docs", target="https://x")
    o.pages = 5
    o.chunks_posted = 42
    o.failures.append("boom")
    d = o.to_dict()
    assert d["source_name"] == "NATS"
    assert d["chunks_posted"] == 42
    assert d["failures"] == ["boom"]


# ---------------------------------------------------------------------------
# main exit code on silent-drop.
# ---------------------------------------------------------------------------


def test_main_exits_nonzero_on_silent_drop(mod) -> None:
    """If a source produced 0 chunks AND 0 failures, main() must return 1."""
    fake_outcome = mod.SourceOutcome(source_name="NATS", kind="docs", target="https://x")
    # pages=0, chunks_posted=0, failures=[] — the silent-drop shape.
    with (
        patch.object(mod, "ingest_all", return_value=[fake_outcome]),
        patch.object(mod, "_print_report"),
    ):
        rc = mod.main([])
    assert rc == 1


def test_main_exits_zero_on_real_failure(mod) -> None:
    """Failures are loud — main returns 0 (failures are reported, not silent)."""
    fake_outcome = mod.SourceOutcome(source_name="NATS", kind="docs", target="https://x")
    fake_outcome.failures.append("404")
    with (
        patch.object(mod, "ingest_all", return_value=[fake_outcome]),
        patch.object(mod, "_print_report"),
    ):
        rc = mod.main([])
    assert rc == 0
