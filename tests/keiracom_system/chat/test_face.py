"""Unit tests for the Face entrypoint (src.keiracom_system.chat.face).

Drives the classify→respond loop and the exit-cycle call with injected seams —
no live Gemini, Hindsight, or stdin. Mirrors test_exit_cycle's asyncio.run style
so the suite needs no pytest-asyncio config.
"""

from __future__ import annotations

from typing import Any

from src.keiracom_system.chat import face
from src.keiracom_system.chat.context_composer import ChatContextResult
from src.keiracom_system.chat.exit_cycle import ExitCycleResult


def _ctx(classification: str) -> ChatContextResult:
    return ChatContextResult(
        context_block="ctx", classification=classification, citations=[], token_estimate=1
    )


def _classify(classification: str):
    """A compose_chat_context stub that always returns `classification`."""
    seen: list[tuple[str, int, list[str]]] = []

    def _c(message: str, customer_id: int, history: list[str]) -> ChatContextResult:
        seen.append((message, customer_id, list(history)))
        return _ctx(classification)

    return _c, seen


def _save_recorder(skipped: str | None = "test"):
    calls: list[tuple[list[dict[str, str]], int]] = []

    async def _s(conversation: list[dict[str, str]], customer_id: int) -> ExitCycleResult:
        calls.append((conversation, customer_id))
        return ExitCycleResult(skipped_reason=skipped)

    return _s, calls


def test_respond_ambiguous_escalates():
    assert "Escalating" in face._respond(_ctx("ambiguous"))


def test_respond_routes_by_classification():
    reply = face._respond(_ctx("technical"))
    assert "technical" in reply
    assert "Escalating" not in reply


def test_run_conversation_builds_transcript_and_passes_history():
    classify, seen = _classify("task")
    convo = face.run_conversation(["set up X", "and Y"], 7, classify=classify)
    # user+assistant per message
    assert [m["role"] for m in convo] == ["user", "assistant", "user", "assistant"]
    assert convo[0]["content"] == "set up X"
    # second classify call sees the first user message as history
    assert seen[1][2] == ["set up X"]
    assert seen[0][1] == 7  # customer_id threaded through


def test_run_conversation_stops_on_exit_sentinel():
    classify, seen = _classify("technical")
    convo = face.run_conversation(["hello", "exit", "ignored"], 1, classify=classify)
    assert len(seen) == 1  # only "hello" classified
    assert len(convo) == 2


def test_run_calls_exit_cycle_with_full_transcript():
    classify, _ = _classify("escalation")
    save, calls = _save_recorder()
    rc = face.run(briefs=lambda: ["I'm unhappy"], classify=classify, save=save)
    assert rc == 0
    assert len(calls) == 1
    conversation, _customer_id = calls[0]
    assert conversation[0] == {"role": "user", "content": "I'm unhappy"}
    assert conversation[1]["role"] == "assistant"


def test_run_empty_brief_still_runs_exit_cycle():
    save, calls = _save_recorder(skipped="empty_conversation")
    rc = face.run(briefs=lambda: [], classify=_classify("task")[0], save=save)
    assert rc == 0
    assert calls == [([], face.DEFAULT_CUSTOMER_ID)]


def test_run_returns_zero_even_when_exit_cycle_skips():
    """Fail-open: a skipped exit cycle must not change the process exit code."""

    async def _skip(conversation: Any, customer_id: int) -> ExitCycleResult:
        return ExitCycleResult(skipped_reason="ingest_failed: boom")

    rc = face.run(briefs=lambda: ["hi"], classify=_classify("technical")[0], save=_skip)
    assert rc == 0
