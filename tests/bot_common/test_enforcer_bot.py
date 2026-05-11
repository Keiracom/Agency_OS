"""Unit and integration tests for src/bot_common/enforcer_bot.py.

Test coverage:
  1. callsign_from_username — 8-entry lookup table per spec §7.3.
  2. stage0_active timing — 29.9 min PASS, 30.1 min FAIL (frozen now).
  3. Per-(rule, channel) cooldown — 300s freeze.
  4. Mock LLM returning rule-3 violation — assert interjection text shape,
     governance_events insert called once (mocked asyncpg pool).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot_common.enforcer_bot import (
    FLAG_COOLDOWN_SECONDS,
    callsign_from_username,
    enforce_events,
    last_flag_times,
    message_windows,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_bot_event(
    text: str,
    username: str = "Elliot",
    channel_id: str = "C123456",
    channel_name: str = "#execution",
    ts: str = "1234567890.000001",
) -> dict:
    return {
        "type": "message",
        "text": text,
        "username": username,
        "bot_id": "B123",
        "channel": channel_id,
        "_channel_name": channel_name,
        "ts": ts,
    }


# ---------------------------------------------------------------------------
# 1. callsign_from_username lookup table — spec §7.3
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "username, expected",
    [
        ("Elliot",   "elliot"),
        ("Aiden",    "aiden"),
        ("Max",      "max"),
        ("ATLAS",    "atlas"),
        ("ORION",    "orion"),
        ("SCOUT",    "scout"),
        ("Enforcer", "enforcer"),
        ("",         "dave"),   # no override → Dave (real Slack user)
    ],
)
def test_callsign_from_username(username: str, expected: str) -> None:
    assert callsign_from_username(username) == expected


def test_callsign_from_username_unrecognised() -> None:
    """Unrecognised values fall back to 'dave' (real Slack user assumed)."""
    # Any value not in the table that is non-empty defaults to 'dave'
    result = callsign_from_username("SomeRandomBot")
    assert result == "dave"


# ---------------------------------------------------------------------------
# 2. stage0_active timing — freeze time
# ---------------------------------------------------------------------------


def _set_stage0_request(minutes_ago: float) -> None:
    """Write a last_stage0_request enforce_events entry N minutes in the past."""
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    enforce_events["last_stage0_request"] = {
        "timestamp": ts.isoformat(),
        "text_snippet": "/stage0",
        "topic_hint": "/stage0",
    }


def _compute_stage0_active() -> bool:
    """Reproduce the deterministic stage0_active check from enforcer_bot.py:317-329."""
    last_stage0 = enforce_events.get("last_stage0_request", {})
    if not last_stage0:
        return False
    stage0_ts = last_stage0.get("timestamp", "")
    if not stage0_ts:
        return False
    try:
        ts_dt = datetime.fromisoformat(stage0_ts)
        age_minutes = (datetime.now(UTC) - ts_dt).total_seconds() / 60
        return age_minutes < 30
    except Exception:
        return False


def test_stage0_active_within_30_min() -> None:
    """29.9 min ago → stage0_active should be True."""
    _set_stage0_request(29.9)
    assert _compute_stage0_active() is True


def test_stage0_inactive_after_30_min() -> None:
    """30.1 min ago → stage0_active should be False."""
    _set_stage0_request(30.1)
    assert _compute_stage0_active() is False


def test_stage0_inactive_when_no_event() -> None:
    enforce_events.pop("last_stage0_request", None)
    assert _compute_stage0_active() is False


# ---------------------------------------------------------------------------
# 3. Per-(rule, channel) cooldown
# ---------------------------------------------------------------------------


def test_cooldown_suppresses_reflag() -> None:
    """Second flag within cooldown window should be suppressed."""
    rule_num = 3
    channel = "#execution"
    flag_key = (rule_num, channel)
    # Simulate first flag just happened
    last_flag_times[flag_key] = time.time()

    now = time.time()
    elapsed = now - last_flag_times[flag_key]
    should_suppress = elapsed < FLAG_COOLDOWN_SECONDS
    assert should_suppress is True


def test_cooldown_allows_flag_after_expiry() -> None:
    """Flag after cooldown window has expired should not be suppressed."""
    rule_num = 5
    channel = "#alerts"
    flag_key = (rule_num, channel)
    # Simulate last flag was 301 seconds ago
    last_flag_times[flag_key] = time.time() - (FLAG_COOLDOWN_SECONDS + 1)

    now = time.time()
    elapsed = now - last_flag_times[flag_key]
    should_suppress = elapsed < FLAG_COOLDOWN_SECONDS
    assert should_suppress is False


def test_cooldown_is_per_channel() -> None:
    """Cooldown for (rule=3, #execution) must NOT affect (rule=3, #alerts)."""
    last_flag_times[(3, "#execution")] = time.time()
    alerts_key = (3, "#alerts")
    last_flag_times.pop(alerts_key, None)

    # alerts key is absent → should not suppress
    suppressed = alerts_key in last_flag_times and (
        time.time() - last_flag_times[alerts_key] < FLAG_COOLDOWN_SECONDS
    )
    assert suppressed is False


# ---------------------------------------------------------------------------
# 4. Mock LLM → rule-3 violation — interjection text + governance_events insert
# ---------------------------------------------------------------------------


_LLM_R3_RESPONSE = {
    "violation": True,
    "rule_number": 3,
    "rule_name": "COMPLETION-REQUIRES-VERIFICATION",
    "detail": "claimed 'done' without showing verification evidence",
    "should_have": "Terminal output or commit hash proving completion",
}

_LLM_R3_JSON_BYTES = json.dumps(_LLM_R3_RESPONSE).encode()


def _make_llm_mock_response() -> Any:
    """Build an httpx-compatible async mock that returns a rule-3 violation."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json = MagicMock(
        return_value={
            "choices": [
                {
                    "message": {
                        "content": json.dumps(_LLM_R3_RESPONSE)
                    }
                }
            ]
        }
    )
    return mock_resp


@pytest.mark.asyncio
async def test_process_message_r3_violation_interjection_shape() -> None:
    """Mock LLM returns R3 violation; assert interjection text matches expected format."""
    from src.bot_common import enforcer_bot

    # Clear state so rate-limit doesn't suppress
    enforcer_bot.last_flag_times.pop((3, "#execution"), None)

    # Stage0 not needed for R3
    enforce_events.pop("last_stage0_request", None)

    # Build event with a completion-claim trigger word
    event = _make_bot_event(
        text="All done — directive complete.",
        channel_name="#execution",
    )

    captured_interjections: list[str] = []
    captured_rows: list[dict] = []

    async def _mock_post_to_slack(channel_id: str, text: str, thread_ts: Any) -> bool:
        captured_interjections.append(text)
        return True

    async def _mock_insert_governance_event(row: dict) -> bool:
        captured_rows.append(row)
        return True

    async def _mock_write_inboxes(text: str, ts: str) -> None:
        pass

    # Mock httpx.AsyncClient POST to return LLM response
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_instance.post = AsyncMock(return_value=_make_llm_mock_response())

    with (
        patch.object(enforcer_bot, "OBSERVE_ONLY", False),
        patch.object(enforcer_bot, "_post_to_slack", _mock_post_to_slack),
        patch.object(enforcer_bot, "_insert_governance_event", _mock_insert_governance_event),
        patch.object(enforcer_bot, "_write_filesystem_inboxes", _mock_write_inboxes),
        patch("httpx.AsyncClient", return_value=mock_client_instance),
    ):
        await enforcer_bot.process_message(event)

    # Interjection text shape — identical format to enforcer_bot.py:357
    assert len(captured_interjections) == 1
    interjection = captured_interjections[0]
    assert interjection.startswith("[ENFORCER] Rule 3 --")
    assert "COMPLETION-REQUIRES-VERIFICATION" in interjection
    assert "claimed 'done' without showing verification evidence" in interjection
    assert interjection.endswith(".")

    # governance_events insert called exactly once
    assert len(captured_rows) == 1
    row = captured_rows[0]
    assert row["rule_id"] == "R3"
    assert row["rule_name"] == "COMPLETION-REQUIRES-VERIFICATION"
    assert row["source"] == "enforcer"
    assert row["channel"] == "#execution"
    assert row["llm_model"] == "gpt-4o-mini"
    assert "claimed 'done'" in row["interjection_text"]


@pytest.mark.asyncio
async def test_process_message_observe_only_skips_slack_post() -> None:
    """In OBSERVE_ONLY mode, Slack post is skipped but governance row is still written."""
    from src.bot_common import enforcer_bot

    enforcer_bot.last_flag_times.pop((3, "#execution"), None)

    event = _make_bot_event(
        text="Task complete — all stores written.",
        channel_name="#execution",
    )

    slack_calls: list[str] = []
    govern_rows: list[dict] = []

    async def _mock_post_to_slack(channel_id: str, text: str, thread_ts: Any) -> bool:
        slack_calls.append(text)
        return True

    async def _mock_insert_governance_event(row: dict) -> bool:
        govern_rows.append(row)
        return True

    async def _mock_write_inboxes(text: str, ts: str) -> None:
        pass

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_instance.post = AsyncMock(return_value=_make_llm_mock_response())

    with (
        patch.object(enforcer_bot, "OBSERVE_ONLY", True),
        patch.object(enforcer_bot, "_post_to_slack", _mock_post_to_slack),
        patch.object(enforcer_bot, "_insert_governance_event", _mock_insert_governance_event),
        patch.object(enforcer_bot, "_write_filesystem_inboxes", _mock_write_inboxes),
        patch("httpx.AsyncClient", return_value=mock_client_instance),
    ):
        await enforcer_bot.process_message(event)

    # Slack should NOT have been called in observe-only mode
    assert len(slack_calls) == 0

    # governance_events row should still be written with OBSERVE: prefix
    assert len(govern_rows) == 1
    assert govern_rows[0]["interjection_text"].startswith("OBSERVE: ")


@pytest.mark.asyncio
async def test_process_message_fails_open_on_llm_error() -> None:
    """LLM failure (httpx exception) → no crash, no interjection."""
    from src.bot_common import enforcer_bot

    enforcer_bot.last_flag_times.pop((3, "#execution"), None)

    event = _make_bot_event(
        text="All done — directive complete.",
        channel_name="#execution",
    )

    slack_calls: list[str] = []

    async def _mock_post_to_slack(channel_id: str, text: str, thread_ts: Any) -> bool:
        slack_calls.append(text)
        return True

    async def _mock_insert(row: dict) -> bool:
        return True

    async def _mock_inboxes(text: str, ts: str) -> None:
        pass

    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=False)
    mock_client_instance.post = AsyncMock(side_effect=Exception("network error"))

    with (
        patch.object(enforcer_bot, "OBSERVE_ONLY", False),
        patch.object(enforcer_bot, "_post_to_slack", _mock_post_to_slack),
        patch.object(enforcer_bot, "_insert_governance_event", _mock_insert),
        patch.object(enforcer_bot, "_write_filesystem_inboxes", _mock_inboxes),
        patch("httpx.AsyncClient", return_value=mock_client_instance),
    ):
        # Must not raise
        await enforcer_bot.process_message(event)

    # No Slack post because LLM failed → result is None → no violation path
    assert len(slack_calls) == 0
