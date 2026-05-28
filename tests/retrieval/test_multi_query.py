"""Tests for src/retrieval/multi_query.

Covers: variant generation, merge/dedup, fallback, gateway routing,
and the integration hook in agent_query.query().
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.retrieval import multi_query, orchestrator

# ── helpers ───────────────────────────────────────────────────────────────────


def _node(
    text: str,
    score: float,
    *,
    collection: str = "Discoveries",
    source_id: str | None = None,
    memory_id: str | None = None,
) -> orchestrator.RetrievedNode:
    md: dict = {}
    if source_id:
        md["source_id"] = source_id
    if memory_id:
        md["memory_id"] = memory_id
    return orchestrator.RetrievedNode(text=text, score=score, metadata=md, collection=collection)


def _fake_response(lines: list[str]) -> MagicMock:
    """Return a fake Anthropic messages.create() response with the given lines joined."""
    block = SimpleNamespace(text="\n".join(lines))
    resp = MagicMock()
    resp.content = [block]
    return resp


# ── generate_variants ─────────────────────────────────────────────────────────


def test_generate_variants_includes_original_as_first():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response(["alt one", "alt two"])
    with patch.object(multi_query, "_get_client", return_value=fake_client):
        variants = multi_query.generate_variants("original query", n=3)
    assert variants[0] == "original query"


def test_generate_variants_returns_alternatives():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response(
        ["phrasing A", "phrasing B", "phrasing C"]
    )
    with patch.object(multi_query, "_get_client", return_value=fake_client):
        variants = multi_query.generate_variants("test query", n=3)
    assert "phrasing A" in variants
    assert len(variants) <= 4  # original + up to 3


def test_generate_variants_deduplicates_original_from_llm_output():
    fake_client = MagicMock()
    # LLM returns the original verbatim — should be dropped from alternatives
    fake_client.messages.create.return_value = _fake_response(["test query", "alt one"])
    with patch.object(multi_query, "_get_client", return_value=fake_client):
        variants = multi_query.generate_variants("test query", n=3)
    # "test query" should appear exactly once (as the original)
    assert variants.count("test query") == 1


def test_generate_variants_fallback_on_llm_failure():
    """Any LLM error → [query] (fail-open, single-query baseline preserved)."""
    with patch.object(multi_query, "_get_client", side_effect=RuntimeError("no gateway")):
        variants = multi_query.generate_variants("fallback query")
    assert variants == ["fallback query"]


def test_generate_variants_fallback_on_empty_response():
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response([])
    with patch.object(multi_query, "_get_client", return_value=fake_client):
        variants = multi_query.generate_variants("empty response query")
    assert variants == ["empty response query"]


def test_generate_variants_empty_input_returns_empty_string_list():
    variants = multi_query.generate_variants("")
    assert variants == [""]


# ── gateway routing ────────────────────────────────────────────────────────────


def test_get_client_requires_base_url(monkeypatch):
    """No ANTHROPIC_BASE_URL → _get_client raises, never constructing a direct client."""
    monkeypatch.delenv(multi_query.ANTHROPIC_BASE_URL_ENV, raising=False)
    with pytest.raises(RuntimeError, match=multi_query.ANTHROPIC_BASE_URL_ENV):
        multi_query._get_client()


def test_get_client_routes_through_gateway_when_set(monkeypatch):
    """ANTHROPIC_BASE_URL set → SDK client constructed with that base_url."""
    monkeypatch.setenv(multi_query.ANTHROPIC_BASE_URL_ENV, "http://127.0.0.1:4000")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = multi_query._get_client()
    assert str(client.base_url).startswith("http://127.0.0.1:4000")


def test_missing_base_url_degrades_gracefully_no_untracked_call(monkeypatch):
    """ANTHROPIC_BASE_URL absent → generate_variants returns [query]. No direct SDK call."""
    monkeypatch.setenv(multi_query.MULTI_QUERY_ENABLED_ENV, "1")
    monkeypatch.delenv(multi_query.ANTHROPIC_BASE_URL_ENV, raising=False)

    import anthropic

    with patch.object(anthropic, "Anthropic", side_effect=AssertionError("untracked direct call")):
        variants = multi_query.generate_variants("raw query")
    assert variants == ["raw query"]


# ── merge_results + _node_key ─────────────────────────────────────────────────


def test_merge_results_deduplicates_by_memory_id():
    """Same memory_id from two variant searches → keep the higher-scored node."""
    n_hi = _node("text", 0.9, memory_id="mem-1")
    n_lo = _node("text", 0.6, memory_id="mem-1")
    merged = multi_query.merge_results(
        [
            (n_hi,),
            (n_lo,),
        ]
    )
    assert len(merged) == 1
    assert merged[0].score == pytest.approx(0.9)


def test_merge_results_deduplicates_by_source_id():
    n_hi = _node("text", 0.8, source_id="src-42")
    n_lo = _node("text", 0.3, source_id="src-42")
    merged = multi_query.merge_results(
        [
            (n_lo,),
            (n_hi,),
        ]
    )
    assert len(merged) == 1
    assert merged[0].score == pytest.approx(0.8)


def test_merge_results_keeps_distinct_nodes():
    a = _node("alpha", 0.7, source_id="a")
    b = _node("beta", 0.5, source_id="b")
    c = _node("gamma", 0.9, source_id="c")
    merged = multi_query.merge_results([(a,), (b,), (c,)])
    assert len(merged) == 3


def test_merge_results_sorted_by_score_descending():
    a = _node("low", 0.1, source_id="x")
    b = _node("high", 0.9, source_id="y")
    c = _node("mid", 0.5, source_id="z")
    merged = multi_query.merge_results([(a, c, b)])
    scores = [n.score for n in merged]
    assert scores == sorted(scores, reverse=True)


def test_merge_results_empty_groups():
    assert multi_query.merge_results([]) == ()
    assert multi_query.merge_results([()]) == ()


def test_node_key_falls_back_to_text_when_no_id():
    n = _node("unique text here", 0.5)
    key = multi_query._node_key(n)
    assert "unique text here" in key


# ── retrieve_multi ─────────────────────────────────────────────────────────────


def _make_outcome(
    nodes: tuple[orchestrator.RetrievedNode, ...],
    bypass: bool = True,
) -> orchestrator.RetrievalOutcome:
    return orchestrator.RetrievalOutcome(
        nodes=nodes,
        bypass_rerank=bypass,
        rerank_reason="test",
        rerank_elapsed_ms=0,
    )


def test_retrieve_multi_merges_variant_results():
    """Each variant returns distinct nodes; retrieve_multi surfaces all."""
    n1 = _node("doc A", 0.9, source_id="a")
    n2 = _node("doc B", 0.7, source_id="b")

    call_count = [0]

    def _fake_retrieve(**_kw):
        call_count[0] += 1
        if call_count[0] == 1:
            return _make_outcome((n1,))
        return _make_outcome((n2,))

    with (
        patch.object(multi_query, "generate_variants", return_value=["q1", "q2"]),
        patch("src.retrieval.orchestrator.retrieve_with_outcome", side_effect=_fake_retrieve),
    ):
        outcome = multi_query.retrieve_multi(
            "original",
            collections=("Discoveries",),
            k_initial=20,
            k_returned=5,
            tenant_id="default",
        )
    source_ids = {n.metadata.get("source_id") for n in outcome.nodes}
    assert source_ids == {"a", "b"}


def test_retrieve_multi_deduplicates_across_variants():
    """Same node returned by two variants → appears only once in merged result."""
    shared = _node("shared doc", 0.8, source_id="shared")

    with (
        patch.object(multi_query, "generate_variants", return_value=["v1", "v2", "v3"]),
        patch(
            "src.retrieval.orchestrator.retrieve_with_outcome",
            return_value=_make_outcome((shared,)),
        ),
    ):
        outcome = multi_query.retrieve_multi(
            "query",
            collections=("Discoveries",),
            k_initial=20,
            k_returned=5,
            tenant_id="default",
        )
    assert len(outcome.nodes) == 1


def test_retrieve_multi_respects_k_returned():
    """Merged result is capped at k_returned nodes."""
    nodes = tuple(_node(f"doc {i}", 0.5, source_id=f"id{i}") for i in range(10))

    with (
        patch.object(multi_query, "generate_variants", return_value=["v1"]),
        patch(
            "src.retrieval.orchestrator.retrieve_with_outcome",
            return_value=_make_outcome(nodes),
        ),
    ):
        outcome = multi_query.retrieve_multi(
            "query",
            collections=("Discoveries",),
            k_initial=20,
            k_returned=3,
            tenant_id="default",
        )
    assert len(outcome.nodes) == 3


def test_retrieve_multi_all_searches_fail_returns_empty():
    """If every variant search raises, retrieve_multi returns empty outcome."""
    with (
        patch.object(multi_query, "generate_variants", return_value=["v1", "v2"]),
        patch(
            "src.retrieval.orchestrator.retrieve_with_outcome",
            side_effect=Exception("hindsight down"),
        ),
    ):
        outcome = multi_query.retrieve_multi(
            "query",
            collections=("Discoveries",),
            k_initial=20,
            k_returned=5,
            tenant_id="default",
        )
    assert outcome.nodes == ()
    assert outcome.rerank_reason == "multi_query_all_failed"


# ── agent_query integration ────────────────────────────────────────────────────


def test_agent_query_uses_multi_query_when_enabled(monkeypatch):
    """With RETRIEVAL_MULTI_QUERY_ENABLED=1, agent_query.query() calls retrieve_multi."""
    monkeypatch.setenv(multi_query.MULTI_QUERY_ENABLED_ENV, "1")

    n = _node("multi result", 0.85, source_id="mq-1")
    mq_outcome = _make_outcome((n,))

    from src.retrieval import agent_query

    with patch.object(multi_query, "retrieve_multi", return_value=mq_outcome) as mock_mq:
        result = agent_query.query("test", agent="max")
    mock_mq.assert_called_once()
    assert result.citations[0].source_id == "mq-1"


def test_agent_query_uses_single_query_when_flag_off(monkeypatch):
    """With RETRIEVAL_MULTI_QUERY_ENABLED unset, agent_query.query() uses direct orchestrator."""
    monkeypatch.delenv(multi_query.MULTI_QUERY_ENABLED_ENV, raising=False)

    n = _node("single result", 0.75, source_id="sq-1")
    sq_outcome = _make_outcome((n,))

    from src.retrieval import agent_query

    with (
        patch(
            "src.retrieval.agent_query.orchestrator.retrieve_with_outcome", return_value=sq_outcome
        ) as mock_orch,
        patch.object(multi_query, "retrieve_multi") as mock_mq,
    ):
        result = agent_query.query("test", agent="max")
    mock_orch.assert_called_once()
    mock_mq.assert_not_called()
    assert result.citations[0].source_id == "sq-1"
