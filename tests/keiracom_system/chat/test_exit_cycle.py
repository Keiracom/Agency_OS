"""Unit tests for John's exit cycle — mock Gemini + mock DB writer.

Uses asyncio.run so the suite needs no pytest-asyncio mode configuration.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.keiracom_system.chat import exit_cycle


class FakeGemini:
    """Stub GeminiClient.comprehend returning a canned result (or raising)."""

    def __init__(self, result: Any = None, *, raises: Exception | None = None) -> None:
        self._result = result
        self._raises = raises
        self.calls: list[dict[str, Any]] = []

    async def comprehend(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self._raises is not None:
            raise self._raises
        return self._result


def _recorder():
    calls: list[tuple[str, str, dict]] = []

    def writer(callsign: str, key: str, value: dict) -> None:
        calls.append((callsign, key, value))

    return writer, calls


def _success(items: list[dict]) -> dict[str, Any]:
    return {"f3_status": "success", "content": {"items": items}}


def _run(conversation, *, gemini, writer, customer_id=42):
    return asyncio.run(
        exit_cycle.classify_and_save(conversation, customer_id, gemini_client=gemini, writer=writer)
    )


CONVO = [
    {"role": "viktor", "content": "We will use Hindsight Layer 2 for cross-spawn recall."},
    {"role": "user", "content": "Go ahead, confirmed."},
]


def test_happy_path_writes_qualifying_items():
    gemini = FakeGemini(
        _success(
            [
                {
                    "decision_text": "Use Hindsight Layer 2 for cross-spawn recall.",
                    "topic_slug": "hindsight-layer-2-recall",
                    "kind": "architectural_decision",
                    "confidence": 0.95,
                },
                {
                    "decision_text": "Dave confirmed the recall direction.",
                    "topic_slug": "dave-approval-recall",
                    "kind": "dave_approval",
                    "confidence": 0.9,
                },
            ]
        )
    )
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.decisions_saved == 2
    assert result.skipped_reason is None
    assert len(calls) == 2
    callsign, key, value = calls[0]
    assert callsign == "john"
    assert key.startswith("ceo:conversation_capture:")
    assert "hindsight-layer-2-recall" in key
    assert value["kind"] == "architectural_decision"
    assert value["customer_id"] == 42
    assert value["captured_by"] == "john_exit_cycle"
    assert result.keys_written == [c[1] for c in calls]


def test_below_confidence_threshold_skips():
    gemini = FakeGemini(
        _success(
            [
                {
                    "decision_text": "Maybe use X.",
                    "topic_slug": "maybe-x",
                    "kind": "architectural_decision",
                    "confidence": 0.6,
                }
            ]
        )
    )
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.decisions_saved == 0
    assert result.skipped_reason == "below_confidence_threshold"
    assert calls == []


def test_confidence_exactly_threshold_excluded():
    gemini = FakeGemini(
        _success(
            [
                {
                    "decision_text": "Boundary case.",
                    "topic_slug": "boundary",
                    "kind": "confirmed_pattern",
                    "confidence": 0.8,
                }
            ]
        )
    )
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.skipped_reason == "below_confidence_threshold"
    assert calls == []


def test_max_three_writes_cap():
    items = [
        {
            "decision_text": f"Decision number {i}.",
            "topic_slug": f"decision-{i}",
            "kind": "architectural_decision",
            "confidence": 0.99,
        }
        for i in range(5)
    ]
    gemini = FakeGemini(_success(items))
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.decisions_saved == 3
    assert len(calls) == 3


def test_invalid_kind_filtered():
    gemini = FakeGemini(
        _success(
            [
                {
                    "decision_text": "Routine status update.",
                    "topic_slug": "status",
                    "kind": "status_update",
                    "confidence": 0.99,
                }
            ]
        )
    )
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.skipped_reason == "below_confidence_threshold"
    assert calls == []


def test_empty_conversation_skips_without_gemini_call():
    gemini = FakeGemini(_success([]))
    writer, calls = _recorder()
    result = _run([], gemini=gemini, writer=writer)
    assert result.skipped_reason == "empty_conversation"
    assert gemini.calls == []
    assert calls == []


def test_no_decisions_detected():
    gemini = FakeGemini(_success([]))
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.skipped_reason == "no_decisions_detected"
    assert calls == []


def test_gemini_failure_is_fail_open():
    gemini = FakeGemini(raises=RuntimeError("gemini 503"))
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.decisions_saved == 0
    assert result.skipped_reason is not None
    assert result.skipped_reason.startswith("classify_failed")
    assert calls == []


def test_gemini_non_success_status_yields_no_writes():
    gemini = FakeGemini({"f3_status": "failed", "content": {}})
    writer, calls = _recorder()
    result = _run(CONVO, gemini=gemini, writer=writer)
    assert result.skipped_reason == "no_decisions_detected"
    assert calls == []


def test_db_write_failure_is_fail_open():
    gemini = FakeGemini(
        _success(
            [
                {
                    "decision_text": "Use Hindsight Layer 2.",
                    "topic_slug": "hindsight-l2",
                    "kind": "architectural_decision",
                    "confidence": 0.95,
                }
            ]
        )
    )

    def boom(callsign: str, key: str, value: dict) -> None:
        raise ConnectionError("db down")

    result = _run(CONVO, gemini=gemini, writer=boom)
    assert result.decisions_saved == 0
    assert result.skipped_reason == "all_writes_failed"


def test_partial_write_failure_counts_successes():
    gemini = FakeGemini(
        _success(
            [
                {
                    "decision_text": "First decision.",
                    "topic_slug": "first",
                    "kind": "architectural_decision",
                    "confidence": 0.95,
                },
                {
                    "decision_text": "Second decision.",
                    "topic_slug": "second",
                    "kind": "confirmed_pattern",
                    "confidence": 0.95,
                },
            ]
        )
    )
    seen: list[str] = []

    def flaky(callsign: str, key: str, value: dict) -> None:
        if "second" in key:
            raise ConnectionError("transient")
        seen.append(key)

    result = _run(CONVO, gemini=gemini, writer=flaky)
    assert result.decisions_saved == 1
    assert len(result.keys_written) == 1
    assert "first" in result.keys_written[0]


def test_classify_passes_response_schema_and_no_grounding():
    gemini = FakeGemini(_success([]))
    writer, _ = _recorder()
    _run(CONVO, gemini=gemini, writer=writer)
    assert gemini.calls, "comprehend should have been called"
    kwargs = gemini.calls[0]
    assert kwargs["enable_grounding"] is False
    assert kwargs["response_schema"] is exit_cycle.RESPONSE_SCHEMA
    assert "viktor:" in kwargs["user_prompt"]  # roles rendered into the prompt
