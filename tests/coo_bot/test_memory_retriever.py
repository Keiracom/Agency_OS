"""tests/coo_bot/test_memory_retriever.py — unit tests for COO memory loaders.

MAX-COO-PHASE-B / Phase B File 2.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_env(monkeypatch):
    """Default: supabase backend so retrievers hit _supabase_client path."""
    monkeypatch.setenv("MEMORY_RECALL_BACKEND", "supabase")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "test-service-key")


def _mock_response(rows):
    """Build a fake supabase response object exposing `.data`."""
    resp = MagicMock()
    resp.data = rows
    return resp


def _build_mock_client(rows):
    """Build a mock client whose chained query call returns `rows`."""
    client = MagicMock()
    chain = client.table.return_value
    chain.select.return_value = chain
    chain.ilike.return_value = chain
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.like.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.execute.return_value = _mock_response(rows)
    return client


def _run(coro):
    """Run an async coro on a fresh event loop — avoids cross-test pollution."""
    import asyncio

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_supabase_returns_rows():
    from src.coo_bot import memory_retriever as mr

    rows = [{"id": "1", "content": "hello world", "source_type": "research"}]
    with patch.object(mr, "_supabase_client", return_value=_build_mock_client(rows)):
        out = _run(mr.get_relevant_memories("hello", limit=5))
    assert out == rows


def test_empty_result_returns_empty_list():
    from src.coo_bot import memory_retriever as mr

    with patch.object(mr, "_supabase_client", return_value=_build_mock_client([])):
        assert _run(mr.get_relevant_memories("nothing-matches")) == []
        assert mr.get_high_value_memories(callsign="aiden") == []
        assert mr.get_ceo_memory_keys("ceo:") == []


def test_exception_returns_empty_list():
    from src.coo_bot import memory_retriever as mr

    failing_client = MagicMock()
    failing_client.table.side_effect = RuntimeError("boom")
    with patch.object(mr, "_supabase_client", return_value=failing_client):
        assert _run(mr.get_relevant_memories("anything")) == []
        assert mr.get_high_value_memories() == []
        assert mr.get_ceo_memory_keys("ceo:") == []


def test_hybrid_backend_uses_memory_listener_path(monkeypatch):
    from src.coo_bot import memory_retriever as mr

    monkeypatch.setenv("MEMORY_RECALL_BACKEND", "hybrid")
    monkeypatch.setenv("CALLSIGN", "orion")

    expected = [{"content": "from-mem0", "source_type": "pattern"}]

    async def _fake_recall(query, callsign, limit):
        assert query == "test query"
        assert callsign == "orion"
        assert limit == 5
        return expected

    fake_module = MagicMock()
    fake_module.recall_via_mem0 = _fake_recall
    with patch.dict(
        "sys.modules",
        {"src.telegram_bot.memory_listener": fake_module},
    ):
        out = _run(mr.get_relevant_memories("test query", limit=5))
    assert out == expected


def test_supabase_fallback_when_memory_listener_unavailable(monkeypatch):
    """When MEMORY_RECALL_BACKEND=hybrid but the import or recall call
    raises, get_relevant_memories falls back to the supabase ilike path."""
    from src.coo_bot import memory_retriever as mr

    monkeypatch.setenv("MEMORY_RECALL_BACKEND", "hybrid")

    fallback_rows = [{"id": "fb", "content": "fallback row"}]

    async def _broken_recall(*args, **kwargs):
        raise RuntimeError("mem0 unreachable")

    fake_module = MagicMock()
    fake_module.recall_via_mem0 = _broken_recall

    with patch.dict("sys.modules", {"src.telegram_bot.memory_listener": fake_module}):
        with patch.object(
            mr,
            "_supabase_client",
            return_value=_build_mock_client(fallback_rows),
        ):
            out = _run(mr.get_relevant_memories("query"))
    assert out == fallback_rows
