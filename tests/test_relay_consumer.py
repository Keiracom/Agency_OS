"""Tests for src/relay/relay_consumer.py — Change 1b Phase 2."""
import hashlib
import hmac
import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.relay.relay_consumer import (
    _hmac_verify_dict,
    format_message,
    inject_into_tmux,
    wait_for_prompt,
)


# ── HMAC verify ──────────────────────────────────────────────────────────────

def test_hmac_verify_valid():
    secret = "test-secret"
    payload = {"type": "task_dispatch", "from": "elliot", "brief": "test"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
    signed = {**payload, "hmac": sig}
    ok, reason = _hmac_verify_dict(signed, secret)
    assert ok is True
    assert reason == "ok"

def test_hmac_verify_missing():
    ok, reason = _hmac_verify_dict({"type": "text"}, "secret")
    assert ok is False
    assert "missing" in reason

def test_hmac_verify_mismatch():
    ok, reason = _hmac_verify_dict({"type": "text", "hmac": "bad"}, "secret")
    assert ok is False
    assert "mismatch" in reason.lower()


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
    payload = {"type": "document", "file_path": "/tmp/doc.pdf", "file_name": "doc.pdf", "sender": "dave"}
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

def test_inject_success():
    with patch("src.relay.relay_consumer.subprocess.run") as mock_run, \
         patch("src.relay.relay_consumer.time.sleep"):
        mock_run.return_value = MagicMock(returncode=0)
        result = inject_into_tmux("elliottbot:0.0", "hello world")
    assert result is True
    assert mock_run.call_count == 2  # send-keys text + send-keys C-m

def test_inject_failure():
    with patch("src.relay.relay_consumer.subprocess.run", side_effect=Exception("tmux error")), \
         patch("src.relay.relay_consumer.time.sleep"):
        result = inject_into_tmux("elliottbot:0.0", "hello")
    assert result is False


# ── wait_for_prompt ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wait_for_prompt_found():
    mock_result = MagicMock()
    mock_result.stdout = "some text ❯ "
    with patch("src.relay.relay_consumer.subprocess.run", return_value=mock_result):
        result = await wait_for_prompt("elliottbot:0.0", max_attempts=1)
    assert result is True

@pytest.mark.asyncio
async def test_wait_for_prompt_not_found():
    mock_result = MagicMock()
    mock_result.stdout = "processing..."
    with patch("src.relay.relay_consumer.subprocess.run", return_value=mock_result), \
         patch("src.relay.relay_consumer.asyncio.sleep", new_callable=AsyncMock):
        result = await wait_for_prompt("elliottbot:0.0", max_attempts=2)
    assert result is False
