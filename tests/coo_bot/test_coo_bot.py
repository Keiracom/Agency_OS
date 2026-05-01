"""Tests for src/coo_bot — COO bot (Max)."""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(event_type: str = "GOV_DENY", message: str = "test") -> dict[str, Any]:
    return {
        "event_type": event_type,
        "message": message,
        "callsign": "elliot",
        "created_at": "2026-05-01T00:00:00+00:00",
        "metadata": {},
    }


def _run(coro: Any) -> Any:
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# test_generate_summary_formats_correctly
# ---------------------------------------------------------------------------


def test_generate_summary_formats_correctly() -> None:
    """OpenAI response content is returned as-is."""
    events = [_make_event("COST_CAP", "daily cap hit"), _make_event("GOV_DENY", "classifier blocked")]

    fake_choice = MagicMock()
    fake_choice.message.content = "- Cost cap hit\n- Classifier blocked"
    fake_resp = MagicMock()
    fake_resp.choices = [fake_choice]

    with patch.dict(
        "os.environ",
        {"COO_BOT_TOKEN": "fake-token", "OPENAI_API_KEY": "fake-key"},
    ):
        with patch("src.coo_bot.bot.openai.AsyncOpenAI") as mock_openai_cls:
            mock_client = MagicMock()
            mock_client.chat = MagicMock()
            mock_client.chat.completions = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=fake_resp)
            mock_openai_cls.return_value = mock_client

            from src.coo_bot.bot import generate_summary

            result = _run(generate_summary(events, window_hours=1))

    assert "Cost cap hit" in result
    assert "Classifier blocked" in result


# ---------------------------------------------------------------------------
# test_fetch_recent_events_empty
# ---------------------------------------------------------------------------


def test_fetch_recent_events_empty() -> None:
    """Returns empty list when asyncpg returns no rows."""
    with patch("src.coo_bot.bot.asyncpg.connect", new_callable=AsyncMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.close = AsyncMock()
        mock_connect.return_value = mock_conn

        from src.coo_bot.bot import fetch_recent_events

        result = _run(fetch_recent_events("postgresql://fake/db", hours=1))

    assert result == []


# ---------------------------------------------------------------------------
# test_send_dm_success
# ---------------------------------------------------------------------------


def test_send_dm_success() -> None:
    """Returns True when Telegram Bot.send_message succeeds."""
    with patch("src.coo_bot.bot.Bot") as mock_bot_cls:
        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(return_value=MagicMock())
        mock_bot_cls.return_value = mock_bot

        from src.coo_bot.bot import send_dm

        result = _run(send_dm("fake-token", 7267788033, "hello Dave"))

    assert result is True
    mock_bot.send_message.assert_awaited_once_with(chat_id=7267788033, text="hello Dave")


# ---------------------------------------------------------------------------
# test_digest_loop_skips_when_no_events
# ---------------------------------------------------------------------------


def test_digest_loop_skips_when_no_events() -> None:
    """digest_loop sends no DM when fetch_recent_events returns []."""
    with patch.dict(
        "os.environ",
        {
            "COO_BOT_TOKEN": "fake-token",
            "OPENAI_API_KEY": "fake-key",
            "COO_DIGEST_INTERVAL_MINUTES": "60",
        },
    ):
        with patch("src.coo_bot.bot.fetch_recent_events", new_callable=AsyncMock, return_value=[]) as mock_fetch, \
             patch("src.coo_bot.bot.send_dm", new_callable=AsyncMock) as mock_send, \
             patch("src.coo_bot.bot.asyncio.sleep", new_callable=AsyncMock, side_effect=asyncio.CancelledError):

            from src.coo_bot.bot import digest_loop
            from src.coo_bot.config import COOConfig

            cfg = COOConfig()
            with pytest.raises(asyncio.CancelledError):
                _run(digest_loop(cfg))

    mock_fetch.assert_called_once()
    mock_send.assert_not_called()
