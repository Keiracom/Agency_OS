"""Tests for deliverability_monitor — 13 cases covering all thresholds."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from src.outreach.safety.deliverability_monitor import (
    BOUNCE_RATE_PAUSE_THRESHOLD,
    BOUNCE_PAUSE_DURATION,
    DeliverabilityMonitor,
    Health,
    OperatorAlert,
)


NOW = datetime(2026, 4, 22, 12, 0, 0)


def _make_monitor(mailbox_stats=None, linkedin_stats=None, alert_fn=None):
    alert_fn = alert_fn or (lambda _: None)
    return DeliverabilityMonitor(
        get_mailbox_stats=lambda _: mailbox_stats or {},
        get_linkedin_stats=lambda _: linkedin_stats or {},
        emit_operator_alert=alert_fn,
        now_fn=lambda: NOW,
    )


def _mailbox(sends, bounces, complaints=0, paused_until=None):
    return {
        "sends": sends,
        "bounces": bounces,
        "complaints": complaints,
        "since": NOW - timedelta(days=30),
        "paused_until": paused_until,
    }


def _linkedin(last_402_at=None, last_429_at=None, cooldown_until=None):
    return {
        "last_402_at": last_402_at,
        "last_429_at": last_429_at,
        "cooldown_until": cooldown_until,
    }


# ── Mailbox cases ─────────────────────────────────────────────────────────────


def test_1_mailbox_healthy():
    """200 sends, 2 bounces (1%), 0 complaints → HEALTHY, no alert."""
    alerts = []
    m = _make_monitor(mailbox_stats=_mailbox(200, 2), alert_fn=alerts.append)
    d = m.check_mailbox("mb1")
    assert d.health == Health.HEALTHY
    assert len(alerts) == 0


def test_2_mailbox_insufficient_sample():
    """50 sends, 5 bounces (10%) → HEALTHY with 'insufficient sample'."""
    m = _make_monitor(mailbox_stats=_mailbox(50, 5))
    d = m.check_mailbox("mb2")
    assert d.health == Health.HEALTHY
    assert "insufficient sample" in d.reason


def test_3_mailbox_degraded():
    """200 sends, 7 bounces (3.5%) → DEGRADED, no alert."""
    alerts = []
    m = _make_monitor(mailbox_stats=_mailbox(200, 7), alert_fn=alerts.append)
    d = m.check_mailbox("mb3")
    assert d.health == Health.DEGRADED
    assert len(alerts) == 0
    assert d.resume_at is None


def test_4_mailbox_paused_on_bounce():
    """200 sends, 12 bounces (6%) → PAUSED, resume_at ≈ now+72h, alert emitted."""
    alerts = []
    m = _make_monitor(mailbox_stats=_mailbox(200, 12), alert_fn=alerts.append)
    d = m.check_mailbox("mb4")
    assert d.health == Health.PAUSED
    assert d.resume_at == NOW + BOUNCE_PAUSE_DURATION
    assert len(alerts) == 1
    assert alerts[0].health == Health.PAUSED
    assert alerts[0].mailbox_id == "mb4"


def test_5_mailbox_quarantined_on_complaint():
    """200 sends, 1 complaint (0.5%) → QUARANTINED, resume_at=None, alert."""
    alerts = []
    m = _make_monitor(mailbox_stats=_mailbox(200, 0, complaints=1), alert_fn=alerts.append)
    d = m.check_mailbox("mb5")
    assert d.health == Health.QUARANTINED
    assert d.resume_at is None
    assert len(alerts) == 1
    assert alerts[0].health == Health.QUARANTINED


def test_6_quarantine_beats_pause():
    """200 sends, 12 bounces + 1 complaint → QUARANTINED (higher priority)."""
    alerts = []
    m = _make_monitor(mailbox_stats=_mailbox(200, 12, complaints=1), alert_fn=alerts.append)
    d = m.check_mailbox("mb6")
    assert d.health == Health.QUARANTINED
    assert len(alerts) == 1


def test_7_honour_paused_until():
    """paused_until=now+24h → PAUSED, no stats evaluation, no alert."""
    alerts = []
    paused_until = NOW + timedelta(hours=24)
    m = _make_monitor(
        mailbox_stats=_mailbox(200, 12, paused_until=paused_until),
        alert_fn=alerts.append,
    )
    d = m.check_mailbox("mb7")
    assert d.health == Health.PAUSED
    assert d.resume_at == paused_until
    assert len(alerts) == 0


# ── LinkedIn cases ─────────────────────────────────────────────────────────────


def test_8_linkedin_healthy():
    """No 402/429, no cooldown → HEALTHY."""
    m = _make_monitor(linkedin_stats=_linkedin())
    d = m.check_linkedin_account("li1")
    assert d.health == Health.HEALTHY


def test_9_linkedin_in_cooldown_from_recent_429():
    """last_429_at=now-1day → PAUSED, resume_at ≈ last_429_at+7d, alert."""
    alerts = []
    last_429 = NOW - timedelta(days=1)
    m = _make_monitor(linkedin_stats=_linkedin(last_429_at=last_429), alert_fn=alerts.append)
    d = m.check_linkedin_account("li2")
    assert d.health == Health.PAUSED
    assert d.resume_at == last_429 + timedelta(days=7)
    assert len(alerts) == 1
    assert alerts[0].linkedin_account_id == "li2"


def test_10_linkedin_cooldown_expired():
    """last_429_at=now-8day → HEALTHY (cooldown_until is None or past)."""
    alerts = []
    m = _make_monitor(
        linkedin_stats=_linkedin(last_429_at=NOW - timedelta(days=8)),
        alert_fn=alerts.append,
    )
    d = m.check_linkedin_account("li3")
    assert d.health == Health.HEALTHY
    assert len(alerts) == 0


def test_11_linkedin_existing_cooldown_until():
    """cooldown_until=now+3day → PAUSED, resume_at=cooldown_until, no new alert."""
    alerts = []
    cooldown_until = NOW + timedelta(days=3)
    m = _make_monitor(
        linkedin_stats=_linkedin(cooldown_until=cooldown_until),
        alert_fn=alerts.append,
    )
    d = m.check_linkedin_account("li4")
    assert d.health == Health.PAUSED
    assert d.resume_at == cooldown_until
    assert len(alerts) == 0  # no new alert — already recorded


def test_12_alert_emission_uses_injected_callable():
    """Mock assertion on call_args for alert callable."""
    mock_alert = MagicMock()
    m = _make_monitor(mailbox_stats=_mailbox(200, 12), alert_fn=mock_alert)
    m.check_mailbox("mb12")
    mock_alert.assert_called_once()
    alert_arg: OperatorAlert = mock_alert.call_args[0][0]
    assert isinstance(alert_arg, OperatorAlert)
    assert alert_arg.mailbox_id == "mb12"
    assert alert_arg.health == Health.PAUSED


def test_13_threshold_configurable():
    """Patch BOUNCE_RATE_PAUSE_THRESHOLD=0.02; a 3% mailbox now pauses."""
    alerts = []
    with patch(
        "src.outreach.safety.deliverability_monitor.BOUNCE_RATE_PAUSE_THRESHOLD",
        0.02,
    ):
        m = _make_monitor(mailbox_stats=_mailbox(200, 6), alert_fn=alerts.append)
        d = m.check_mailbox("mb13")
    assert d.health == Health.PAUSED
    assert len(alerts) == 1
