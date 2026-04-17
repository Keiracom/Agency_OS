"""
Tests for src/telegram_bot/save_handler.py
Covers: parse_save_command, write_agent_memory (mocked), cmd_save flow
No real API calls — httpx patched throughout.
"""

import sys
import os
import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# sys.path injection — telegram_bot src + system site-packages (LAW V pattern)
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "telegram_bot"))
# python-telegram-bot lives in system python, not project venv
_system_site = "/home/elliotbot/.local/lib/python3.12/site-packages"
if _system_site not in sys.path:
    sys.path.insert(0, _system_site)

from save_handler import (  # noqa: E402
    parse_save_command,
    write_agent_memory,
    cmd_save,
    VALID_TYPES,
)


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

    def test_unknown_first_word_falls_back_to_general(self):
        source_type, content = parse_save_command(["remember", "this", "thing"])
        assert source_type == "general"
        assert content == "remember this thing"

    def test_bare_save_returns_general_empty(self):
        source_type, content = parse_save_command([])
        assert source_type == "general"
        assert content == ""

    def test_type_only_no_content(self):
        source_type, content = parse_save_command(["pattern"])
        assert source_type == "pattern"
        assert content == ""

    def test_type_case_insensitive(self):
        source_type, content = parse_save_command(["PATTERN", "text"])
        assert source_type == "pattern"
        assert content == "text"

    def test_general_bare_text(self):
        source_type, content = parse_save_command(["some", "raw", "note"])
        assert source_type == "general"
        assert content == "some raw note"


# ---------------------------------------------------------------------------
# write_agent_memory — Supabase POST mocked
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_agent_memory_success():
    """write_agent_memory POSTs correct payload and returns row."""
    fake_row = {
        "id": "abc-123",
        "callsign": "elliot",
        "source_type": "pattern",
        "content": "use semaphore",
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = [fake_row]

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await write_agent_memory(
            source_type="pattern",
            content="use semaphore",
            callsign="elliot",
        )

    assert result["id"] == "abc-123"
    assert result["source_type"] == "pattern"
    mock_client.post.assert_awaited_once()
    call_kwargs = mock_client.post.call_args
    posted_payload = call_kwargs.kwargs["json"]
    assert posted_payload["source_type"] == "pattern"
    assert posted_payload["content"] == "use semaphore"
    assert posted_payload["callsign"] == "elliot"


@pytest.mark.asyncio
async def test_write_agent_memory_supabase_error_raises():
    """write_agent_memory propagates HTTP error."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500, text="internal error")
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await write_agent_memory(source_type="pattern", content="test")


# ---------------------------------------------------------------------------
# cmd_save — Telegram handler (fully mocked update/context)
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
async def test_cmd_save_pattern_success():
    """cmd_save writes pattern memory and confirms."""
    update, context = _make_update(["pattern", "use", "gather"])

    fake_row = {"id": "row-1", "source_type": "pattern", "content": "use gather"}
    with patch("save_handler.write_agent_memory", new=AsyncMock(return_value=fake_row)):
        await cmd_save(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "pattern" in reply_text
    assert "use gather" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_general_fallback():
    """cmd_save saves as general when first word is not a valid type."""
    update, context = _make_update(["remember", "this"])

    fake_row = {"id": "row-2", "source_type": "general", "content": "remember this"}
    with patch("save_handler.write_agent_memory", new=AsyncMock(return_value=fake_row)):
        await cmd_save(update, context)

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "general" in reply_text


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
async def test_cmd_save_supabase_error_replies_gracefully():
    """cmd_save catches HTTP errors and replies with failure message."""
    update, context = _make_update(["decision", "ship it"])

    err = httpx.HTTPStatusError(
        "500",
        request=MagicMock(),
        response=MagicMock(status_code=500, text="error"),
    )
    with patch("save_handler.write_agent_memory", new=AsyncMock(side_effect=err)):
        await cmd_save(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Failed" in reply_text or "500" in reply_text
