"""Tests for src/outreach/safety/alert_emitter.py — 10 cases."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from src.outreach.safety.alert_emitter import (
    DEDUPE_WINDOW,
    TelegramAlertEmitter,
    format_alert,
)
from src.outreach.safety.deliverability_monitor import Health, OperatorAlert


# --- helpers ---

def _mailbox_alert(health: Health, reason: str = "bounce rate 6.0000% >= 5.0000%") -> OperatorAlert:
    return OperatorAlert(mailbox_id="mb-001", linkedin_account_id=None, health=health, reason=reason)


def _linkedin_alert() -> OperatorAlert:
    return OperatorAlert(
        mailbox_id=None,
        linkedin_account_id="li-999",
        health=Health.PAUSED,
        reason="LinkedIn rate-limit event",
    )


def _quarantine_alert() -> OperatorAlert:
    return OperatorAlert(
        mailbox_id="mb-001",
        linkedin_account_id=None,
        health=Health.QUARANTINED,
        reason="spam complaint rate 0.1500% >= 0.1000%",
    )


# --- format_alert tests ---

def test_format_alert_mailbox_paused():
    msg = format_alert(_mailbox_alert(Health.PAUSED))
    assert "[DELIVERABILITY]" in msg
    assert "mb-001" in msg
    assert "paused 72hr" in msg
    assert "5%" in msg


def test_format_alert_quarantined():
    msg = format_alert(_quarantine_alert())
    assert "QUARANTINED" in msg
    assert "0.1%" in msg
    assert "mb-001" in msg


def test_format_alert_linkedin_cooldown():
    msg = format_alert(_linkedin_alert())
    assert "LinkedIn account" in msg
    assert "li-999" in msg
    assert "paused 7d" in msg
    assert "402/429" in msg


def test_format_alert_healthy_defensive():
    """HEALTHY alerts should return a non-empty defensive string, not raise."""
    alert = OperatorAlert(
        mailbox_id="mb-x", linkedin_account_id=None, health=Health.HEALTHY, reason="all clear"
    )
    result = format_alert(alert)
    assert isinstance(result, str) and len(result) > 0


# --- TelegramAlertEmitter behavioural tests ---

def test_alert_invokes_send_fn_once():
    send = Mock()
    emitter = TelegramAlertEmitter(send_fn=send)
    emitter(_mailbox_alert(Health.PAUSED))
    send.assert_called_once()


def test_dedupe_same_mailbox_same_health():
    """Two emits within window for same target+health => one send."""
    send = Mock()
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    emitter = TelegramAlertEmitter(send_fn=send, now_fn=lambda: now)
    emitter(_mailbox_alert(Health.PAUSED))
    emitter(_mailbox_alert(Health.PAUSED))
    assert send.call_count == 1


def test_dedupe_different_health():
    """PAUSED then QUARANTINED for same mailbox => two separate sends."""
    send = Mock()
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    emitter = TelegramAlertEmitter(send_fn=send, now_fn=lambda: now)
    emitter(_mailbox_alert(Health.PAUSED))
    emitter(_quarantine_alert())
    assert send.call_count == 2


def test_dedupe_expires_after_window():
    """Second call fires after dedupe window has elapsed."""
    send = Mock()
    base = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    tick = {"t": base}

    def now_fn():
        return tick["t"]

    emitter = TelegramAlertEmitter(send_fn=send, now_fn=now_fn, dedupe_window=timedelta(hours=1))
    emitter(_mailbox_alert(Health.PAUSED))
    tick["t"] = base + timedelta(hours=1, seconds=1)
    emitter(_mailbox_alert(Health.PAUSED))
    assert send.call_count == 2


def test_missing_token_swallows_error(monkeypatch):
    """Default send_fn with no TELEGRAM_TOKEN logs warning and does NOT raise."""
    monkeypatch.delitem(os.environ, "TELEGRAM_TOKEN", raising=False)
    emitter = TelegramAlertEmitter()  # uses default _send_to_supergroup
    # Should complete without raising
    emitter(_mailbox_alert(Health.PAUSED))


def test_dedupe_key_differs_per_target():
    """mailbox-A paused + mailbox-B paused in same window => two sends."""
    send = Mock()
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    emitter = TelegramAlertEmitter(send_fn=send, now_fn=lambda: now)
    alert_a = OperatorAlert(mailbox_id="mb-A", linkedin_account_id=None, health=Health.PAUSED, reason="x")
    alert_b = OperatorAlert(mailbox_id="mb-B", linkedin_account_id=None, health=Health.PAUSED, reason="x")
    emitter(alert_a)
    emitter(alert_b)
    assert send.call_count == 2
