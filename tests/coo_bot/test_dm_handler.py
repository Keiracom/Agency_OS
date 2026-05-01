"""Tests for src/coo_bot/dm_handler.py — DM bidirectional handler."""
from __future__ import annotations

import asyncio
import pathlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.coo_bot.dm_handler import handle_dm, _write_stop_state


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_update(text: str, chat_id: int = 7267788033) -> MagicMock:
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.chat_id = chat_id
    update.message.reply_text = AsyncMock()
    return update


def test_non_dave_chat_id_rejected():
    """Messages from non-Dave chat IDs are silently ignored."""
    update = _make_update("hello", chat_id=99999)
    _run(handle_dm(update, MagicMock()))
    update.message.reply_text.assert_not_called()


def test_stop_max_writes_state(tmp_path):
    """STOP MAX writes the stop state file."""
    with patch("src.coo_bot.dm_handler._write_stop_state") as mock_write:
        update = _make_update("STOP MAX")
        _run(handle_dm(update, MagicMock()))
        mock_write.assert_called_once_with(True)
        update.message.reply_text.assert_called_once()
        assert "STOP MAX acknowledged" in update.message.reply_text.call_args[0][0]


def test_resume_max_clears_state():
    """RESUME MAX clears the stop state."""
    with patch("src.coo_bot.dm_handler._write_stop_state") as mock_write:
        update = _make_update("RESUME MAX")
        _run(handle_dm(update, MagicMock()))
        mock_write.assert_called_once_with(False)
        assert "Resumed" in update.message.reply_text.call_args[0][0]


def test_post_command_calls_group_writer():
    """'/post hello world' delegates to group_writer."""
    mock_post = AsyncMock(return_value=True)
    with patch.dict("sys.modules", {"src.coo_bot.group_writer": MagicMock(post_to_group=mock_post)}):
        update = _make_update("/post hello world")
        _run(handle_dm(update, MagicMock()))
        assert "Posted" in update.message.reply_text.call_args[0][0]


def test_regular_text_calls_opus():
    """Regular DM text calls opus_call and replies."""
    with patch("src.coo_bot.dm_handler.opus_call", new_callable=AsyncMock, return_value="Max response") as mock_opus, \
         patch("src.coo_bot.dm_handler._load_context", new_callable=AsyncMock, return_value="context"):
        update = _make_update("what's happening?")
        _run(handle_dm(update, MagicMock()))
        mock_opus.assert_called_once()
        assert "Max response" in update.message.reply_text.call_args[0][0]


def test_opus_failure_shows_fallback():
    """When opus_call returns '', show fallback message."""
    with patch("src.coo_bot.dm_handler.opus_call", new_callable=AsyncMock, return_value="") as mock_opus, \
         patch("src.coo_bot.dm_handler._load_context", new_callable=AsyncMock, return_value=""):
        update = _make_update("tell me something")
        _run(handle_dm(update, MagicMock()))
        assert "couldn't generate" in update.message.reply_text.call_args[0][0]


def test_write_stop_state_creates_file(tmp_path):
    """_write_stop_state(True) creates the state file."""
    state_file = tmp_path / "max-coo-stopped"
    with patch("pathlib.Path", return_value=state_file):
        _write_stop_state(True)
    assert state_file.read_text() == "STOPPED"


def test_write_stop_state_removes_file(tmp_path):
    """_write_stop_state(False) removes the state file."""
    state_file = tmp_path / "max-coo-stopped"
    state_file.write_text("STOPPED")
    with patch("pathlib.Path", return_value=state_file):
        _write_stop_state(False)
    assert not state_file.exists()
