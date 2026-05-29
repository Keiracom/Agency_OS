"""Unit tests for scripts/orchestrator/silent_failure_probe.py (Agency_OS-52wu).

No DB / no systemd / no Slack. Pure-function tests for all three evaluators
plus registry loading and idempotency logic.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "orchestrator"))

import silent_failure_probe as sfp  # noqa: E402

_NOW = _dt.datetime(2026, 5, 29, 10, 0, 0, tzinfo=_dt.UTC)


# ── ServiceEntry factory helpers ─────────────────────────────────────────────


def _entry_systemd(name: str = "test-svc", criticality: str = "P0") -> sfp.ServiceEntry:
    return sfp.ServiceEntry(
        name=name,
        check="systemd",
        criticality=criticality,
        description="test service",
    )


def _entry_timer(
    name: str = "test-timer",
    window_hours: float = 2.0,
    criticality: str = "P0",
) -> sfp.ServiceEntry:
    return sfp.ServiceEntry(
        name=name,
        check="timer",
        criticality=criticality,
        description="test timer",
        timer_window_hours=window_hours,
    )


def _entry_heartbeat(
    name: str = "test-hb",
    stale_minutes: int = 10,
    criticality: str = "P0",
) -> sfp.ServiceEntry:
    return sfp.ServiceEntry(
        name=name,
        check="heartbeat",
        criticality=criticality,
        description="test heartbeat",
        stale_minutes=stale_minutes,
    )


# ── evaluate_systemd ─────────────────────────────────────────────────────────


# ACCEPTANCE TEST 1 — active service never fires.
def test_systemd_active_no_miss():
    assert sfp.evaluate_systemd(_entry_systemd(), "active") is None


def test_systemd_failed_fires_miss():
    miss = sfp.evaluate_systemd(_entry_systemd(), "failed")
    assert miss is not None
    assert miss.reason == "systemd_not_active"
    assert "failed" in miss.detail


def test_systemd_inactive_fires_miss():
    miss = sfp.evaluate_systemd(_entry_systemd(), "inactive")
    assert miss is not None
    assert miss.reason == "systemd_not_active"


def test_systemd_unknown_fires_miss():
    miss = sfp.evaluate_systemd(_entry_systemd(), "unknown")
    assert miss is not None
    assert miss.reason == "systemd_not_active"


# ── evaluate_timer ───────────────────────────────────────────────────────────


# ACCEPTANCE TEST 2 — timer never run → alert.
def test_timer_never_run_fires_miss():
    miss = sfp.evaluate_timer(_entry_timer(), last_trigger=None, now=_NOW)
    assert miss is not None
    assert miss.reason == "timer_never_run"


def test_timer_within_window_no_miss():
    # Last run 30 min ago, window 2h → fine.
    last = _NOW - _dt.timedelta(minutes=30)
    assert sfp.evaluate_timer(_entry_timer(window_hours=2.0), last, _NOW) is None


def test_timer_just_past_window_fires_miss():
    # Last run 2.1h ago, window 2h → stale.
    last = _NOW - _dt.timedelta(hours=2, minutes=6)
    miss = sfp.evaluate_timer(_entry_timer(window_hours=2.0), last, _NOW)
    assert miss is not None
    assert miss.reason == "timer_stale"
    assert "2.0h" in miss.detail


def test_timer_exactly_at_boundary_no_miss():
    # Exactly at window boundary — not past it.
    last = _NOW - _dt.timedelta(hours=2, seconds=0)
    # 2.0h == window 2.0 → boundary (not strictly greater than)
    entry = _entry_timer(window_hours=2.0)
    miss = sfp.evaluate_timer(entry, last, _NOW)
    # age_hours == timer_window_hours → NOT stale (>) not (>=)
    assert miss is None


# ── evaluate_heartbeat ───────────────────────────────────────────────────────


# ACCEPTANCE TEST 3 — missing heartbeat key → alert.
def test_heartbeat_missing_key_fires_miss():
    miss = sfp.evaluate_heartbeat(_entry_heartbeat(), hb_state=None, now=_NOW)
    assert miss is not None
    assert miss.reason == "heartbeat_missing"


def test_heartbeat_fresh_no_miss():
    hb = {"last_tick_ts": (_NOW - _dt.timedelta(minutes=3)).isoformat()}
    assert sfp.evaluate_heartbeat(_entry_heartbeat(stale_minutes=10), hb, _NOW) is None


def test_heartbeat_stale_fires_miss():
    hb = {"last_tick_ts": (_NOW - _dt.timedelta(minutes=20)).isoformat()}
    miss = sfp.evaluate_heartbeat(_entry_heartbeat(stale_minutes=10), hb, _NOW)
    assert miss is not None
    assert miss.reason == "heartbeat_stale"
    assert "20.0min" in miss.detail


def test_heartbeat_unparseable_ts_fires_miss():
    hb = {"last_tick_ts": "not-a-timestamp"}
    miss = sfp.evaluate_heartbeat(_entry_heartbeat(), hb, _NOW)
    assert miss is not None
    assert miss.reason == "heartbeat_unparseable"


def test_heartbeat_missing_ts_key_fires_miss():
    miss = sfp.evaluate_heartbeat(_entry_heartbeat(), hb_state={}, now=_NOW)
    assert miss is not None
    assert miss.reason == "heartbeat_unparseable"


# ── Criticality preserved ────────────────────────────────────────────────────


def test_p0_criticality_preserved_on_systemd_miss():
    miss = sfp.evaluate_systemd(_entry_systemd(criticality="P0"), "failed")
    assert miss is not None and miss.criticality == "P0"


def test_p1_criticality_preserved_on_systemd_miss():
    miss = sfp.evaluate_systemd(_entry_systemd(criticality="P1"), "failed")
    assert miss is not None and miss.criticality == "P1"


def test_p0_criticality_preserved_on_timer_miss():
    miss = sfp.evaluate_timer(_entry_timer(criticality="P0"), None, _NOW)
    assert miss is not None and miss.criticality == "P0"


# ── Idempotency — process_miss ───────────────────────────────────────────────


# ACCEPTANCE TEST 4 — second miss with pending debt → no duplicate alert.
def test_process_miss_skips_alert_when_debt_pending():
    miss = sfp.LivenessMiss("svc", "systemd_not_active", "state=failed", "P0")
    conn = MagicMock()

    with (
        patch.object(sfp, "get_debt_row", return_value={"status": "pending"}),
        patch.object(sfp, "emit_alert") as mock_alert,
        patch.object(sfp, "upsert_debt_row") as mock_debt,
    ):
        sfp.process_miss(miss, conn, dry_run=False)

    mock_alert.assert_not_called()
    mock_debt.assert_not_called()


def test_process_miss_fires_alert_when_no_debt():
    miss = sfp.LivenessMiss("svc", "systemd_not_active", "state=failed", "P0")
    conn = MagicMock()

    with (
        patch.object(sfp, "get_debt_row", return_value=None),
        patch.object(sfp, "emit_alert") as mock_alert,
        patch.object(sfp, "upsert_debt_row") as mock_debt,
    ):
        sfp.process_miss(miss, conn, dry_run=False)

    mock_alert.assert_called_once_with(miss, dry_run=False)
    mock_debt.assert_called_once()


def test_process_miss_dry_run_no_debt_write():
    miss = sfp.LivenessMiss("svc", "systemd_not_active", "state=failed", "P0")
    conn = MagicMock()

    with (
        patch.object(sfp, "get_debt_row", return_value=None),
        patch.object(sfp, "emit_alert"),
        patch.object(sfp, "upsert_debt_row") as mock_debt,
    ):
        sfp.process_miss(miss, conn, dry_run=True)

    mock_debt.assert_not_called()


# ── Auto-recovery — process_healthy ─────────────────────────────────────────


# ACCEPTANCE TEST 5 — healthy service with pending debt → flips to resolved.
def test_process_healthy_resolves_pending_debt():
    conn = MagicMock()
    with (
        patch.object(sfp, "get_debt_row", return_value={"status": "pending"}),
        patch.object(sfp, "upsert_debt_row") as mock_debt,
    ):
        sfp.process_healthy("svc", conn, dry_run=False)

    mock_debt.assert_called_once_with("svc", status="resolved", reason="auto-recovered")


def test_process_healthy_no_existing_debt_is_noop():
    conn = MagicMock()
    with (
        patch.object(sfp, "get_debt_row", return_value=None),
        patch.object(sfp, "upsert_debt_row") as mock_debt,
    ):
        sfp.process_healthy("svc", conn, dry_run=False)

    mock_debt.assert_not_called()


def test_process_healthy_already_resolved_is_noop():
    conn = MagicMock()
    with (
        patch.object(sfp, "get_debt_row", return_value={"status": "resolved"}),
        patch.object(sfp, "upsert_debt_row") as mock_debt,
    ):
        sfp.process_healthy("svc", conn, dry_run=False)

    mock_debt.assert_not_called()


# ── Registry loading ─────────────────────────────────────────────────────────


def test_load_registry_parses_all_required_fields(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        """
services:
  - name: test-svc
    check: systemd
    criticality: P0
    description: "a test service"
  - name: test-timer
    check: timer
    timer_window_hours: 2.0
    criticality: P1
    description: "a test timer"
