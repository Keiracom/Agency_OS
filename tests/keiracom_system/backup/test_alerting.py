"""Tests for backup-failure ceo_memory alerting."""

from __future__ import annotations

from datetime import UTC, datetime

from src.keiracom_system.backup import alerting

FIXED = datetime(2026, 6, 1, 9, 30, tzinfo=UTC)


def _recorder():
    calls: list[tuple] = []

    def writer(callsign, key, value):
        calls.append((callsign, key, value))

    return writer, calls


def test_alert_key_and_payload():
    writer, calls = _recorder()
    key = alerting.write_backup_alert("weaviate_snapshot", "tar failed", writer=writer, now=FIXED)
    assert key == "ceo:backup_alert:2026-06-01"
    assert len(calls) == 1
    callsign, written_key, value = calls[0]
    assert callsign == "elliot"  # KEI-87 write-guard allowlist
    assert written_key == key
    assert value["component"] == "weaviate_snapshot"
    assert value["error"] == "tar failed"
    assert value["severity"] == "P1"
    assert value["source"] == "keiracom_system.backup"


def test_alert_truncates_long_error():
    writer, calls = _recorder()
    alerting.write_backup_alert("pg", "x" * 5000, writer=writer, now=FIXED)
    assert len(calls[0][2]["error"]) == 1000


def test_alert_write_failure_returns_none_not_raises():
    def boom(callsign, key, value):
        raise ConnectionError("db down")

    # Must not raise — alerting reports failures, it must not add one.
    assert alerting.write_backup_alert("pg", "err", writer=boom, now=FIXED) is None
