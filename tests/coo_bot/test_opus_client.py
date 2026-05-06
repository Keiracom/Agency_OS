"""Tests for src/coo_bot/opus_client.py — Opus CLI subprocess wrapper."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.coo_bot.opus_client import opus_call


def _run(coro):
    """Run an async coro on a fresh event loop — avoids cross-test pollution."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_happy_path():
    """opus_call returns stdout on success."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"response text", b""))
    mock_proc.returncode = 0

    with patch("src.coo_bot.opus_client.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = _run(opus_call("system", "user"))
    assert result == "response text"


def test_non_zero_exit_returns_empty():
    """opus_call returns '' on non-zero exit code."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b"error msg"))
    mock_proc.returncode = 1

    with patch("src.coo_bot.opus_client.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = _run(opus_call("system", "user"))
    assert result == ""


def test_timeout_returns_empty():
    """opus_call returns '' on timeout."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    mock_proc.kill = MagicMock()

    with patch("src.coo_bot.opus_client.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = _run(opus_call("system", "user", timeout=1))
    assert result == ""


def test_missing_binary_returns_empty():
    """opus_call returns '' when claude binary not found."""
    with patch(
        "src.coo_bot.opus_client.asyncio.create_subprocess_exec", side_effect=FileNotFoundError()
    ):
        result = _run(opus_call("system", "user"))
    assert result == ""


def test_empty_stdout_returns_empty():
    """opus_call returns '' on empty stdout."""
    mock_proc = AsyncMock()
    mock_proc.communicate = AsyncMock(return_value=(b"  \n  ", b""))
    mock_proc.returncode = 0

    with patch("src.coo_bot.opus_client.asyncio.create_subprocess_exec", return_value=mock_proc):
        result = _run(opus_call("system", "user"))
    assert result == ""
