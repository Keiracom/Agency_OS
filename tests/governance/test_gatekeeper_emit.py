"""GOV-PHASE2 — Gatekeeper verdict emit instrumentation tests."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.governance import gatekeeper


@pytest.fixture
def common_args() -> dict:
    return {
        "callsign": "aiden-test",
        "directive_id": "GOV-PHASE2-TEST",
        "claim_text": "synthetic completion claim",
        "evidence": "$ pytest -q\nOK",
        "target_files": ["src/foo.py"],
        "store_writes": [],
        "frozen_paths": [],
    }


def test_emit_on_allow_true(common_args: dict) -> None:
    with patch.object(gatekeeper, "_post_decision",
                      return_value={"allow": True, "deny_reasons": []}), \
         patch("src.governance._mcp_helpers.governance_event_emit") as emit:
        result = gatekeeper.check_completion_claim(**common_args)
    assert result.allow is True
    assert emit.call_count == 1
    kwargs = emit.call_args.kwargs
    assert kwargs["event_type"] == "gatekeeper_decision"
    assert kwargs["event_data"]["allow"] is True
    assert kwargs["directive_id"] == "GOV-PHASE2-TEST"


def test_emit_on_deny(common_args: dict) -> None:
    with patch.object(gatekeeper, "_post_decision",
                      return_value={"allow": False, "deny_reasons": ["G2 fail"]}), \
         patch("src.governance._mcp_helpers.governance_event_emit") as emit:
        result = gatekeeper.check_completion_claim(**common_args)
    assert result.allow is False
    assert result.reasons == ["G2 fail"]
    assert emit.call_args.kwargs["event_data"]["allow"] is False
    assert emit.call_args.kwargs["event_data"]["reasons"] == ["G2 fail"]


def test_emit_on_opa_error(common_args: dict) -> None:
    with patch.object(gatekeeper, "_post_decision",
                      side_effect=httpx.ConnectError("boom")), \
         patch("src.governance._mcp_helpers.governance_event_emit") as emit:
        result = gatekeeper.check_completion_claim(**common_args)
    assert result.allow is False
    assert emit.call_count == 1
    assert emit.call_args.kwargs["event_data"]["error"] == "boom"
