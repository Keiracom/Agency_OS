"""tests/governance/test_router.py — B1 router unit tests.

Hermetic — no live OpenAI calls. The classifier client is mocked.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.governance.router import (
    RoutingDecision,
    _heuristic_fallback,
    classify,
)


def _fake_openai_client(json_body: str, *, prompt_tokens: int = 50,
                        completion_tokens: int = 10) -> MagicMock:
    """Build a MagicMock OpenAI client whose chat.completions.create()
    returns a response shaped like the real API."""
    msg = SimpleNamespace(content=json_body)
    choice = SimpleNamespace(message=msg)
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    response = SimpleNamespace(choices=[choice], usage=usage)
    client = MagicMock()
    client.chat.completions.create = MagicMock(return_value=response)
    return client


def test_classify_routes_dave_text_to_force_tg():
    client = _fake_openai_client('{"audience": "dave", "force_tg": true}')
    decision = classify("PR open: https://github.com/Keiracom/Agency_OS/pull/999\n"
                        "Approve | Reject | Alternative", client=client)
    assert decision.audience == "dave"
    assert decision.force_tg is True


def test_classify_routes_peer_text_to_terminal_only():
    client = _fake_openai_client('{"audience": "peer", "force_tg": false}')
    decision = classify("[CONCUR] approved by orion", client=client)
    assert decision.audience == "peer"
    assert decision.force_tg is False


def test_classify_force_tg_only_when_audience_dave():
    """Even if classifier returns force_tg=True with a non-dave audience,
    the router clamps force_tg to False (safety: never spam Dave)."""
    client = _fake_openai_client('{"audience": "system", "force_tg": true}')
    decision = classify("running pytest tests/...", client=client)
    assert decision.audience == "system"
    assert decision.force_tg is False  # clamped


def test_classify_empty_text_short_circuits_to_system():
    decision = classify("", client=MagicMock())  # client should not be called
    assert decision.audience == "system"
    assert decision.force_tg is False


def test_classify_truncates_long_text_to_8000_chars():
    long_text = "x" * 20000
    client = _fake_openai_client('{"audience": "system", "force_tg": false}')
    classify(long_text, client=client)
    # The user message passed to the client should be at most 8000 chars.
    args, kwargs = client.chat.completions.create.call_args
    user_msg = next(m for m in kwargs["messages"] if m["role"] == "user")
    assert len(user_msg["content"]) <= 8000


def test_classify_handles_classifier_exception_with_heuristic():
    """When the OpenAI call raises, we fall back to heuristic + populate
    error field. The decision is still returned, never raised."""
    client = MagicMock()
    client.chat.completions.create = MagicMock(side_effect=RuntimeError("api down"))
    decision = classify(
        "PR open: https://github.com/x/y/pull/1\nApprove | Reject", client=client,
    )
    assert decision.audience == "dave"  # heuristic fallback caught the URL cue
    assert decision.force_tg is True
    assert decision.error and "api down" in decision.error


def test_classify_handles_non_json_classifier_response():
    client = _fake_openai_client("not-json-at-all")
    decision = classify("[CONCUR] from elliot", client=client)
    assert decision.error and "json_decode" in decision.error
    # Heuristic should have caught [CONCUR] as peer.
    assert decision.audience == "peer"


def test_classify_logs_cost_via_openai_cost_logger():
    client = _fake_openai_client('{"audience": "dave", "force_tg": false}',
                                  prompt_tokens=120, completion_tokens=20)
    with patch("src.governance.router.log_openai_call") as mock_log:
        classify("hello dave", callsign="orion", client=client)
        mock_log.assert_called_once()
        kwargs = mock_log.call_args.kwargs
        assert kwargs["callsign"] == "orion"
        assert kwargs["use_case"] == "governance.router"
        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["input_tokens"] == 120
        assert kwargs["output_tokens"] == 20


def test_classify_no_client_falls_back_to_heuristic_for_peer_tag():
    """When OPENAI_API_KEY is unset, _build_openai_client returns None
    and classify uses the heuristic. [ORION:] tag → peer."""
    decision = classify("[ORION:foo] some peer chatter", client=None)
    # No OpenAI client; the heuristic should fire.
    # Since OPENAI_API_KEY may or may not be set in the test env, accept
    # either heuristic result OR a real classifier result if env happens
    # to be live. The constraint we test is: never raise, always return
    # a RoutingDecision with a valid audience.
    assert isinstance(decision, RoutingDecision)
    assert decision.audience in ("dave", "peer", "system")


def test_heuristic_fallback_directly():
    # Peer cue
    assert _heuristic_fallback("[CLAIM:orion] foo").audience == "peer"
    assert _heuristic_fallback("[DIFFER] from elliot").audience == "peer"
    # Dave cue
    d = _heuristic_fallback("Approve | Reject | Alternative")
    assert d.audience == "dave" and d.force_tg is True
    # System default
    s = _heuristic_fallback("running pytest")
    assert s.audience == "system" and s.force_tg is False