"""
    )
    entries = sfp.load_registry(reg)
    assert len(entries) == 2
    assert entries[0].name == "test-svc"
    assert entries[0].check == "systemd"
    assert entries[0].criticality == "P0"
    assert entries[1].name == "test-timer"
    assert entries[1].timer_window_hours == 2.0
    assert entries[1].criticality == "P1"


def test_load_registry_defaults_applied(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(
        """
services:
  - name: minimal
    check: heartbeat
    criticality: P1
    description: "minimal entry"
"""
    )
    entries = sfp.load_registry(reg)
    assert entries[0].stale_minutes == 10
    assert entries[0].timer_window_hours == 1.0


def test_load_production_registry_has_all_anchor_services():
    """The production registry must include both anchor-incident services."""
    entries = sfp.load_registry(sfp.REGISTRY_PATH)
    names = {e.name for e in entries}
    # keiracom-temporal-worker: dual-publish was dead 5 days
    assert "keiracom-temporal-worker" in names, "anchor service keiracom-temporal-worker missing"
    # migration-apply-watcher: schema gate failed silently
    assert "migration-apply-watcher" in names, "anchor service migration-apply-watcher missing"


def test_load_production_registry_all_p0_are_inbox_or_nats_or_core():
    """P0 services in the registry should be the expected critical categories."""
    entries = sfp.load_registry(sfp.REGISTRY_PATH)
    p0_names = {e.name for e in entries if e.criticality == "P0"}
    # All inbox-watchers must be P0
    inbox_watchers = {
        "aiden-inbox-watcher",
        "atlas-inbox-watcher",
        "elliot-inbox-watcher",
        "max-inbox-watcher",
        "orion-inbox-watcher",
        "scout-inbox-watcher",
    }
    missing_p0 = inbox_watchers - p0_names
    assert not missing_p0, f"Inbox watchers missing from P0: {missing_p0}"


# ── query_timer_last_trigger parsing ────────────────────────────────────────


def test_query_timer_last_trigger_parses_valid_output():
    """Parsing logic extracted via monkeypatch — no real systemctl needed."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="Thu 2026-05-29 03:30:01 UTC\n", returncode=0)
        result = sfp.query_timer_last_trigger("weaviate-backup")

    assert result is not None
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 29
    assert result.tzinfo == _dt.UTC


def test_query_timer_last_trigger_empty_returns_none():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="\n", returncode=0)
        result = sfp.query_timer_last_trigger("migration-apply-watcher")
    assert result is None
