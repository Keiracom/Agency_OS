"""Tests for src/relay/redis_relay.py — Change 1b Phase 1."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.relay.redis_relay import (
    push, pop, push_sync,
    inbox_queue, outbox_queue, dispatch_queue,
)


# ── Queue name builders ──────────────────────────────────────────────────────

def test_inbox_queue():
    assert inbox_queue("elliot") == "relay:inbox:elliot"

def test_outbox_queue():
    assert outbox_queue("aiden") == "relay:outbox:aiden"

def test_dispatch_queue():
    assert dispatch_queue("atlas") == "dispatch:atlas"


# ── push() ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_success():
    mock_redis = AsyncMock()
    mock_redis.lpush = AsyncMock(return_value=1)
    with patch("src.relay.redis_relay.get_redis", return_value=mock_redis):
        result = await push("relay:outbox:elliot", {"type": "text", "text": "hello"})
    assert result is True
    mock_redis.lpush.assert_called_once()
    args = mock_redis.lpush.call_args
    assert args[0][0] == "relay:outbox:elliot"
    assert json.loads(args[0][1])["text"] == "hello"

@pytest.mark.asyncio
async def test_push_fail_open():
    mock_redis = AsyncMock()
    mock_redis.lpush = AsyncMock(side_effect=ConnectionError("Redis down"))
    with patch("src.relay.redis_relay.get_redis", return_value=mock_redis):
        result = await push("relay:outbox:elliot", {"type": "text"})
    assert result is False


# ── pop() ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pop_success():
    payload = {"type": "text", "text": "hi"}
    mock_redis = AsyncMock()
    mock_redis.brpop = AsyncMock(return_value=("relay:inbox:elliot", json.dumps(payload)))
    with patch("src.relay.redis_relay.get_redis", return_value=mock_redis):
        result = await pop("relay:inbox:elliot", timeout=1)
    assert result == payload

@pytest.mark.asyncio
async def test_pop_timeout():
    mock_redis = AsyncMock()
    mock_redis.brpop = AsyncMock(return_value=None)
    with patch("src.relay.redis_relay.get_redis", return_value=mock_redis):
        result = await pop("relay:inbox:elliot", timeout=1)
    assert result is None

@pytest.mark.asyncio
async def test_pop_fail_open():
    mock_redis = AsyncMock()
    mock_redis.brpop = AsyncMock(side_effect=ConnectionError("Redis down"))
    with patch("src.relay.redis_relay.get_redis", return_value=mock_redis):
        result = await pop("relay:inbox:elliot", timeout=1)
    assert result is None


# ── push_sync() ──────────────────────────────────────────────────────────────

def test_push_sync_success():
    mock_client = MagicMock()
    with patch("src.relay.redis_relay.redis_sync.Redis.from_url", return_value=mock_client), \
         patch.dict("os.environ", {"REDIS_URL": "redis://fake:6379"}):
        result = push_sync("dispatch:atlas", {"type": "task_dispatch", "brief": "test"})
    assert result is True
    mock_client.lpush.assert_called_once()

def test_push_sync_fail_open():
    with patch("src.relay.redis_relay.redis_sync.Redis.from_url", side_effect=ConnectionError("nope")), \
         patch.dict("os.environ", {"REDIS_URL": "redis://fake:6379"}):
        result = push_sync("dispatch:atlas", {"type": "task_dispatch"})
    assert result is False
