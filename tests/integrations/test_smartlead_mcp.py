"""tests/integrations/test_smartlead_mcp.py — unit tests for the SmartLead MCP wrapper.

Mocks `asyncio.create_subprocess_exec` so no actual MCP bridge is invoked.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integrations import smartlead_mcp


def _mock_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""):
    """Build a mock subprocess.Process with communicate() returning the given bytes."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


# ── purchase_domain ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_purchase_domain_returns_parsed_json():
    proc = _mock_proc(stdout=b'{"email_account_id": 12345, "status": "ok"}')
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = await smartlead_mcp.purchase_domain("acme-outreach.com")
    assert result["email_account_id"] == 12345
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_purchase_domain_normalises_input():
    """Domain name is stripped + lower-cased before the MCP call."""
    captured: dict = {}

    async def capturing_exec(*cmd, **kwargs):
        captured["args_json"] = cmd[-1]  # last arg is the json blob
        return _mock_proc(stdout=b'{"id": 1}')

    with patch("asyncio.create_subprocess_exec", capturing_exec):
        await smartlead_mcp.purchase_domain("  ACME-OUTREACH.COM  ")

    payload = json.loads(captured["args_json"])
    assert payload == {"domain": "acme-outreach.com"}


@pytest.mark.asyncio
async def test_purchase_domain_rejects_empty():
    with pytest.raises(ValueError, match="non-empty"):
        await smartlead_mcp.purchase_domain("")


@pytest.mark.asyncio
async def test_purchase_domain_rejects_invalid_chars():
    with pytest.raises(ValueError, match="bare domain"):
        await smartlead_mcp.purchase_domain("acme.com/path")
    with pytest.raises(ValueError, match="bare domain"):
        await smartlead_mcp.purchase_domain("acme com")


@pytest.mark.asyncio
async def test_purchase_domain_raises_on_nonzero_exit():
    proc = _mock_proc(returncode=1, stderr=b"smartlead 401 unauthorized")
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        pytest.raises(smartlead_mcp.SmartleadMCPError, match="exit 1"),
    ):
        await smartlead_mcp.purchase_domain("acme.com")


@pytest.mark.asyncio
async def test_purchase_domain_raises_on_empty_stdout():
    proc = _mock_proc(returncode=0, stdout=b"")
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        pytest.raises(smartlead_mcp.SmartleadMCPError, match="empty stdout"),
    ):
        await smartlead_mcp.purchase_domain("acme.com")


@pytest.mark.asyncio
async def test_purchase_domain_recovers_json_from_noisy_stdout():
    """MCP bridge sometimes prepends diagnostic lines; helper recovers the last JSON line."""
    noisy = b"diagnostic line\nanother diagnostic\n{\"id\": 99, \"status\": \"ok\"}\n"
    proc = _mock_proc(stdout=noisy)
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        result = await smartlead_mcp.purchase_domain("acme.com")
    assert result == {"id": 99, "status": "ok"}


@pytest.mark.asyncio
async def test_purchase_domain_raises_on_unparseable():
    """No recoverable JSON in stdout → SmartleadMCPError."""
    proc = _mock_proc(stdout=b"plain text, not json")
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        pytest.raises(smartlead_mcp.SmartleadMCPError, match="non-JSON"),
    ):
        await smartlead_mcp.purchase_domain("acme.com")


# ── get_warmup_stats ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_warmup_stats_returns_parsed_json():
    proc = _mock_proc(
        stdout=b'{"warmup_status": "ready", "sent_7d": 150, "replied_7d": 42}'
    )
    with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)):
        stats = await smartlead_mcp.get_warmup_stats(12345)
    assert stats["warmup_status"] == "ready"
    assert stats["sent_7d"] == 150


@pytest.mark.asyncio
async def test_get_warmup_stats_accepts_string_id():
    """Some external systems use string-encoded IDs; helper passes through."""
    captured: dict = {}

    async def capturing_exec(*cmd, **kwargs):
        captured["args_json"] = cmd[-1]
        return _mock_proc(stdout=b'{"warmup_status": "warming"}')

    with patch("asyncio.create_subprocess_exec", capturing_exec):
        await smartlead_mcp.get_warmup_stats("acct-789")

    payload = json.loads(captured["args_json"])
    assert payload == {"email_account_id": "acct-789"}


@pytest.mark.asyncio
async def test_get_warmup_stats_rejects_none():
    with pytest.raises(ValueError, match="non-empty"):
        await smartlead_mcp.get_warmup_stats(None)
    with pytest.raises(ValueError, match="non-empty"):
        await smartlead_mcp.get_warmup_stats("")


@pytest.mark.asyncio
async def test_get_warmup_stats_propagates_bridge_error():
    proc = _mock_proc(returncode=2, stderr=b"smartlead 404 not found")
    with (
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=proc)),
        pytest.raises(smartlead_mcp.SmartleadMCPError, match="exit 2"),
    ):
        await smartlead_mcp.get_warmup_stats(12345)


# ── shell_safe_repr_for_logs ──────────────────────────────────────────────────


def test_shell_safe_repr_for_logs():
    """Helper produces a single-quoted shell-safe string."""
    s = smartlead_mcp.shell_safe_repr_for_logs({"domain": "acme.com"})
    # shlex.quote wraps in single quotes when needed
    assert s.startswith("'") or s == '{"domain": "acme.com"}'
    assert "domain" in s
