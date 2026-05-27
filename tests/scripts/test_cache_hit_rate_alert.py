"""Unit tests for scripts/cache_hit_rate_alert.py (Agency_OS-if0r).

Covers the pure surface (no Supabase):
- format_breach_summary handles empty + populated rows
- write_alerts emits one structured row per breach

query_breaches is a thin psycopg wrapper; covered by an integration probe in
a separate suite that points at a real DB.

bd: Agency_OS-if0r
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

_mod = importlib.import_module("cache_hit_rate_alert")


def test_format_breach_summary_empty_returns_no_callsigns_message():
    out = _mod.format_breach_summary([], 80.0)
    assert out == "No callsigns below 80% threshold."


def test_format_breach_summary_lists_each_row():
    breaches = [
        {
            "rollup_date": "2026-05-27",
            "callsign": "scout",
            "hit_rate_percent": 75.5,
            "spawn_count": 3,
            "cache_read_tokens": 1000,
            "cache_creation_tokens": 500,
            "input_tokens": 324,
            "output_tokens": 50,
            "assistant_message_count": 10,
        },
        {
            "rollup_date": "2026-05-27",
            "callsign": "atlas",
            "hit_rate_percent": 60.0,
            "spawn_count": 2,
            "cache_read_tokens": 600,
            "cache_creation_tokens": 100,
            "input_tokens": 400,
            "output_tokens": 30,
            "assistant_message_count": 5,
        },
    ]
    out = _mod.format_breach_summary(breaches, 80.0)
    assert "2 (date, callsign) breaches of 80% threshold" in out
    assert "scout" in out
    assert "atlas" in out
    assert "75.50%" in out
    assert "60.00%" in out


def test_write_alerts_emits_one_line_per_breach(tmp_path):
    breaches = [
        {
            "rollup_date": "2026-05-27",
            "callsign": "scout",
            "hit_rate_percent": 75.5,
            "spawn_count": 3,
            "cache_read_tokens": 1000,
            "cache_creation_tokens": 500,
            "input_tokens": 324,
            "output_tokens": 50,
            "assistant_message_count": 10,
        }
    ]
    log_path = tmp_path / "alerts.jsonl"
    _mod.write_alerts(breaches, 80.0, log_path)
    line = log_path.read_text().strip()
    row = json.loads(line)
    assert row["severity"] == "warning"
    assert row["kei"] == "Agency_OS-if0r"
    assert row["callsign"] == "scout"
    assert row["hit_rate_percent"] == 75.5
    assert row["threshold_percent"] == 80.0
    assert "cache hit-rate below 80%" in row["title"]
    assert "scout" in row["title"]
    assert "2026-05-27" in row["title"]
    assert row["spawn_count"] == 3


def test_write_alerts_creates_parent_dir_if_missing(tmp_path):
    log_path = tmp_path / "subdir" / "deeper" / "alerts.jsonl"
    _mod.write_alerts(
        [
            {
                "rollup_date": "2026-05-27",
                "callsign": "x",
                "hit_rate_percent": 0.0,
                "spawn_count": 0,
                "cache_read_tokens": 0,
                "cache_creation_tokens": 0,
                "input_tokens": 1,
                "output_tokens": 0,
                "assistant_message_count": 1,
            }
        ],
        80.0,
        log_path,
    )
    assert log_path.exists()


def test_write_alerts_appends_does_not_truncate(tmp_path):
    log_path = tmp_path / "alerts.jsonl"
    base = {
        "rollup_date": "2026-05-27",
        "callsign": "scout",
        "spawn_count": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
        "input_tokens": 1,
        "output_tokens": 0,
        "assistant_message_count": 1,
    }
    _mod.write_alerts([{**base, "hit_rate_percent": 70.0}], 80.0, log_path)
    _mod.write_alerts([{**base, "hit_rate_percent": 65.0}], 80.0, log_path)
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_dsn_returns_none_when_env_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert _mod._dsn() is None


def test_dsn_strips_asyncpg_dialect_prefix(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@host:5432/db")
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert _mod._dsn() == "postgresql://user:pass@host:5432/db"
