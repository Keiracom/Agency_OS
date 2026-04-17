"""
Tests for src/telegram_bot/save_handler.py
Covers: parse_save_command, cmd_save (store() mocked)
No real API calls — src.memory.store patched throughout.
"""

import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# sys.path injection — resolve src root so save_handler imports work
# ---------------------------------------------------------------------------
_repo_root = os.path.join(os.path.dirname(__file__), "..")
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# python-telegram-bot lives in system python, not project venv
_system_site = "/home/elliotbot/.local/lib/python3.12/site-packages"
if _system_site not in sys.path:
    sys.path.insert(0, _system_site)

from src.telegram_bot.save_handler import (  # noqa: E402
    parse_save_command,
    cmd_save,
)
from src.memory.types import VALID_SOURCE_TYPES  # noqa: E402


# ---------------------------------------------------------------------------
# parse_save_command
# ---------------------------------------------------------------------------


class TestParseSaveCommand:
    def test_valid_type_pattern(self):
        source_type, content = parse_save_command(["pattern", "use", "asyncio.gather"])
        assert source_type == "pattern"
        assert content == "use asyncio.gather"

    def test_valid_type_decision(self):
        source_type, content = parse_save_command(["decision", "always", "use", "REST"])
        assert source_type == "decision"
        assert content == "always use REST"

    def test_valid_type_skill(self):
        source_type, content = parse_save_command(["skill", "leadmagic does email lookup"])
        assert source_type == "skill"
        assert content == "leadmagic does email lookup"

    def test_valid_type_reasoning(self):
        source_type, content = parse_save_command(["reasoning", "because waterfall"])
        assert source_type == "reasoning"
        assert content == "because waterfall"

    def test_valid_type_test_result(self):
        source_type, content = parse_save_command(["test_result", "stage8 passed"])
        assert source_type == "test_result"
        assert content == "stage8 passed"

    def test_valid_type_dave_confirmed(self):
        source_type, content = parse_save_command(["dave_confirmed", "ship it"])
        assert source_type == "dave_confirmed"
        assert content == "ship it"

    def test_valid_type_daily_log(self):
        source_type, content = parse_save_command(["daily_log", "wrapped up stage 8"])
        assert source_type == "daily_log"
        assert content == "wrapped up stage 8"

    def test_unknown_first_word_falls_back_to_daily_log(self):
        source_type, content = parse_save_command(["remember", "this", "thing"])
        assert source_type == "daily_log"
        assert content == "remember this thing"

    def test_bare_save_returns_daily_log_empty(self):
        source_type, content = parse_save_command([])
        assert source_type == "daily_log"
        assert content == ""

    def test_type_only_no_content(self):
        source_type, content = parse_save_command(["pattern"])
        assert source_type == "pattern"
        assert content == ""

    def test_type_case_insensitive(self):
        source_type, content = parse_save_command(["PATTERN", "text"])
        assert source_type == "pattern"
        assert content == "text"

    def test_general_bare_text_becomes_daily_log(self):
        source_type, content = parse_save_command(["some", "raw", "note"])
        assert source_type == "daily_log"
        assert content == "some raw note"

    def test_valid_source_types_used_for_validation(self):
        """parse_save_command uses VALID_SOURCE_TYPES — all members are accepted."""
        for vtype in VALID_SOURCE_TYPES:
            st, _ = parse_save_command([vtype, "content"])
            assert st == vtype

    def test_general_is_not_a_valid_type(self):
        """'general' was removed — falls back to daily_log."""
        source_type, content = parse_save_command(["general", "some note"])
        assert source_type == "daily_log"
        assert content == "general some note"


# ---------------------------------------------------------------------------
# cmd_save — Telegram handler (fully mocked update/context + store mocked)
# ---------------------------------------------------------------------------


def _make_update(args: list[str]) -> tuple[MagicMock, MagicMock]:
    """Build mock Update and Context."""
    update = MagicMock()
    update.message = AsyncMock()
    update.message.reply_text = AsyncMock()
    context = MagicMock()
    context.args = args
    return update, context


@pytest.mark.asyncio
async def test_cmd_save_pattern_calls_store():
    """cmd_save calls store() with correct args for pattern type."""
    update, context = _make_update(["pattern", "use", "gather"])

    fake_row = {"id": "row-1", "source_type": "pattern", "content": "use gather"}
    with patch("src.telegram_bot.save_handler.store", new=AsyncMock(return_value=fake_row)) as mock_store:
        await cmd_save(update, context)

    assert mock_store.await_count == 1
    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "pattern"
    assert call_kwargs["content"] == "use gather"
    assert call_kwargs["tags"] == ["pattern"]

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "pattern" in reply_text
    assert "use gather" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_unknown_type_falls_back_to_daily_log():
    """cmd_save saves as daily_log when first word is not a valid type."""
    update, context = _make_update(["remember", "this"])

    fake_row = {"id": "row-2", "source_type": "daily_log", "content": "remember this"}
    with patch("src.telegram_bot.save_handler.store", new=AsyncMock(return_value=fake_row)) as mock_store:
        await cmd_save(update, context)

    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "daily_log"
    assert call_kwargs["content"] == "remember this"

    reply_text = update.message.reply_text.call_args[0][0]
    assert "daily_log" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_empty_shows_usage():
    """cmd_save with no args returns usage instructions."""
    update, context = _make_update([])

    await cmd_save(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_type_only_no_content_shows_usage():
    """/save pattern (no content) shows usage."""
    update, context = _make_update(["pattern"])

    await cmd_save(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "Usage" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_store_error_replies_gracefully():
    """cmd_save catches errors from store() and replies with failure message."""
    update, context = _make_update(["decision", "ship it"])

    with patch("src.telegram_bot.save_handler.store", new=AsyncMock(side_effect=Exception("Supabase 500"))):
        await cmd_save(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Failed" in reply_text or "Supabase" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_uses_valid_source_types_for_validation():
    """store() is called only when source_type is in VALID_SOURCE_TYPES."""
    for vtype in sorted(VALID_SOURCE_TYPES)[:3]:  # spot-check first 3
        update, context = _make_update([vtype, "content"])
        fake_row = {"id": "x", "source_type": vtype, "content": "content"}
        with patch("src.telegram_bot.save_handler.store", new=AsyncMock(return_value=fake_row)) as mock_store:
            await cmd_save(update, context)
        assert mock_store.call_args.kwargs["source_type"] == vtype
