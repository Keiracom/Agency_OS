"""Unit tests for src/retrieval/hyde — Wave 4 HyDE query expansion.

Mocks the Anthropic client so tests run without an API key / network. Locks
the contract: hypothesis generation, flag gating, fail-open fallback, and
that the expanded (hypothetical-bearing) text reaches the retrieval/embedding
path while observability stays on the original query.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.retrieval import agent_query, hyde, orchestrator


def _fake_client(text: str):
    """A stand-in Anthropic client whose messages.create returns `text`."""

    class _Msgs:
        def create(self, **_kwargs):
            return SimpleNamespace(content=[SimpleNamespace(text=text)])

    return SimpleNamespace(messages=_Msgs())


# ─── hyde_enabled ────────────────────────────────────────────────────────────


def test_hyde_disabled_by_default(monkeypatch):
    monkeypatch.delenv(hyde.HYDE_ENABLED_ENV, raising=False)
    assert hyde.hyde_enabled() is False


def test_hyde_enabled_truthy_values(monkeypatch):
    for val in ("1", "true", "TRUE", "yes"):
        monkeypatch.setenv(hyde.HYDE_ENABLED_ENV, val)
        assert hyde.hyde_enabled() is True
    monkeypatch.setenv(hyde.HYDE_ENABLED_ENV, "no")
    assert hyde.hyde_enabled() is False


# ─── generate_hypothetical ───────────────────────────────────────────────────


def test_generate_returns_paragraph():
    with patch.object(
        hyde, "_get_client", return_value=_fake_client("Hindsight embeds server-side.")
    ):
        out = hyde.generate_hypothetical("how does recall embed queries?")
    assert out == "Hindsight embeds server-side."


def test_generate_empty_query_returns_empty():
    assert hyde.generate_hypothetical("") == ""
    assert hyde.generate_hypothetical("   ") == ""


def test_generate_fails_open_on_client_error():
    with patch.object(hyde, "_get_client", side_effect=RuntimeError("no api key")):
        assert hyde.generate_hypothetical("q") == ""


def test_generate_fails_open_on_empty_content():
    with patch.object(hyde, "_get_client", return_value=_fake_client("")):
        assert hyde.generate_hypothetical("q") == ""


def test_generate_passes_model_through():
    captured = {}

    class _Msgs:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(text="x")])

    with patch.object(hyde, "_get_client", return_value=SimpleNamespace(messages=_Msgs())):
        hyde.generate_hypothetical("q", model="governance_tier_fast")
    assert captured["model"] == "governance_tier_fast"
    assert captured["max_tokens"] == hyde.MAX_TOKENS


# ─── gateway routing (Aiden HOLD, PR #1243) ──────────────────────────────────


def test_get_client_requires_base_url(monkeypatch):
    """No ANTHROPIC_BASE_URL → _get_client raises rather than constructing a
    direct (untracked) client."""
    monkeypatch.delenv(hyde.ANTHROPIC_BASE_URL_ENV, raising=False)
    with pytest.raises(RuntimeError, match=hyde.ANTHROPIC_BASE_URL_ENV):
        hyde._get_client()


def test_get_client_routes_through_gateway_when_set(monkeypatch):
    """ANTHROPIC_BASE_URL set → the SDK client is constructed with that base_url
    (no real network call — the SDK constructor does not connect)."""
    monkeypatch.setenv(hyde.ANTHROPIC_BASE_URL_ENV, "http://127.0.0.1:4000")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = hyde._get_client()
    assert str(client.base_url).startswith("http://127.0.0.1:4000")


def test_missing_base_url_degrades_gracefully_no_untracked_call(monkeypatch):
    """The HOLD scenario: ANTHROPIC_BASE_URL absent → expand_query returns the
    original query unchanged. No crash, and no direct Anthropic SDK client is
    ever constructed (so the budget gate sees no untracked call)."""
    monkeypatch.setenv(hyde.HYDE_ENABLED_ENV, "1")
    monkeypatch.delenv(hyde.ANTHROPIC_BASE_URL_ENV, raising=False)

    import anthropic

    with patch.object(anthropic, "Anthropic", side_effect=AssertionError("untracked direct call")):
        assert hyde.expand_query("raw query") == "raw query"


# ─── expand_query ────────────────────────────────────────────────────────────


def test_expand_returns_raw_query_when_disabled(monkeypatch):
    monkeypatch.delenv(hyde.HYDE_ENABLED_ENV, raising=False)
    # generate_hypothetical must not even be reached when disabled.
    with patch.object(hyde, "generate_hypothetical", side_effect=AssertionError("should not run")):
        assert hyde.expand_query("raw query") == "raw query"


def test_expand_fuses_query_and_hypothetical_when_enabled(monkeypatch):
    monkeypatch.setenv(hyde.HYDE_ENABLED_ENV, "1")
    with patch.object(hyde, "generate_hypothetical", return_value="HYPOTHETICAL DOC"):
        out = hyde.expand_query("raw query")
    assert "raw query" in out  # original signal retained
    assert "HYPOTHETICAL DOC" in out


def test_expand_falls_back_to_raw_when_generation_fails(monkeypatch):
    monkeypatch.setenv(hyde.HYDE_ENABLED_ENV, "1")
    with patch.object(hyde, "generate_hypothetical", return_value=""):
        assert hyde.expand_query("raw query") == "raw query"


# ─── embedding-path integration via agent_query.query ────────────────────────


def _outcome(nodes=()):
    return orchestrator.RetrievalOutcome(
        nodes=tuple(nodes),
        bypass_rerank=True,
        rerank_reason="test",
        rerank_elapsed_ms=0,
    )


def test_expanded_text_reaches_retrieval_path_when_enabled(monkeypatch):
    """The fused (hypothetical-bearing) text is what hits the recall/embedding
    path; the raw query is what gets logged for observability."""
    monkeypatch.setenv(hyde.HYDE_ENABLED_ENV, "1")
    captured = {}

    def _fake_retrieve(*, text, **_kwargs):
        captured["search_text"] = text
        return _outcome()

    with (
        patch.object(hyde, "generate_hypothetical", return_value="ANSWER PASSAGE"),
        patch("src.retrieval.agent_query.orchestrator.retrieve_with_outcome", _fake_retrieve),
        patch("src.retrieval.agent_query._record_event") as rec,
    ):
        agent_query.query("what is the canonical approach?", agent="test")

    assert "ANSWER PASSAGE" in captured["search_text"]
    assert "what is the canonical approach?" in captured["search_text"]
    # Observability logs the ORIGINAL query, not the expansion.
    assert rec.call_args.kwargs["query_text"] == "what is the canonical approach?"


def test_raw_query_reaches_retrieval_path_when_disabled(monkeypatch):
    monkeypatch.delenv(hyde.HYDE_ENABLED_ENV, raising=False)
    captured = {}

    def _fake_retrieve(*, text, **_kwargs):
        captured["search_text"] = text
        return _outcome()

    with (
        patch("src.retrieval.agent_query.orchestrator.retrieve_with_outcome", _fake_retrieve),
        patch("src.retrieval.agent_query._record_event"),
    ):
        agent_query.query("plain query", agent="test")

    assert captured["search_text"] == "plain query"
