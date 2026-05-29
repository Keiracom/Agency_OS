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
    # 'task' now triggers a NATS dispatch — inject a no-op so the test doesn't
    # try to reach a real NATS server.
    convo = face.run_conversation(
        ["set up X", "and Y"], 7, classify=classify, dispatch=lambda **_kw: True
    )
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


# ---------------------------------------------------------------------------
# zr7e.1 — Face → Aiden NATS dispatch on classification == 'task'
# ---------------------------------------------------------------------------


def test_respond_task_dispatches_and_confirms():
    """'task' → dispatch fires once with the brief; reply confirms the dispatch."""
    calls: list[dict[str, Any]] = []

    def _ok_dispatch(**kw: Any) -> bool:
        calls.append(kw)
        return True

    reply = face._respond(_ctx("task"), "set up X", dispatch=_ok_dispatch)
    assert "Dispatching to Aiden" in reply
    assert "set up X" in reply
    assert len(calls) == 1
    assert calls[0]["brief"] == "set up X"
    # task_id is a uuid4 hex-shape string (deterministic only in length/shape).
    assert isinstance(calls[0]["task_id"], str) and len(calls[0]["task_id"]) == 36
    assert calls[0]["atom_id"] is None  # V1: Face has no atom_id yet (zr7e.9 follows)


def test_respond_task_dispatch_failure_returns_retry():
    """Dispatch returning False → 'Dispatch failed — try again', never raises."""

    def _fail_dispatch(**_kw: Any) -> bool:
        return False

    reply = face._respond(_ctx("task"), "do the thing", dispatch=_fail_dispatch)
    assert reply == "Dispatch failed — try again."


def test_respond_non_task_does_not_dispatch():
    """Non-'task' classifications must not call dispatch (fast path, no NATS)."""

    def _explode(**_kw: Any) -> bool:
        raise AssertionError("dispatch must not be called for non-'task' classifications")

    # technical, escalation, ambiguous — none should dispatch.
    assert "technical" in face._respond(_ctx("technical"), "what is X", dispatch=_explode)
    assert "escalation" in face._respond(_ctx("escalation"), "urgent!", dispatch=_explode)
    assert "Escalating" in face._respond(_ctx("ambiguous"), "?", dispatch=_explode)


def test_dispatch_to_aiden_publishes_correct_envelope(monkeypatch):
    """_dispatch_to_aiden publishes to the canonical subject with full payload."""
    captured: dict[str, Any] = {}

    class _FakeNC:
        async def connect(self, url, connect_timeout=2):  # noqa: ARG002 — sig match
            captured["url"] = url

        async def publish(self, subject, payload):
            captured["subject"] = subject
            captured["payload"] = payload

        async def flush(self):
            captured["flushed"] = True

        async def close(self):
            captured["closed"] = True

    monkeypatch.setattr("nats.aio.client.Client", lambda: _FakeNC())

    ok = face._dispatch_to_aiden(brief="ship it", task_id="t-1", atom_id=None)

    assert ok is True
    assert captured["subject"] == face.DISPATCH_SUBJECT == "keiracom.dispatch.aiden"
    assert captured["url"] == face.NATS_URL
    assert captured["flushed"] is True and captured["closed"] is True
    import json as _json

    body = _json.loads(captured["payload"].decode())
    assert body["type"] == "task_dispatch"
    assert body["task_id"] == "t-1"
    assert body["atom_id"] is None
    assert body["from_callsign"] == "face"
    assert body["to_callsign"] == "aiden"
    assert body["brief"] == "ship it"
    assert isinstance(body["ts"], int)


def test_dispatch_to_aiden_fail_open_on_nats_error(monkeypatch):
    """NATS connect/publish failure → False, no exception escapes."""

    class _BoomNC:
        async def connect(self, url, connect_timeout=2):  # noqa: ARG002
            raise OSError("nats unreachable")

        async def publish(self, *a, **kw): ...
        async def flush(self): ...
        async def close(self): ...

    monkeypatch.setattr("nats.aio.client.Client", lambda: _BoomNC())

    # Must not raise; must return False.
    assert face._dispatch_to_aiden(brief="x", task_id="t-2") is False


def test_respond_task_uses_face_task_id_when_set(monkeypatch):
    """FACE_TASK_ID env from the dispatcher is used as the dispatch task_id,
    so Aiden's work is attributable back to the original Postgres tasks row
    (PR #1312 cost-attribution path)."""
    calls: list[dict[str, Any]] = []

    def _ok(**kw: Any) -> bool:
        calls.append(kw)
        return True

    monkeypatch.setattr(face, "FACE_TASK_ID", "t-9999")
    reply = face._respond(_ctx("task"), "set up X", dispatch=_ok)
    assert "Dispatching to Aiden" in reply
    assert calls[0]["task_id"] == "t-9999"


def test_respond_task_falls_back_to_uuid4_when_face_task_id_unset(monkeypatch):
    """When FACE_TASK_ID is None, manual invocations still work — task_id is
    a fresh uuid4 string."""
    calls: list[dict[str, Any]] = []

    def _ok(**kw: Any) -> bool:
        calls.append(kw)
        return True

    monkeypatch.setattr(face, "FACE_TASK_ID", None)
    face._respond(_ctx("task"), "x", dispatch=_ok)
    tid = calls[0]["task_id"]
    assert isinstance(tid, str) and len(tid) == 36 and tid.count("-") == 4
