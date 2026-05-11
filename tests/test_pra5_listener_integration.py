"""tests for Drevon PR-A.5 listener integration (replay-on-claim post-LLM hook).

Mocks the LLM result + replay verifier to assert run_enforcer correctly:
  - Calls verify_completion_claim when REPLAY_ON_CLAIM_ENABLED=1
  - Skips the call when env unset (default disabled)
  - Suppresses R3 violation on verified=True
  - Confirms R3 violation on verified=False (proceeds to _fire_violation)
  - Falls through on replay exception (best-effort, never breaks enforcer)

Stubs slack_sdk so the module loads in test env without the SDK installed.
"""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import patch

import pytest

# Stub slack_sdk before module import (same pattern as PR #711)
for mod_name in (
    "slack_sdk",
    "slack_sdk.socket_mode",
    "slack_sdk.socket_mode.request",
    "slack_sdk.socket_mode.response",
    "slack_sdk.web",
):
    sys.modules.setdefault(mod_name, types.ModuleType(mod_name))
sys.modules["slack_sdk.socket_mode"].SocketModeClient = type("SocketModeClient", (), {})  # type: ignore[attr-defined]
sys.modules["slack_sdk.socket_mode.request"].SocketModeRequest = type("SocketModeRequest", (), {})  # type: ignore[attr-defined]
sys.modules["slack_sdk.socket_mode.response"].SocketModeResponse = type(
    "SocketModeResponse", (), {}
)  # type: ignore[attr-defined]
sys.modules["slack_sdk.web"].WebClient = type("WebClient", (), {})  # type: ignore[attr-defined]

from src.slack_bot import central_listener  # noqa: E402


@pytest.fixture
def fake_event() -> dict:
    return {
        "channel": central_listener.LISTEN_CHANNEL,
        "user": "U123",
        "type": "message",
        "text": "PR #715 merged at 2026-05-11T23:21:31Z",
    }


@pytest.fixture
def llm_r3_violation():
    """Force the LLM check to return an R3 violation."""
    with patch.object(
        central_listener,
        "check_with_llm",
        return_value={"violation": True, "rule_number": 3, "rule_name": "R3"},
    ):
        yield


@pytest.fixture
def always_should_check():
    """Force should_check to return True (text qualifies for enforcer)."""
    with patch.object(central_listener, "should_check", return_value=True):
        yield


@pytest.fixture
def attribute_aiden():
    """attribute(event) → 'aiden' (so the enforcer/dave early-returns don't fire)."""
    with patch.object(central_listener, "attribute", return_value="aiden"):
        yield


@pytest.fixture
def fire_capture():
    """Capture _fire_violation calls."""
    calls: list[dict] = []

    def fake_fire(result, web):
        calls.append(result)

    with patch.object(central_listener, "_fire_violation", side_effect=fake_fire):
        yield calls


@pytest.fixture(autouse=True)
def clear_replay_flag():
    """Ensure REPLAY_ON_CLAIM_ENABLED is unset between tests."""
    prior = os.environ.pop("REPLAY_ON_CLAIM_ENABLED", None)
    yield
    if prior is not None:
        os.environ["REPLAY_ON_CLAIM_ENABLED"] = prior


def _run(event: dict) -> None:
    central_listener.run_enforcer(event, event["text"], web=None)


def test_replay_disabled_by_default_r3_fires(
    fake_event, llm_r3_violation, always_should_check, attribute_aiden, fire_capture
) -> None:
    """Without REPLAY_ON_CLAIM_ENABLED, replay is skipped and R3 fires."""
    # Use a message that won't be caught by the pre-existing post-LLM regex
    fake_event["text"] = "Task is done. Standing by."
    _run(fake_event)
    # Without "merged"/PR refs/etc, post-LLM evidence regex won't match → R3 fires
    assert len(fire_capture) == 1
    assert fire_capture[0]["rule_number"] == 3


def test_replay_enabled_and_verified_suppresses(
    fake_event, llm_r3_violation, always_should_check, attribute_aiden, fire_capture
) -> None:
    """REPLAY_ON_CLAIM_ENABLED=1 + verifier returns (True, ...) → R3 suppressed."""
    os.environ["REPLAY_ON_CLAIM_ENABLED"] = "1"
    fake_event["text"] = "Task is done. No completion patterns here either."
    with patch("src.replay.verify_completion_claim", return_value=(True, "evidence")):
        _run(fake_event)
    assert len(fire_capture) == 0


def test_replay_enabled_and_not_verified_fires(
    fake_event, llm_r3_violation, always_should_check, attribute_aiden, fire_capture
) -> None:
    """REPLAY_ON_CLAIM_ENABLED=1 + verifier returns (False, ...) → R3 fires."""
    os.environ["REPLAY_ON_CLAIM_ENABLED"] = "1"
    fake_event["text"] = "Task is done. Plain claim."
    with patch("src.replay.verify_completion_claim", return_value=(False, "no evidence")):
        _run(fake_event)
    assert len(fire_capture) == 1
    assert fire_capture[0]["rule_number"] == 3


def test_replay_exception_falls_through_to_llm_verdict(
    fake_event, llm_r3_violation, always_should_check, attribute_aiden, fire_capture
) -> None:
    """If verify_completion_claim raises, run_enforcer proceeds with LLM verdict."""
    os.environ["REPLAY_ON_CLAIM_ENABLED"] = "1"
    fake_event["text"] = "Task is done."

    def boom(*args, **kwargs):
        raise RuntimeError("supabase down")

    with patch("src.replay.verify_completion_claim", side_effect=boom):
        _run(fake_event)
    # Best-effort: LLM verdict (R3 violation) proceeds → fire
    assert len(fire_capture) == 1
    assert fire_capture[0]["rule_number"] == 3
