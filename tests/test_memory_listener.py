"""
Tests for src/telegram_bot/memory_listener.py
"""

import sys
import os

# Ensure the telegram_bot package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "telegram_bot"))

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from memory_listener import (
    find_relevant_memories,
    format_memory_context,
    MAX_RELEVANCE_RESULTS,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_ROW = {
    "id": "abc-123",
    "source_type": "decision",
    "content": "Pipeline F uses Bright Data for LinkedIn enrichment",
    "tags": ["pipeline", "linkedin"],
    "created_at": "2026-04-10T12:00:00Z",
    "callsign": "elliot",
    "access_count": 2,
}

SUPABASE_ENV = {
    "SUPABASE_URL": "https://fake.supabase.co",
    "SUPABASE_SERVICE_KEY": "fake-key",
}


# ---------------------------------------------------------------------------
# find_relevant_memories — returns results on 200 response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_relevant_memories_returns_results():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [FAKE_ROW]

    with patch.dict(os.environ, SUPABASE_ENV):
        with patch("memory_listener.httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            instance.get = AsyncMock(return_value=mock_response)
            instance.patch = AsyncMock(return_value=MagicMock(status_code=204))

            results = await find_relevant_memories("Pipeline LinkedIn enrichment details")

    assert len(results) >= 1
    assert results[0]["id"] == "abc-123"
    assert results[0]["source_type"] == "decision"


# ---------------------------------------------------------------------------
# find_relevant_memories — empty message returns empty list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_relevant_memories_empty_message():
    with patch.dict(os.environ, SUPABASE_ENV):
        results = await find_relevant_memories("")
    assert results == []


@pytest.mark.asyncio
async def test_find_relevant_memories_short_message():
    with patch.dict(os.environ, SUPABASE_ENV):
        results = await find_relevant_memories("hi")
    assert results == []


# ---------------------------------------------------------------------------
# find_relevant_memories — no env vars → empty list (no crash)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_relevant_memories_no_env():
    with patch.dict(os.environ, {}, clear=True):
        # Patch the module-level globals directly
        import memory_listener as ml

        original_url, original_key = ml.SUPABASE_URL, ml.SUPABASE_KEY
        ml.SUPABASE_URL = ""
        ml.SUPABASE_KEY = ""
        try:
            results = await find_relevant_memories("this message should fail gracefully")
        finally:
            ml.SUPABASE_URL = original_url
            ml.SUPABASE_KEY = original_key
    assert results == []


# ---------------------------------------------------------------------------
# find_relevant_memories — Supabase failure doesn't crash (returns empty)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_relevant_memories_supabase_failure():
    with patch.dict(os.environ, SUPABASE_ENV):
        with patch("memory_listener.httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            instance.get = AsyncMock(side_effect=Exception("connection refused"))

            results = await find_relevant_memories("what is the pipeline config")

    assert results == []


# ---------------------------------------------------------------------------
# find_relevant_memories — access_count increment is called for each result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_relevant_memories_increments_access_count():
    mock_get = MagicMock()
    mock_get.status_code = 200
    mock_get.json.return_value = [FAKE_ROW]

    mock_patch = AsyncMock(return_value=MagicMock(status_code=204))

    with patch.dict(os.environ, SUPABASE_ENV):
        with patch("memory_listener.httpx.AsyncClient") as MockClient:
            instance = MagicMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            instance.get = AsyncMock(return_value=mock_get)
            instance.patch = mock_patch

            results = await find_relevant_memories("Pipeline LinkedIn enrichment details")

    # patch should have been called at least once for the returned row
    assert instance.patch.called
    call_kwargs = instance.patch.call_args_list[0]
    # The JSON body should increment access_count from 2 → 3
    assert call_kwargs.kwargs["json"]["access_count"] == 3


# ---------------------------------------------------------------------------
# format_memory_context — produces correct block
# ---------------------------------------------------------------------------


def test_format_memory_context_produces_correct_format():
    memories = [FAKE_ROW]
    result = format_memory_context(memories)
    assert result.startswith("[MEMORY CONTEXT")
    assert "[END MEMORY CONTEXT]" in result
    assert "decision" in result
    assert "2026-04-10" in result
    assert "Pipeline F" in result


def test_format_memory_context_empty():
    result = format_memory_context([])
    assert result == ""


def test_format_memory_context_truncates_content():
    long_row = {**FAKE_ROW, "content": "x" * 1000}
    result = format_memory_context([long_row])
    # Content is capped at 500 chars inside the block
    lines = result.splitlines()
    content_line = next(l for l in lines if "xxx" in l)
    assert len(content_line) < 600  # well under 1000


def test_format_memory_context_multiple_rows():
    rows = [
        {**FAKE_ROW, "id": "row-1", "source_type": "core_fact"},
        {**FAKE_ROW, "id": "row-2", "source_type": "daily_log", "content": "Daily summary"},
    ]
    result = format_memory_context(rows)
    assert "core_fact" in result
    assert "daily_log" in result
    assert "Daily summary" in result
