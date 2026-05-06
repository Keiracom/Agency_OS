"""Tests for _classify_intent in src/coo_bot/dm_handler.py."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.coo_bot.dm_handler import _classify_intent, handle_dm


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_update(text: str, chat_id: int = 7267788033) -> MagicMock:
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.chat_id = chat_id
    update.message.message_id = 42
    update.message.reply_text = AsyncMock()
    return update


# ---------------------------------------------------------------------------
# Unit tests for _classify_intent
# ---------------------------------------------------------------------------


def test_relay_intent_returned():
    """When opus returns relay JSON, _classify_intent returns relay intent."""
    relay_json = json.dumps({"intent": "relay", "relay_text": "approve that PR"})
    with patch("src.coo_bot.dm_handler.opus_call", new_callable=AsyncMock, return_value=relay_json):
        result = _run(_classify_intent("approve that PR", "recent context"))
    assert result["intent"] == "relay"
    assert result["relay_text"] == "approve that PR"


def test_private_intent_returned():
    """When opus returns private JSON, _classify_intent returns private intent."""
    private_json = json.dumps({"intent": "private", "relay_text": None})
    with patch(
        "src.coo_bot.dm_handler.opus_call", new_callable=AsyncMock, return_value=private_json
    ):
        result = _run(_classify_intent("what do you think?", ""))
    assert result["intent"] == "private"
    assert result["relay_text"] is None


def test_parse_failure_defaults_to_private():
    """When opus returns garbage, _classify_intent defaults to private."""
    with patch(
        "src.coo_bot.dm_handler.opus_call", new_callable=AsyncMock, return_value="not valid json"
    ):
        result = _run(_classify_intent("some message", ""))
    assert result["intent"] == "private"
    assert result["relay_text"] is None


# ---------------------------------------------------------------------------
# Integration: handle_dm routes correctly based on intent
# ---------------------------------------------------------------------------


def test_handle_dm_relay_calls_post_to_group():
    """handle_dm with relay intent calls post_to_group and confirms in DM."""
    relay_result = {"intent": "relay", "relay_text": "merge it"}
    mock_post = AsyncMock(return_value=True)
    with (
        patch(
            "src.coo_bot.dm_handler._classify_intent",
            new_callable=AsyncMock,
            return_value=relay_result,
        ),
        patch("src.coo_bot.dm_handler._load_context", new_callable=AsyncMock, return_value="ctx"),
    ):
        update = _make_update("tell them to merge it")
        with patch.dict(
            "sys.modules", {"src.coo_bot.group_writer": MagicMock(post_to_group=mock_post)}
        ):
            _run(handle_dm(update, MagicMock()))
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Posted to group" in reply_text
    assert "merge it" in reply_text


def test_handle_dm_private_calls_opus_response():
    """handle_dm with private intent calls opus for response, not post_to_group."""
    private_result = {"intent": "private", "relay_text": None}
    mock_post = AsyncMock(return_value=True)
    with (
        patch(
            "src.coo_bot.dm_handler._classify_intent",
            new_callable=AsyncMock,
            return_value=private_result,
        ),
        patch(
            "src.coo_bot.dm_handler.opus_call", new_callable=AsyncMock, return_value="my opinion"
        ) as mock_opus,
        patch("src.coo_bot.dm_handler._load_context", new_callable=AsyncMock, return_value="ctx"),
    ):
        update = _make_update("what do you think about the pipeline?")
        _run(handle_dm(update, MagicMock()))
    mock_opus.assert_called_once()
    assert "my opinion" in update.message.reply_text.call_args[0][0]
