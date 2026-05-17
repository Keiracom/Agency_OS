"""Tests for auto-KEI creation in central_listener.py (KEI-18).

Per Dave-direct mandate 2026-05-16: messages in #ceo channel starting with
[CEO] prefix trigger automatic task insertion into public.tasks and a
confirmation post back to #ceo. Fanout relay must still fire regardless of
auto-KEI outcome.

All tests use mocks — no live Slack or Supabase calls.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

# Stub slack_sdk and psycopg before module import (same pattern as PR #711)
for mod_name in (
    "slack_sdk",
    "slack_sdk.socket_mode",
    "slack_sdk.socket_mode.request",
    "slack_sdk.socket_mode.response",
    "slack_sdk.web",
):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = types.ModuleType(mod_name)
sys.modules["slack_sdk.socket_mode"].SocketModeClient = type("SocketModeClient", (), {})
sys.modules["slack_sdk.socket_mode.request"].SocketModeRequest = type("SocketModeRequest", (), {})
sys.modules["slack_sdk.socket_mode.response"].SocketModeResponse = type(
    "SocketModeResponse", (), {}
)
sys.modules["slack_sdk.web"].WebClient = type("WebClient", (), {})

# Stub psycopg at the top level before importing central_listener
psycopg_stub = types.ModuleType("psycopg")
psycopg_errors_stub = types.ModuleType("psycopg.errors")


class _UniqueViolation(Exception):
    pass


psycopg_errors_stub.UniqueViolation = _UniqueViolation
psycopg_stub.errors = psycopg_errors_stub
psycopg_stub.connect = MagicMock()
sys.modules["psycopg"] = psycopg_stub
sys.modules["psycopg.errors"] = psycopg_errors_stub

from src.slack_bot.central_listener import (  # noqa: E402
    CALLSIGN_TO_INBOX,
    CEO_CHANNEL,
    _extract_ceo_title,
    _insert_kei_task,
    _maybe_auto_create_kei,
    process_event,
)

CEO_EVENT_TEXT = "[CEO] File the migration KEI now."
NON_CEO_TEXT = "Status check on Wave 4"
EMPTY_CEO_TEXT = "[CEO]\n"


# ──────────────────────────────────────────────────────────────────────────────
# Helper: build a #ceo Slack event dict
# ──────────────────────────────────────────────────────────────────────────────


def _ceo_event(text: str) -> dict:
    return {"type": "message", "channel": CEO_CHANNEL, "text": text, "ts": "1.0"}


def _execution_event(text: str) -> dict:
    return {"type": "message", "channel": "C0B3QB0K1GQ", "text": text, "ts": "1.0"}


# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: [CEO] prefix triggers INSERT with correct fields
# ──────────────────────────────────────────────────────────────────────────────


def test_ceo_prefix_inserts_task() -> None:
    """Mocked psycopg cursor receives INSERT with computed next id + extracted title + status='available'."""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = (42,)

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    with (
        patch("src.slack_bot.central_listener.DATABASE_URL", "postgresql://fake/db"),
        patch("src.slack_bot.central_listener.psycopg.connect", return_value=mock_conn),
    ):
        kei_id = _insert_kei_task("File the migration KEI now.")

    assert kei_id == "KEI-42"
    # Verify INSERT was called with the right arguments
    insert_call = mock_cursor.execute.call_args_list[1]
    args = insert_call[0][1]  # positional args tuple passed to execute
    assert args[0] == "KEI-42"
    assert args[1] == "File the migration KEI now."
    assert args[2] == "available"
    assert args[3] == []
    assert args[4] is None


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: No [CEO] prefix → INSERT not called
# ──────────────────────────────────────────────────────────────────────────────


def test_no_prefix_skips_insert() -> None:
    """Non-[CEO] message in #ceo channel does not trigger any INSERT."""
    mock_web = MagicMock()
    event = _ceo_event(NON_CEO_TEXT)

    with patch("src.slack_bot.central_listener.psycopg.connect") as mock_connect:
        _maybe_auto_create_kei(event, mock_web)
        mock_connect.assert_not_called()

    mock_web.chat_postMessage.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: Empty body after [CEO] strip → INSERT skipped
# ──────────────────────────────────────────────────────────────────────────────


def test_empty_body_skips_insert() -> None:
    """A bare [CEO] post (nothing after the prefix) skips auto-create."""
    mock_web = MagicMock()
    event = _ceo_event(EMPTY_CEO_TEXT)

    with patch("src.slack_bot.central_listener.psycopg.connect") as mock_connect:
        _maybe_auto_create_kei(event, mock_web)
        mock_connect.assert_not_called()

    mock_web.chat_postMessage.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: Successful insert → confirmation posted to #ceo
# ──────────────────────────────────────────────────────────────────────────────


def test_confirmation_posted_on_success() -> None:
    """After a successful insert, chat_postMessage is called with [System] KEI-N created — …"""
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = (7,)

    mock_conn = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    mock_web = MagicMock()
    event = _ceo_event(CEO_EVENT_TEXT)

    with (
        patch("src.slack_bot.central_listener.DATABASE_URL", "postgresql://fake/db"),
        patch("src.slack_bot.central_listener.psycopg.connect", return_value=mock_conn),
    ):
        _maybe_auto_create_kei(event, mock_web)

    mock_web.chat_postMessage.assert_called_once_with(
        channel=CEO_CHANNEL,
        text="[System] KEI-7 created — File the migration KEI now.",
    )


# ──────────────────────────────────────────────────────────────────────────────
# TEST 5: Auto-create failure does NOT block fanout relay
# ──────────────────────────────────────────────────────────────────────────────


def test_fanout_still_fires(tmp_path) -> None:
    """write_inbox (fanout) fires even when _maybe_auto_create_kei raises."""
    inbox_elliot = tmp_path / "elliot_inbox"
    inbox_elliot.mkdir()

    event = _ceo_event(CEO_EVENT_TEXT)

    with (
        patch(
            "src.slack_bot.central_listener._maybe_auto_create_kei",
            side_effect=RuntimeError("db down"),
        ),
        patch.dict(CALLSIGN_TO_INBOX, {"elliot": [inbox_elliot]}),
    ):
        process_event(event)

    # Elliot's inbox should have received the fanout despite the auto-KEI failure
    files = list(inbox_elliot.iterdir())
    assert len(files) == 1


# ──────────────────────────────────────────────────────────────────────────────
# TITLE EXTRACTION UNIT TESTS
# ──────────────────────────────────────────────────────────────────────────────


def test_extract_title_basic() -> None:
    assert _extract_ceo_title("[CEO] File the migration KEI now.") == "File the migration KEI now."


def test_extract_title_multiline_takes_first() -> None:
    text = "[CEO]\nFirst meaningful line\nSecond line"
    assert _extract_ceo_title(text) == "First meaningful line"


def test_extract_title_empty_returns_none() -> None:
    assert _extract_ceo_title("[CEO]\n") is None
    assert _extract_ceo_title("[CEO]") is None
    assert _extract_ceo_title("[CEO]   ") is None


def test_extract_title_truncates_at_200() -> None:
    long_title = "A" * 250
    text = f"[CEO] {long_title}"
    result = _extract_ceo_title(text)
    assert result is not None
    assert len(result) == 200


def test_extract_title_case_insensitive_prefix() -> None:
    assert _extract_ceo_title("[ceo] lower case prefix") == "lower case prefix"
