"""
Tests for src/telegram_bot/save_handler.py
Covers: parse_save_command, extract_memory_fields, cmd_save (store() mocked)
No real API calls — src.memory.store.store and openai.OpenAI patched throughout.

store() is SYNC (returns uuid.UUID) — mocked with MagicMock, not AsyncMock.
cmd_save is async (Telegram handler) — sync store() called from async context.
"""

import sys
import os
import uuid
import json
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
    extract_memory_fields,
    cmd_save,
)
from src.memory.types import VALID_SOURCE_TYPES  # noqa: E402


# ---------------------------------------------------------------------------
# parse_save_command — now returns 3-tuple (source_type, content, needs_extraction)
# ---------------------------------------------------------------------------


class TestParseSaveCommand:
    def test_valid_type_pattern(self):
        source_type, content, needs_extraction = parse_save_command(["pattern", "use", "asyncio.gather"])
        assert source_type == "pattern"
        assert content == "use asyncio.gather"
        assert needs_extraction is False

    def test_valid_type_decision(self):
        source_type, content, needs_extraction = parse_save_command(["decision", "always", "use", "REST"])
        assert source_type == "decision"
        assert content == "always use REST"
        assert needs_extraction is False

    def test_valid_type_skill(self):
        source_type, content, needs_extraction = parse_save_command(["skill", "leadmagic does email lookup"])
        assert source_type == "skill"
        assert content == "leadmagic does email lookup"
        assert needs_extraction is False

    def test_valid_type_reasoning(self):
        source_type, content, needs_extraction = parse_save_command(["reasoning", "because waterfall"])
        assert source_type == "reasoning"
        assert content == "because waterfall"
        assert needs_extraction is False

    def test_valid_type_test_result(self):
        source_type, content, needs_extraction = parse_save_command(["test_result", "stage8 passed"])
        assert source_type == "test_result"
        assert content == "stage8 passed"
        assert needs_extraction is False

    def test_valid_type_dave_confirmed(self):
        source_type, content, needs_extraction = parse_save_command(["dave_confirmed", "ship it"])
        assert source_type == "dave_confirmed"
        assert content == "ship it"
        assert needs_extraction is False

    def test_valid_type_daily_log(self):
        source_type, content, needs_extraction = parse_save_command(["daily_log", "wrapped up stage 8"])
        assert source_type == "daily_log"
        assert content == "wrapped up stage 8"
        assert needs_extraction is False

    def test_unknown_first_word_triggers_extraction(self):
        """Free text not starting with a valid type sets needs_extraction=True."""
        source_type, content, needs_extraction = parse_save_command(["remember", "this", "thing"])
        assert source_type == "daily_log"
        assert content == "remember this thing"
        assert needs_extraction is True

    def test_bare_save_returns_daily_log_empty(self):
        source_type, content, needs_extraction = parse_save_command([])
        assert source_type == "daily_log"
        assert content == ""
        assert needs_extraction is False

    def test_type_only_no_content(self):
        source_type, content, needs_extraction = parse_save_command(["pattern"])
        assert source_type == "pattern"
        assert content == ""
        assert needs_extraction is False

    def test_type_case_insensitive(self):
        source_type, content, needs_extraction = parse_save_command(["PATTERN", "text"])
        assert source_type == "pattern"
        assert content == "text"
        assert needs_extraction is False

    def test_general_bare_text_becomes_daily_log_with_extraction(self):
        source_type, content, needs_extraction = parse_save_command(["some", "raw", "note"])
        assert source_type == "daily_log"
        assert content == "some raw note"
        assert needs_extraction is True

    def test_valid_source_types_used_for_validation(self):
        """parse_save_command uses VALID_SOURCE_TYPES — all members skip extraction."""
        for vtype in VALID_SOURCE_TYPES:
            st, _, needs_ext = parse_save_command([vtype, "content"])
            assert st == vtype
            assert needs_ext is False

    def test_general_is_not_a_valid_type(self):
        """'general' was removed — falls back to daily_log with extraction."""
        source_type, content, needs_extraction = parse_save_command(["general", "some note"])
        assert source_type == "daily_log"
        assert content == "general some note"
        assert needs_extraction is True


# ---------------------------------------------------------------------------
# extract_memory_fields — OpenAI call (fully mocked)
# ---------------------------------------------------------------------------


def _make_openai_response(payload: dict) -> MagicMock:
    """Build a mock openai ChatCompletion response."""
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps(payload)
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


