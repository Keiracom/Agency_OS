"""Tests for src/coo_bot/group_handler.py — group message buffer."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

import src.coo_bot.group_handler as gh


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _make_update(
    text: str,
    sender_id: int = 12345,
    sender_name: str = "testuser",
    chat_id: int = -1003926592540,
    message_id: int = 1,
) -> MagicMock:
    update = MagicMock()
    update.message = MagicMock()
    update.message.text = text
    update.message.chat_id = chat_id
    update.message.message_id = message_id
    update.message.date = None
    update.message.from_user = MagicMock()
    update.message.from_user.id = sender_id
    update.message.from_user.username = sender_name
    update.message.from_user.full_name = sender_name
    return update


def _make_context(bot_id: int = 999) -> MagicMock:
    ctx = MagicMock()
    ctx.bot = MagicMock()
    ctx.bot.id = bot_id
    return ctx


def setup_function():
    """Clear buffer before each test."""
    gh._buffer.clear()


def test_skip_own_messages():
    """Bot's own messages must not enter the buffer."""
    bot_id = 999
    update = _make_update("hello", sender_id=bot_id)
    ctx = _make_context(bot_id=bot_id)
    _run(gh.handle_group_message(update, ctx))
    assert len(gh._buffer) == 0


def test_skip_enforcer():
    """Messages starting with [ENFORCER] must be silently dropped."""
    update = _make_update("[ENFORCER] some alert", sender_id=111)
    ctx = _make_context(bot_id=999)
    _run(gh.handle_group_message(update, ctx))
    assert len(gh._buffer) == 0


def test_buffer_stores_message():
    """Normal group message is stored with correct keys and values."""
    update = _make_update("hi group", sender_id=111, sender_name="alice", message_id=42)
    ctx = _make_context(bot_id=999)
    _run(gh.handle_group_message(update, ctx))
    assert len(gh._buffer) == 1
    entry = gh._buffer[0]
    assert entry["sender"] == "alice"
    assert entry["text"] == "hi group"
    assert entry["message_id"] == 42
    assert "timestamp" in entry


def test_buffer_limit_50():
    """Buffer must never exceed 50 entries."""
    ctx = _make_context(bot_id=999)
    for i in range(60):
        update = _make_update(f"msg {i}", sender_id=111, message_id=i)
        _run(gh.handle_group_message(update, ctx))
    assert len(gh._buffer) == 50


def test_get_recent_messages_returns_latest():
    """get_recent_messages(limit=N) returns the N most recent messages."""
    ctx = _make_context(bot_id=999)
    for i in range(10):
        update = _make_update(f"msg {i}", sender_id=111, message_id=i)
        _run(gh.handle_group_message(update, ctx))

    recent = gh.get_recent_messages(limit=3)
    assert len(recent) == 3
    # Should be the last three (msg 7, 8, 9)
    assert recent[-1]["text"] == "msg 9"
    assert recent[0]["text"] == "msg 7"
