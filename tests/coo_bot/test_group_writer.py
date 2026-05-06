"""Tests for src/coo_bot/group_writer.py — group post wrapper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

from src.coo_bot.group_writer import post_to_group, _PREFIX


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = "ok" if status_code == 200 else "error"
    return resp


def test_post_success():
    """When sendMessage returns 200, post_to_group returns True."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_mock_response(200))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.coo_bot.group_writer.httpx.AsyncClient", return_value=mock_client):
        result = _run(post_to_group("fake-token", "Hello group"))

    assert result is True


def test_post_failure():
    """When sendMessage returns non-200, post_to_group returns False."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=_mock_response(400))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.coo_bot.group_writer.httpx.AsyncClient", return_value=mock_client):
        result = _run(post_to_group("fake-token", "Hello group"))

    assert result is False


def test_prefix_added():
    """[MAX] prefix is prepended to the message text sent to Telegram."""
    sent_payload = {}

    async def capture_post(url, json):
        sent_payload.update(json)
        return _mock_response(200)

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=capture_post)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.coo_bot.group_writer.httpx.AsyncClient", return_value=mock_client):
        _run(post_to_group("fake-token", "status update"))

    assert sent_payload["text"].startswith(_PREFIX)
    assert "status update" in sent_payload["text"]


def test_post_exception_returns_false():
    """Network exception is swallowed and returns False."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("src.coo_bot.group_writer.httpx.AsyncClient", return_value=mock_client):
        result = _run(post_to_group("fake-token", "Hello"))

    assert result is False
