"""Unit tests for John's exit cycle — direct-write to Hindsight fleet_decisions.

Mocks Gemini + an injected ingest_fn (no live Hindsight POST). Uses asyncio.run
so the suite needs no pytest-asyncio mode configuration.
"""

from __future__ import annotations

import asyncio
import json
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
    """Record each (bank, items) ingest batch."""
    calls: list[tuple[str, list[dict]]] = []

    def ingest(bank: str, items: list[dict]) -> None:
        calls.append((bank, items))

    return ingest, calls


def _success(items: list[dict]) -> dict[str, Any]:
    return {"f3_status": "success", "content": {"items": items}}


def _run(conversation, *, gemini, ingest_fn, customer_id=42):
    return asyncio.run(
        exit_cycle.classify_and_save(
            conversation, customer_id, gemini_client=gemini, ingest_fn=ingest_fn
        )
    )


CONVO = [
    {"role": "viktor", "content": "We will use Hindsight Layer 2 for cross-spawn recall."},
    {"role": "user", "content": "Go ahead, confirmed."},
]


def test_happy_path_writes_atoms_to_fleet_decisions():
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
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert result.decisions_saved == 2
    assert result.bank == "fleet_decisions"
    assert result.skipped_reason is None
    assert len(result.atom_ids) == 2
    # All atoms land in a SINGLE batch POST to fleet_decisions.
    assert len(calls) == 1
    bank, items = calls[0]
    assert bank == "fleet_decisions"
    assert len(items) == 2
    first = items[0]
    assert first["content"] == "Use Hindsight Layer 2 for cross-spawn recall."
    assert "atom_v1" in first["tags"]
    assert "state:active" in first["tags"]
    assert "schema_v1" in first["tags"]
    # decision composition tags retrievable as a class
    assert "internal" in first["tags"] and "compliance" in first["tags"]
    assert "audit_review" in first["tags"]
    assert first["metadata"]["source"] == "live_spawn_exit"
    trig = json.loads(first["metadata"]["trigger_condition"])
    assert trig["kind"] == "context_predicate"
    assert trig["params"]["decision_kind"] == "architectural_decision"


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
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
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
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
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
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert result.decisions_saved == 3
    assert len(calls) == 1
    _, batch = calls[0]
    assert len(batch) == 3


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
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert result.skipped_reason == "below_confidence_threshold"
    assert calls == []


def test_empty_conversation_skips_without_gemini_call():
    gemini = FakeGemini(_success([]))
    ingest, calls = _recorder()
    result = _run([], gemini=gemini, ingest_fn=ingest)
    assert result.skipped_reason == "empty_conversation"
    assert gemini.calls == []
    assert calls == []


def test_no_decisions_detected():
    gemini = FakeGemini(_success([]))
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert result.skipped_reason == "no_decisions_detected"
    assert calls == []


def test_gemini_failure_is_fail_open():
    gemini = FakeGemini(raises=RuntimeError("gemini 503"))
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert result.decisions_saved == 0
    assert result.skipped_reason is not None
    assert result.skipped_reason.startswith("classify_failed")
    assert calls == []


def test_gemini_non_success_status_yields_no_writes():
    gemini = FakeGemini({"f3_status": "failed", "content": {}})
    ingest, calls = _recorder()
    result = _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert result.skipped_reason == "no_decisions_detected"
    assert calls == []


def test_ingest_failure_is_fail_open():
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

    def boom(bank: str, items: list[dict]) -> None:
        raise ConnectionError("hindsight down")

    result = _run(CONVO, gemini=gemini, ingest_fn=boom)
    assert result.decisions_saved == 0
    assert result.skipped_reason is not None
    assert result.skipped_reason.startswith("ingest_failed")


def test_classify_passes_response_schema_and_no_grounding():
    gemini = FakeGemini(_success([]))
    ingest, _ = _recorder()
    _run(CONVO, gemini=gemini, ingest_fn=ingest)
    assert gemini.calls, "comprehend should have been called"
    kwargs = gemini.calls[0]
    assert kwargs["enable_grounding"] is False
    assert kwargs["response_schema"] is exit_cycle.RESPONSE_SCHEMA
    assert "viktor:" in kwargs["user_prompt"]  # roles rendered into the prompt
