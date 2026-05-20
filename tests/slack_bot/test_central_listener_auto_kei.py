"""Tests for auto-KEI creation in central_listener.py (KEI-18, KEI-100 pivot).

Per Dave-direct mandate 2026-05-16: messages in #ceo channel starting with
[CEO] prefix trigger automatic KEI creation and a confirmation post back to
#ceo. Fanout relay must still fire regardless of auto-KEI outcome.

KEI-100 pivot: creation goes via Linear GraphQL (Linear is source of truth);
the Linear webhook handles the Supabase upsert asynchronously.

KEI-144 hotpatch: behavior is env-gated behind AUTO_KEI_FROM_CEO=1.

All tests use mocks — no live Slack or Linear calls.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

# Stub slack_sdk before module import (same pattern as PR #711).
# psycopg is NOT stubbed here — central_listener.py post-KEI-100 no longer
# imports psycopg directly; stubbing it leaked into sys.modules and broke
# unrelated tests (ceo_memory_writer, tool_call_logger, e2e schema smoke).
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

from src.slack_bot.central_listener import (  # noqa: E402
    CALLSIGN_TO_INBOX,
    CEO_CHANNEL,
    _create_kei_via_linear,
    _extract_ceo_title,
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
# TEST 1: _create_kei_via_linear posts Linear GraphQL and returns identifier
# ──────────────────────────────────────────────────────────────────────────────


def test_create_kei_via_linear_returns_identifier() -> None:
    """Linear issueCreate success → function returns the assigned identifier."""
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(return_value=None)
    mock_response.json.return_value = {
        "data": {
            "issueCreate": {
                "success": True,
                "issue": {"id": "uuid-42", "identifier": "KEI-42", "url": "https://linear.app/x"},
            }
        }
    }

    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.send.return_value = mock_response

    with (
        patch.dict("os.environ", {"LINEAR_API_KEY": "lk_test"}, clear=False),
        patch("src.slack_bot.central_listener.httpx.Client", return_value=mock_client),
    ):
        kei_id = _create_kei_via_linear("File the migration KEI now.")

    assert kei_id == "KEI-42"
    # Verify the GraphQL request body contains the title
    sent_request = mock_client.send.call_args[0][0]
    body = sent_request.content.decode()
    assert "File the migration KEI now." in body
    assert "issueCreate" in body


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: No [CEO] prefix → Linear create not called
# ──────────────────────────────────────────────────────────────────────────────


def test_no_prefix_skips_linear_create() -> None:
    """Non-[CEO] message in #ceo channel does not trigger Linear issue create."""
    mock_web = MagicMock()
    event = _ceo_event(NON_CEO_TEXT)

    with (
        patch.dict("os.environ", {"AUTO_KEI_FROM_CEO": "1"}, clear=False),
        patch("src.slack_bot.central_listener._create_kei_via_linear") as mock_create,
    ):
        _maybe_auto_create_kei(event, mock_web)
        mock_create.assert_not_called()

    mock_web.chat_postMessage.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: Empty body after [CEO] strip → Linear create skipped
# ──────────────────────────────────────────────────────────────────────────────


def test_empty_body_skips_linear_create() -> None:
    """A bare [CEO] post (nothing after the prefix) skips auto-create."""
    mock_web = MagicMock()
    event = _ceo_event(EMPTY_CEO_TEXT)

    with (
        patch.dict("os.environ", {"AUTO_KEI_FROM_CEO": "1"}, clear=False),
        patch("src.slack_bot.central_listener._create_kei_via_linear") as mock_create,
    ):
        _maybe_auto_create_kei(event, mock_web)
        mock_create.assert_not_called()

    mock_web.chat_postMessage.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: Successful Linear create → confirmation posted to #ceo
# ──────────────────────────────────────────────────────────────────────────────


def test_confirmation_posted_on_success() -> None:
    """After a successful Linear create, chat_postMessage is called with [System] KEI-N created — …"""
    mock_web = MagicMock()
    event = _ceo_event(CEO_EVENT_TEXT)

    with (
        patch.dict("os.environ", {"AUTO_KEI_FROM_CEO": "1"}, clear=False),
        patch(
            "src.slack_bot.central_listener._create_kei_via_linear",
            return_value="KEI-7",
        ),
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
