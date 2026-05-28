"""Unit tests for src/keiracom_system/chat/context_composer.

Both external dependencies are injected: Gemini via a fake LLMClient
(call_structured), Hindsight via a recording retrieve_fn. No live API key,
no Weaviate/Hindsight, no LiteLLM proxy needed.
"""

from __future__ import annotations

from typing import Any

from src.keiracom_system.atomization.llm_client import LLMResponse
from src.keiracom_system.chat import context_composer as cc
from src.retrieval.agent_query import Citation, QueryResult


class _FakeLLM:
    """Canned classifier — returns `parsed`, or raises if `boom` is set."""

    def __init__(self, parsed: Any = None, *, boom: bool = False):
        self.parsed = parsed
        self.boom = boom
        self.calls: list[dict] = []

    def call_structured(self, **kwargs):
        self.calls.append(kwargs)
        if self.boom:
            raise RuntimeError("gemini down")
        return LLMResponse(parsed=self.parsed, tokens_in=10, tokens_out=2, latency_ms=5, model="x")


class _RecordingRetrieve:
    """Records (query_text, collections); returns a canned QueryResult or raises."""

    def __init__(self, result: QueryResult | None = None, *, boom: bool = False):
        self.result = result
        self.boom = boom
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def __call__(self, query_text: str, collections: tuple[str, ...]):
        self.calls.append((query_text, collections))
        if self.boom:
            raise RuntimeError("hindsight down")
        return self.result


def _result(*citations: Citation, answer: str = "synthesised answer") -> QueryResult:
    return QueryResult(answer=answer, citations=tuple(citations), elapsed_ms=1, bypass_rerank=True)


def _cite(source_id: str = "DEC-1", collection: str = "Decisions") -> Citation:
    return Citation(
        source_id=source_id, collection=collection, score=0.81, excerpt="how scoring works"
    )


def _llm(label: str) -> _FakeLLM:
    return _FakeLLM({"classification": label})


# --- classification → collection routing -------------------------------


def test_technical_routes_to_decisions_and_agent_memories():
    retrieve = _RecordingRetrieve(_result(_cite()))
    res = cc.compose_chat_context(
        "how does CIS scoring work?", 42, [], llm_client=_llm("technical"), retrieve_fn=retrieve
    )
    assert res.classification == "technical"
    assert retrieve.calls[0][1] == ("Decisions", "AgentMemories")
    assert res.citations and res.citations[0]["source_id"] == "DEC-1"
    assert "[DYNAMIC CONTEXT — technical]" in res.context_block
    assert "how scoring works" in res.context_block
    assert res.token_estimate == len(res.context_block) // 4


def test_task_routes_to_decisions_and_keis():
    retrieve = _RecordingRetrieve(_result(_cite("KEI-9", "Keis")))
    res = cc.compose_chat_context(
        "set up a new campaign", 7, [], llm_client=_llm("task"), retrieve_fn=retrieve
    )
    assert res.classification == "task"
    assert retrieve.calls[0][1] == ("Decisions", "Keis")


def test_escalation_routes_to_agent_memories_with_customer_context():
    retrieve = _RecordingRetrieve(_result(_cite("MEM-3", "AgentMemories")))
    res = cc.compose_chat_context(
        "this is unacceptable, get me a manager",
        99,
        [],
        llm_client=_llm("escalation"),
        retrieve_fn=retrieve,
    )
    assert res.classification == "escalation"
    query_text, collections = retrieve.calls[0]
    assert collections == ("AgentMemories",)
    assert "customer 99" in query_text  # biased toward this customer's prior context


# --- ambiguous + fail-open ---------------------------------------------


def test_ambiguous_returns_failopen_block_and_skips_retrieval():
    retrieve = _RecordingRetrieve(_result(_cite()))
    res = cc.compose_chat_context("hmm", 1, [], llm_client=_llm("ambiguous"), retrieve_fn=retrieve)
    assert res.classification == "ambiguous"
    assert res.context_block == cc.AMBIGUOUS_BLOCK
    assert res.citations == []
    assert retrieve.calls == []  # no retrieval on ambiguous


def test_classification_failure_falls_open_to_ambiguous():
    retrieve = _RecordingRetrieve(_result(_cite()))
    res = cc.compose_chat_context(
        "anything", 1, [], llm_client=_FakeLLM(boom=True), retrieve_fn=retrieve
    )
    assert res.classification == "ambiguous"
    assert res.context_block == cc.AMBIGUOUS_BLOCK
    assert retrieve.calls == []


def test_unknown_label_falls_open_to_ambiguous():
    res = cc.compose_chat_context(
        "x", 1, [], llm_client=_llm("banana"), retrieve_fn=_RecordingRetrieve(_result())
    )
    assert res.classification == "ambiguous"
    assert res.context_block == cc.AMBIGUOUS_BLOCK


def test_retrieval_failure_returns_empty_block_not_exception():
    retrieve = _RecordingRetrieve(boom=True)
    res = cc.compose_chat_context(
        "how does X work?", 1, [], llm_client=_llm("technical"), retrieve_fn=retrieve
    )
    assert res.classification == "technical"  # classified fine
    assert res.context_block == ""  # retrieval failed → empty, no raise
    assert res.citations == []


# --- token budget ------------------------------------------------------


def test_context_block_capped_at_800_tokens():
    huge = _result(_cite(), answer="x" * 100_000)
    res = cc.compose_chat_context(
        "big", 1, [], llm_client=_llm("technical"), retrieve_fn=_RecordingRetrieve(huge)
    )
    assert len(res.context_block) // 4 <= cc.MAX_CONTEXT_TOKENS
    assert res.token_estimate <= cc.MAX_CONTEXT_TOKENS


def test_history_passed_to_classifier():
    llm = _llm("technical")
    cc.compose_chat_context(
        "now what?",
        1,
        ["earlier msg A", "earlier msg B"],
        llm_client=llm,
        retrieve_fn=_RecordingRetrieve(_result()),
    )
    prompt = llm.calls[0]["messages"][0]["content"]
    assert "earlier msg B" in prompt  # recent turns fed in for disambiguation
