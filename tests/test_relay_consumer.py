"""Tests for src/relay/relay_consumer.py — Change 1b Phase 2 + KEI-138 audit."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.relay.relay_consumer import (
    _classify_dispatch,
    _file_watchers_active,
    format_message,
    inject_into_tmux,
    wait_for_prompt,
)
from src.security.inbox_hmac import sign

# ── _classify_dispatch (KEI-138 — replaces inline _hmac_verify_dict) ─────────


def test_classify_signed_verified(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "test-secret")
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREV", raising=False)
    signed = sign({"type": "task_dispatch", "from": "elliot", "brief": "test"})
    accept, status, idx, reason = _classify_dispatch(signed, hmac_secret_present=True)
    assert accept is True
    assert status == "signed_verified"
    assert idx == 0
    assert reason is None


def test_classify_unsigned_when_secret_present(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "test-secret")
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREV", raising=False)
    accept, status, idx, reason = _classify_dispatch({"type": "text"}, hmac_secret_present=True)
    assert accept is False
    assert status == "unsigned"
    assert idx == -1
    assert "missing" in reason


def test_classify_signed_invalid(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "test-secret")
    monkeypatch.delenv("INBOX_HMAC_SECRET_PREV", raising=False)
    accept, status, idx, reason = _classify_dispatch(
        {"type": "text", "hmac": "deadbeef"}, hmac_secret_present=True
    )
    assert accept is False
    assert status == "signed_invalid"
    assert idx == -1
    assert "mismatch" in reason.lower()


def test_classify_no_secret_accepts_unsigned():
    """Pre-rotation: if env has no secret, dispatch is accepted as no_secret status.

    Matches the legacy behaviour (`if queue_type == "dispatch" and hmac_secret`)
    — verify is only gated on when the operator has set the secret.
    """
    accept, status, idx, reason = _classify_dispatch(
        {"type": "task_dispatch"}, hmac_secret_present=False
    )
    assert accept is True
    assert status == "no_secret"
    assert idx == -1
    assert reason is None


def test_classify_signed_with_prev_secret_during_rotation(monkeypatch):
    monkeypatch.setenv("INBOX_HMAC_SECRET", "new-secret")
    monkeypatch.setenv("INBOX_HMAC_SECRET_PREV", "old-secret")
    signed_with_old = sign({"type": "task_dispatch", "from": "elliot"}, secret="old-secret")
    accept, status, idx, reason = _classify_dispatch(signed_with_old, hmac_secret_present=True)
    assert accept is True
    assert status == "signed_verified"
    assert idx == 1  # PREV slot
    assert reason is None


# ── format_message ───────────────────────────────────────────────────────────


def test_format_inbox_text():
    payload = {"type": "text", "text": "hello", "sender": "dave"}
    result = format_message(payload, "inbox")
    assert result == "[TG-DAVE] hello"


def test_format_inbox_photo():
    payload = {"type": "photo", "file_path": "/tmp/photo.jpg", "caption": "look", "sender": "dave"}
    result = format_message(payload, "inbox")
    assert "screenshot" in result
    assert "/tmp/photo.jpg" in result


def test_format_inbox_document():
    payload = {
        "type": "document",
        "file_path": "/tmp/doc.pdf",
        "file_name": "doc.pdf",
        "sender": "dave",
    }
    result = format_message(payload, "inbox")
    assert "file" in result
    assert "doc.pdf" in result


def test_format_dispatch():
    payload = {"type": "task_dispatch", "from": "elliot", "brief": "fix bug"}
    result = format_message(payload, "dispatch")
    assert result == "[DISPATCH FROM elliot] fix bug"


def test_format_clone_outbox():
    payload = {"text": "done"}
    result = format_message(payload, "clone_outbox", "ATLAS")
    assert result == "[ATLAS] done"


def test_format_unknown_returns_none():
    result = format_message({"type": "unknown"}, "inbox")
    assert result is None


# ── inject_into_tmux ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_inject_success():
    mock_run = AsyncMock(return_value=(0, ""))
    with (
        patch("src.relay.relay_consumer._run_tmux", mock_run),
        patch("src.relay.relay_consumer.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await inject_into_tmux("elliottbot:0.0", "hello world")
    assert result is True
    assert mock_run.call_count == 2  # send-keys text + send-keys C-m


@pytest.mark.asyncio
async def test_inject_failure():
    mock_run = AsyncMock(side_effect=Exception("tmux error"))
    with (
        patch("src.relay.relay_consumer._run_tmux", mock_run),
        patch("src.relay.relay_consumer.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await inject_into_tmux("elliottbot:0.0", "hello")
    assert result is False


# ── file watcher guard ──────────────────────────────────────────────────────


def test_file_watchers_active_detected():
    mock_result = MagicMock(returncode=0)
    with patch("src.relay.relay_consumer.subprocess.run", return_value=mock_result):
        assert _file_watchers_active() is True


def test_file_watchers_not_active():
    mock_result = MagicMock(returncode=1)
    with patch("src.relay.relay_consumer.subprocess.run", return_value=mock_result):
        assert _file_watchers_active() is False


# ── wait_for_prompt ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wait_for_prompt_found():
    mock_run = AsyncMock(return_value=(0, "some text ❯ "))
    with patch("src.relay.relay_consumer._run_tmux", mock_run):
        result = await wait_for_prompt("elliottbot:0.0", max_attempts=1)
    assert result is True


@pytest.mark.asyncio
async def test_wait_for_prompt_not_found():
    mock_run = AsyncMock(return_value=(0, "processing..."))
    with (
        patch("src.relay.relay_consumer._run_tmux", mock_run),
        patch("src.relay.relay_consumer.asyncio.sleep", new_callable=AsyncMock),
    ):
        result = await wait_for_prompt("elliottbot:0.0", max_attempts=2)
    assert result is False