class TestExtractMemoryFields:
    def test_returns_extracted_fields(self):
        expected = {
            "source_type": "decision",
            "content": "Use Supabase for memory because it is already paid for",
            "tags": ["supabase", "memory", "architecture"],
        }
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_openai_response(expected)

        with patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
            result = extract_memory_fields("we decided to use Supabase for memory because it's already paid for")

        assert result["source_type"] == "decision"
        assert result["content"] == expected["content"]
        assert result["tags"] == ["supabase", "memory", "architecture"]

    def test_calls_gpt4o_mini(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_openai_response(
            {"source_type": "daily_log", "content": "test", "tags": ["test"]}
        )
        with patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
            extract_memory_fields("some text")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["temperature"] == 0


# ---------------------------------------------------------------------------
# cmd_save — Telegram handler (fully mocked update/context + store mocked)
# store() is SYNC — use MagicMock (not AsyncMock) for the store patch.
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
    """cmd_save calls store() with correct args for pattern type (no OpenAI)."""
    update, context = _make_update(["pattern", "use", "gather"])

    fake_uuid = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid) as mock_store:
        await cmd_save(update, context)

    assert mock_store.call_count == 1
    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "pattern"
    assert call_kwargs["content"] == "use gather"
    assert call_kwargs["tags"] == ["pattern"]

    update.message.reply_text.assert_awaited_once()
    reply_text = update.message.reply_text.call_args[0][0]
    assert "pattern" in reply_text
    assert "use gather" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_free_text_uses_openai_extraction():
    """Free text (no valid type prefix) triggers OpenAI extraction path."""
    update, context = _make_update(["we", "decided", "to", "use", "Supabase"])

    fake_uuid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    extracted = {
        "source_type": "decision",
        "content": "Use Supabase for memory storage",
        "tags": ["supabase", "memory"],
    }

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(extracted)

    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid) as mock_store, \
         patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
        await cmd_save(update, context)

    assert mock_store.call_count == 1
    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "decision"
    assert call_kwargs["content"] == "Use Supabase for memory storage"
    assert call_kwargs["tags"] == ["supabase", "memory"]

    reply_text = update.message.reply_text.call_args[0][0]
    assert "decision" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_typed_input_skips_openai():
    """Typed input (/save decision ...) never calls OpenAI."""
    update, context = _make_update(["decision", "ship", "it"])

    fake_uuid = uuid.uuid4()
    mock_client = MagicMock()

    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid), \
         patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
        await cmd_save(update, context)

    mock_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_save_openai_failure_falls_back_to_daily_log():
    """If OpenAI extraction fails, falls back to daily_log with raw content."""
    update, context = _make_update(["some", "free", "text"])

    fake_uuid = uuid.UUID("cafebabe-dead-beef-0000-123456789abc")
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("OpenAI timeout")

    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid) as mock_store, \
         patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
        await cmd_save(update, context)

    assert mock_store.call_count == 1
    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "daily_log"
    assert call_kwargs["content"] == "some free text"

    reply_text = update.message.reply_text.call_args[0][0]
    assert "daily_log" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_unknown_type_triggers_extraction():
    """First word not a valid type triggers OpenAI extraction (not direct daily_log)."""
    update, context = _make_update(["remember", "this"])

    fake_uuid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    extracted = {
        "source_type": "pattern",
        "content": "Remember this important pattern",
        "tags": ["pattern"],
    }
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(extracted)

    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid) as mock_store, \
         patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
        await cmd_save(update, context)

    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "pattern"


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

    with patch("src.telegram_bot.save_handler.store", side_effect=Exception("Supabase 500")):
        await cmd_save(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert "Failed" in reply_text or "Supabase" in reply_text


@pytest.mark.asyncio
async def test_cmd_save_uses_valid_source_types_for_validation():
    """store() is called only when source_type is in VALID_SOURCE_TYPES."""
    for vtype in sorted(VALID_SOURCE_TYPES)[:3]:  # spot-check first 3
        update, context = _make_update([vtype, "content"])
        fake_uuid = uuid.uuid4()
        with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid) as mock_store:
            await cmd_save(update, context)
        assert mock_store.call_args.kwargs["source_type"] == vtype


@pytest.mark.asyncio
async def test_cmd_save_reply_contains_uuid():
    """Reply text includes the UUID returned by store()."""
    update, context = _make_update(["skill", "use leadmagic for email"])

    fake_uuid = uuid.UUID("cafebabe-dead-beef-0000-123456789abc")
    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid):
        await cmd_save(update, context)

    reply_text = update.message.reply_text.call_args[0][0]
    assert str(fake_uuid) in reply_text


@pytest.mark.asyncio
async def test_cmd_save_openai_invalid_source_type_falls_back():
    """If OpenAI returns an invalid source_type, fallback to daily_log."""
    update, context = _make_update(["free", "text", "here"])

    fake_uuid = uuid.uuid4()
    extracted = {
        "source_type": "not_a_real_type",
        "content": "Some content",
        "tags": ["tag"],
    }
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(extracted)

    with patch("src.telegram_bot.save_handler.store", return_value=fake_uuid) as mock_store, \
         patch("src.telegram_bot.save_handler.openai.OpenAI", return_value=mock_client):
        await cmd_save(update, context)

    call_kwargs = mock_store.call_args.kwargs
    assert call_kwargs["source_type"] == "daily_log"
