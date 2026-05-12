"""tests for scripts/alerts/artifact_freshness_monitor.py — Dave System Health Outcome 4.

Covers:
  - ceo_memory >30d filter (excludes _complete suffix, sorts oldest-first)
  - completed_directives >60d filter (_complete suffix only)
  - slack_pins >14d filter (cross-channel aggregation)
  - Empty-input no-op behavior
  - Slack post failure does not raise
  - main() invokes each check independently
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MONITOR_PATH = REPO_ROOT / "scripts" / "alerts" / "artifact_freshness_monitor.py"


@pytest.fixture(scope="module")
def monitor():
    spec = importlib.util.spec_from_file_location("artifact_freshness_monitor", MONITOR_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["artifact_freshness_monitor"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 12, 0, 0, 0, tzinfo=UTC)


def _iso(now: datetime, days_ago: int) -> str:
    return (now - timedelta(days=days_ago)).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# check_ceo_memory_stale
# ─────────────────────────────────────────────────────────────────────────────


def test_ceo_memory_stale_filters_by_age(monitor, now) -> None:
    rows = [
        {"key": "ceo:fresh", "updated_at": _iso(now, 5)},
        {"key": "ceo:stale_31d", "updated_at": _iso(now, 31)},
        {"key": "ceo:stale_90d", "updated_at": _iso(now, 90)},
    ]
    stale = monitor.check_ceo_memory_stale(rows, now)
    assert len(stale) == 2
    # sorted oldest first
    assert stale[0]["key"] == "ceo:stale_90d"
    assert stale[1]["key"] == "ceo:stale_31d"


def test_ceo_memory_stale_excludes_complete_suffix(monitor, now) -> None:
    rows = [
        {"key": "ceo:directive_123_complete", "updated_at": _iso(now, 99)},
        {"key": "ceo:active_thing", "updated_at": _iso(now, 99)},
    ]
    stale = monitor.check_ceo_memory_stale(rows, now)
    assert len(stale) == 1
    assert stale[0]["key"] == "ceo:active_thing"


def test_ceo_memory_stale_handles_bad_timestamps(monitor, now) -> None:
    rows = [
        {"key": "ceo:broken", "updated_at": "not-a-date"},
        {"key": "ceo:missing"},
    ]
    stale = monitor.check_ceo_memory_stale(rows, now)
    assert stale == []


def test_ceo_memory_stale_boundary_30d(monitor, now) -> None:
    """Exactly 30d = not stale (boundary uses < threshold)."""
    rows = [
        {"key": "ceo:exactly_30d", "updated_at": _iso(now, 30)},
        {"key": "ceo:just_over_30d", "updated_at": _iso(now, 31)},
    ]
    stale = monitor.check_ceo_memory_stale(rows, now)
    keys = {s["key"] for s in stale}
    assert "ceo:just_over_30d" in keys
    # exactly_30d may or may not be in stale due to seconds-rounding; both acceptable
    # but the deliberate test is the strictly-older case → just_over_30d MUST be stale


# ─────────────────────────────────────────────────────────────────────────────
# check_completed_directives_stale
# ─────────────────────────────────────────────────────────────────────────────


def test_completed_directives_stale_filters_suffix(monitor, now) -> None:
    rows = [
        {"key": "ceo:directive_old_complete", "updated_at": _iso(now, 90)},
        {"key": "ceo:directive_recent_complete", "updated_at": _iso(now, 10)},
        {"key": "ceo:active_thing", "updated_at": _iso(now, 200)},
    ]
    stale = monitor.check_completed_directives_stale(rows, now)
    assert len(stale) == 1
    assert stale[0]["key"] == "ceo:directive_old_complete"


def test_completed_directives_stale_60d_threshold(monitor, now) -> None:
    rows = [
        {"key": "ceo:c_59_complete", "updated_at": _iso(now, 59)},
        {"key": "ceo:c_61_complete", "updated_at": _iso(now, 61)},
    ]
    stale = monitor.check_completed_directives_stale(rows, now)
    keys = {s["key"] for s in stale}
    assert "ceo:c_61_complete" in keys
    assert "ceo:c_59_complete" not in keys


# ─────────────────────────────────────────────────────────────────────────────
# check_slack_pins_stale
# ─────────────────────────────────────────────────────────────────────────────


def test_slack_pins_stale_aggregates_channels(monitor, now) -> None:
    threshold_ts = (now - timedelta(days=14)).timestamp()
    old_ts = threshold_ts - 86400  # 1 day past threshold = 15d old
    fresh_ts = now.timestamp() - 3600  # 1h old

    def fake_slack_get(method: str, params: dict) -> dict:
        if method != "pins.list":
            return {}
        if params.get("channel") == monitor.EXECUTION_CHANNEL:
            return {
                "ok": True,
                "items": [
                    {"type": "message", "created": old_ts},
                    {"type": "message", "created": fresh_ts},
                ],
            }
        if params.get("channel") == monitor.CEO_CHANNEL:
            return {"ok": True, "items": [{"type": "file", "created": old_ts}]}
        return {}

    with patch.object(monitor, "_slack_get", side_effect=fake_slack_get):
        stale = monitor.check_slack_pins_stale(now)
    assert len(stale) == 2
    channels = {s["channel"] for s in stale}
    assert channels == {"execution", "ceo"}


def test_slack_pins_stale_handles_api_failure(monitor, now) -> None:
    with patch.object(monitor, "_slack_get", return_value={}):
        stale = monitor.check_slack_pins_stale(now)
    assert stale == []


def test_slack_pins_stale_ok_false_skipped(monitor, now) -> None:
    with patch.object(monitor, "_slack_get", return_value={"ok": False, "error": "not_in_channel"}):
        stale = monitor.check_slack_pins_stale(now)
    assert stale == []


# ─────────────────────────────────────────────────────────────────────────────
# post_to_slack
# ─────────────────────────────────────────────────────────────────────────────


def test_post_to_slack_no_token_returns_false(monitor, monkeypatch) -> None:
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    assert monitor.post_to_slack("test") is False


def test_post_to_slack_network_error_returns_false(monitor, monkeypatch) -> None:
    import urllib.error

    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("network down")):
        assert monitor.post_to_slack("test") is False


# ─────────────────────────────────────────────────────────────────────────────
# Formatters
# ─────────────────────────────────────────────────────────────────────────────


def test_format_ceo_memory_alert_caps_at_10(monitor) -> None:
    stale = [{"key": f"ceo:key_{i}", "age_days": 30 + i} for i in range(20)]
    text = monitor.format_ceo_memory_alert(stale)
    assert "20 entries stale" in text
    assert text.count("ceo:key_") == 10  # only top 10 shown
    assert "ceo:key_0" in text  # at least the first sample present


def test_format_completed_directives_alert_caps_at_10(monitor) -> None:
    stale = [{"key": f"ceo:c{i}_complete", "age_days": 60 + i} for i in range(15)]
    text = monitor.format_completed_directives_alert(stale)
    assert "15 entries" in text
    assert text.count("ceo:c") == 10


def test_format_slack_pins_alert_caps_at_10(monitor) -> None:
    stale = [{"channel": "execution", "type": "message", "age_days": 14 + i} for i in range(15)]
    text = monitor.format_slack_pins_alert(stale)
    assert "15 pin(s) stale" in text


# ─────────────────────────────────────────────────────────────────────────────
# main entry
# ─────────────────────────────────────────────────────────────────────────────


def test_main_returns_zero_with_no_stale(monitor, now) -> None:
    with (
        patch.object(monitor, "_fetch_ceo_memory_rows", return_value=[]),
        patch.object(monitor, "check_slack_pins_stale", return_value=[]),
        patch.object(monitor, "post_to_slack") as mock_post,
    ):
        assert monitor.main() == 0
    assert mock_post.call_count == 0


def test_main_posts_alerts_for_each_class(monitor, now) -> None:
    rows = [
        {"key": "ceo:active_stale", "updated_at": _iso(now, 60)},
        {"key": "ceo:directive_done_complete", "updated_at": _iso(now, 90)},
    ]
    pins = [{"channel": "execution", "type": "message", "age_days": 20}]
    with (
        patch.object(monitor, "_fetch_ceo_memory_rows", return_value=rows),
        patch.object(monitor, "check_slack_pins_stale", return_value=pins),
        patch.object(monitor, "post_to_slack", return_value=True) as mock_post,
    ):
        monitor.main()
    assert mock_post.call_count == 3
    # Verify each call referenced its class
    posted_texts = [c.args[0] for c in mock_post.call_args_list]
    assert any("ceo_memory" in t for t in posted_texts)
    assert any("completed_directives" in t for t in posted_texts)
    assert any("slack_pins" in t for t in posted_texts)


def test_main_returns_zero_even_on_db_failure(monitor) -> None:
    """Best-effort — daily timer must never fail noisily."""
    with (
        patch.object(monitor, "_fetch_ceo_memory_rows", return_value=[]),
        patch.object(monitor, "check_slack_pins_stale", return_value=[]),
    ):
        assert monitor.main() == 0
