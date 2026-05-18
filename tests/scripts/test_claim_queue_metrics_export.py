"""Tests for scripts/orchestrator/claim_queue_metrics_export.py — KEI-136.

Covers:
  - is_stalled() logic for all stall conditions + healthy + NULL fail-open
  - fetch_metrics() shape via mocked psycopg
  - main() heartbeat-skip on stall + heartbeat-post on healthy
  - main() exits clean when CLAIM_QUEUE_HEARTBEAT_URL is unset (fail-open)
  - main() exits clean when DB fetch fails (no fail-loud)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "orchestrator" / "claim_queue_metrics_export.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("claim_queue_metrics_export", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["claim_queue_metrics_export"] = m
    spec.loader.exec_module(m)
    return m


# ─── is_stalled ──────────────────────────────────────────────────────────────


def test_is_stalled_healthy_queue(mod):
    metrics = {
        "available_count": 0,
        "oldest_available_age_sec": None,
        "max_idle_seconds": None,
    }
    stalled, reason = mod.is_stalled(metrics, 300)
    assert stalled is False
    assert reason == ""


def test_is_stalled_available_aging_past_threshold(mod):
    metrics = {
        "available_count": 3,
        "oldest_available_age_sec": 600,
        "max_idle_seconds": None,
    }
    stalled, reason = mod.is_stalled(metrics, 300)
    assert stalled is True
    assert "available work aging" in reason


def test_is_stalled_available_under_threshold(mod):
    metrics = {
        "available_count": 5,
        "oldest_available_age_sec": 100,
        "max_idle_seconds": None,
    }
    stalled, _ = mod.is_stalled(metrics, 300)
    assert stalled is False


def test_is_stalled_no_available_rows_ignored(mod):
    """available_count=0 means nothing to wait for — even if oldest_available_age
    is somehow non-null (shouldn't be), it must NOT stall."""
    metrics = {
        "available_count": 0,
        "oldest_available_age_sec": 999999,
        "max_idle_seconds": None,
    }
    stalled, _ = mod.is_stalled(metrics, 300)
    assert stalled is False


def test_is_stalled_max_idle_past_threshold(mod):
    metrics = {
        "available_count": 0,
        "oldest_available_age_sec": None,
        "max_idle_seconds": 900,
    }
    stalled, reason = mod.is_stalled(metrics, 300)
    assert stalled is True
    assert "idle past SLA" in reason


def test_is_stalled_max_idle_null_is_failopen(mod):
    """NULL max_idle_seconds (no heartbeat data on any active row) must NOT
    be treated as stall — tasks.heartbeat_at is unpopulated in production."""
    metrics = {
        "available_count": 0,
        "oldest_available_age_sec": None,
        "max_idle_seconds": None,
    }
    stalled, _ = mod.is_stalled(metrics, 300)
    assert stalled is False


# ─── fetch_metrics ───────────────────────────────────────────────────────────


def test_fetch_metrics_returns_named_dict(mod, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    cur = MagicMock()
    cur.fetchone.return_value = (5, 2, 1, 600, 120, None)
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)

    with patch("psycopg.connect", return_value=conn_ctx):
        result = mod.fetch_metrics()

    assert result == {
        "available_count": 5,
        "active_count": 2,
        "blocked_count": 1,
        "oldest_available_age_sec": 600,
        "oldest_active_age_sec": 120,
        "max_idle_seconds": None,
    }


def test_fetch_metrics_empty_view_returns_empty_dict(mod, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    cur = MagicMock()
    cur.fetchone.return_value = None
    cur_ctx = MagicMock()
    cur_ctx.__enter__ = MagicMock(return_value=cur)
    cur_ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur_ctx
    conn_ctx = MagicMock()
    conn_ctx.__enter__ = MagicMock(return_value=conn)
    conn_ctx.__exit__ = MagicMock(return_value=False)
    with patch("psycopg.connect", return_value=conn_ctx):
        assert mod.fetch_metrics() == {}


# ─── main entry ──────────────────────────────────────────────────────────────


def test_main_exits_clean_when_heartbeat_url_unset(mod, monkeypatch, caplog):
    """No CLAIM_QUEUE_HEARTBEAT_URL = exporter logs warning + returns 0.
    Critical: must not error out — runbook says heartbeat URL is set AFTER install."""
    monkeypatch.delenv("CLAIM_QUEUE_HEARTBEAT_URL", raising=False)
    rc = mod.main()
    assert rc is None


def test_main_posts_heartbeat_on_healthy_queue(mod, monkeypatch):
    monkeypatch.setenv(
        "CLAIM_QUEUE_HEARTBEAT_URL", "https://uptime.betterstack.com/api/v1/heartbeat/TOKEN"
    )
    healthy = {
        "available_count": 0,
        "active_count": 1,
        "blocked_count": 0,
        "oldest_available_age_sec": None,
        "oldest_active_age_sec": 60,
        "max_idle_seconds": None,
    }
    with (
        patch.object(mod, "fetch_metrics", return_value=healthy),
        patch.object(mod, "post_heartbeat", return_value=True) as ph,
    ):
        rc = mod.main()
    assert rc is None
    ph.assert_called_once_with("https://uptime.betterstack.com/api/v1/heartbeat/TOKEN")


def test_main_skips_heartbeat_on_stalled_queue(mod, monkeypatch, caplog):
    monkeypatch.setenv(
        "CLAIM_QUEUE_HEARTBEAT_URL", "https://uptime.betterstack.com/api/v1/heartbeat/TOKEN"
    )
    stalled = {
        "available_count": 3,
        "active_count": 0,
        "blocked_count": 0,
        "oldest_available_age_sec": 600,
        "oldest_active_age_sec": None,
        "max_idle_seconds": None,
    }
    with (
        patch.object(mod, "fetch_metrics", return_value=stalled),
        patch.object(mod, "post_heartbeat") as ph,
    ):
        rc = mod.main()
    assert rc is None
    ph.assert_not_called()  # BS alert fires via missed heartbeat


def test_main_exits_clean_when_db_unreachable(mod, monkeypatch):
    """fetch_metrics raising → exporter logs + returns 0 (no fail-loud, no
    cascade kill of subsequent timer fires)."""
    monkeypatch.setenv("CLAIM_QUEUE_HEARTBEAT_URL", "https://example.com/hb")
    with patch.object(mod, "fetch_metrics", side_effect=OSError("connection refused")):
        rc = mod.main()
    assert rc is None


def test_main_threshold_override_via_env(mod, monkeypatch):
    """Operator can override the 300s stall threshold via env."""
    monkeypatch.setenv("CLAIM_QUEUE_HEARTBEAT_URL", "https://example.com/hb")
    monkeypatch.setenv("CLAIM_QUEUE_STALL_THRESHOLD_SEC", "60")
    metrics = {
        "available_count": 1,
        "oldest_available_age_sec": 120,  # >60 → stall, but <300 default
        "max_idle_seconds": None,
    }
    with (
        patch.object(mod, "fetch_metrics", return_value=metrics),
        patch.object(mod, "post_heartbeat") as ph,
    ):
        rc = mod.main()
    assert rc is None
    ph.assert_not_called()
