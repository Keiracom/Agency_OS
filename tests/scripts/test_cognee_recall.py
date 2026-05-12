"""tests for scripts/cognee_recall.py — KEI-7 dispatch enrichment wrapper.

Mocks `src.cognee.client.search` via the injectable search_fn parameter on
enrich_dispatch (production routes through asyncio.run + import).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "cognee_recall.py"


@pytest.fixture(scope="module")
def recall_mod():
    spec = importlib.util.spec_from_file_location("cognee_recall", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cognee_recall"] = mod
    spec.loader.exec_module(mod)
    return mod


# _format_context ────────────────────────────────────────────────────────────


def test_format_context_empty_returns_empty_string(recall_mod) -> None:
    assert recall_mod._format_context([], 5) == ""


def test_format_context_renders_top_n(recall_mod) -> None:
    hits = ["fact one", "fact two", "fact three"]
    out = recall_mod._format_context(hits, limit=2)
    assert "## Cognee context" in out
    assert "1. fact one" in out
    assert "2. fact two" in out
    assert "fact three" not in out


def test_format_context_truncates_long_chunks(recall_mod) -> None:
    long_text = "x" * 1000
    out = recall_mod._format_context([long_text], limit=5)
    assert "…" in out
    assert len(out) < 1100


def test_format_context_collapses_newlines(recall_mod) -> None:
    out = recall_mod._format_context(["line1\nline2\nline3"], limit=5)
    assert "line1 line2 line3" in out


# enrich_dispatch ─────────────────────────────────────────────────────────────


def test_enrich_dispatch_empty_text_unchanged(recall_mod) -> None:
    assert recall_mod.enrich_dispatch("") == ""
    assert recall_mod.enrich_dispatch("   ") == "   "


def test_enrich_dispatch_no_credentials_passes_through(recall_mod, monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    original = "Build the new feature."
    assert recall_mod.enrich_dispatch(original) == original


def test_enrich_dispatch_prepends_context_on_hits(recall_mod, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def fake_search(query, **kwargs):
        return ["context fact 1", "context fact 2"]

    out = recall_mod.enrich_dispatch(
        "Brief: ship Stream 2 ingestion.",
        search_fn=fake_search,
    )
    assert out.startswith("## Cognee context")
    assert "context fact 1" in out
    assert "Brief: ship Stream 2 ingestion." in out
    # original dispatch comes after the context block
    assert out.index("## Cognee context") < out.index("Brief:")


def test_enrich_dispatch_no_hits_passes_through(recall_mod, monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def fake_search(query, **kwargs):
        return []

    original = "Brief: do thing X."
    assert recall_mod.enrich_dispatch(original, search_fn=fake_search) == original


def test_enrich_dispatch_search_raises_passes_through(recall_mod, monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def boom(q, **kw):
        raise RuntimeError("simulated cognee failure")

    # search_fn raises before our return → enrich_dispatch's wrapper around
    # search_fn doesn't have a try/except, so this propagates. The caller
    # main() catches it. Verify main() fail-open instead.
    with pytest.raises(RuntimeError):
        recall_mod.enrich_dispatch("text", search_fn=boom)


def test_enrich_dispatch_respects_limit(recall_mod, monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def fake_search(query, **kwargs):
        return [f"fact {i}" for i in range(10)]

    out = recall_mod.enrich_dispatch("brief", limit=3, search_fn=fake_search)
    assert "1. fact 0" in out
    assert "3. fact 2" in out
    assert "4. fact 3" not in out


def test_enrich_dispatch_passes_org_app_agent(recall_mod, monkeypatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    captured = {}

    def fake_search(query, **kw):
        captured.update({"query": query, **kw})
        return []

    recall_mod.enrich_dispatch(
        "the brief",
        org_id="custom_org",
        app_id="custom_app",
        agent_id="aiden",
        search_fn=fake_search,
    )
    assert captured["query"] == "the brief"
    assert captured["org_id"] == "custom_org"
    assert captured["app_id"] == "custom_app"
    assert captured["agent_id"] == "aiden"


# main CLI ──────────────────────────────────────────────────────────────────


def test_main_text_arg_no_credentials_passes_through(recall_mod, monkeypatch, capsys) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["cognee_recall.py", "--text", "hello"])
    rc = recall_mod.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "hello"


def test_main_text_arg_empty_stdin(recall_mod, monkeypatch, capsys) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["cognee_recall.py", "--text", ""])
    rc = recall_mod.main()
    assert rc == 0
    assert capsys.readouterr().out == ""


def test_main_search_raises_passes_through_via_top_level_except(
    recall_mod, monkeypatch, capsys
) -> None:
    """main() has a top-level except that swallows any exception from
    enrich_dispatch and falls back to the original text — the contract is
    'wrapper is fail-open' so caller's pipe never breaks."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["cognee_recall.py", "--text", "original"])

    def boom(*args, **kwargs):
        raise RuntimeError("simulated")

    monkeypatch.setattr(recall_mod, "enrich_dispatch", boom)
    rc = recall_mod.main()
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "original"
