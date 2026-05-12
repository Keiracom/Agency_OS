"""Tests for scripts/alerts/hook_failure_monitor.py — KEI-11 Outcome 3.

Mocks filesystem (via tmp_path watched_dirs) + Slack POST. No network. Covers:
  - .err files with new bytes (in 5-min window) trigger alert
  - .log files trigger only when new content matches ERROR pattern
  - Files not modified in the last 5 min are ignored
  - Per-log-file dedupe within 5-min window
  - Slack post failure: state advances bytes_seen but NOT last_alerted_iso
  - Empty watched dir + corrupt state file are non-fatal
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "alerts" / "hook_failure_monitor.py"
_spec = importlib.util.spec_from_file_location("hook_failure_monitor", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["hook_failure_monitor"] = mod
_spec.loader.exec_module(mod)


NOW = datetime(2026, 5, 12, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def watched_dir(tmp_path: Path) -> Path:
    d = tmp_path / "agency-os-session-store"
    d.mkdir()
    return d


@pytest.fixture
def state_path(tmp_path: Path) -> Path:
    return tmp_path / "state.json"


@pytest.fixture
def post_calls():
    calls: list[str] = []

    def fake_post(text: str, channel: str = mod.EXECUTION_CHANNEL) -> bool:
        calls.append(text)
        return True

    fake_post.calls = calls  # type: ignore[attr-defined]
    return fake_post


def _write_with_mtime(path: Path, content: str, *, mtime: datetime) -> None:
    path.write_text(content)
    ts = mtime.timestamp()
    os.utime(path, (ts, ts))


# ─── 1. .err file with new content within window triggers alert ────────


def test_err_file_new_content_within_window_triggers_alert(
    watched_dir: Path, state_path: Path, post_calls
):
    err = watched_dir / "recorder.err"
    _write_with_mtime(err, "session close failed: schema mismatch\n", mtime=NOW)

    summary = mod.run_once(
        state_path,
        watched_dirs=(watched_dir,),
        post_fn=post_calls,
        now=NOW,
    )
    assert summary["findings"] == 1
    assert summary["alerted"] == 1
    assert len(post_calls.calls) == 1
    assert "recorder.err" in post_calls.calls[0]
    assert "schema mismatch" in post_calls.calls[0]


# ─── 2. .log file with new ERROR-ish lines triggers; clean .log does not ─


def test_log_file_with_error_pattern_triggers(watched_dir: Path, state_path: Path, post_calls):
    log = watched_dir / "posttooluse.log"
    _write_with_mtime(
        log,
        "2026-05-12T12:00:00Z\torion\trecording_started\n"
        "2026-05-12T12:00:01Z\torion\tERROR something blew up\n",
        mtime=NOW,
    )
    summary = mod.run_once(
        state_path,
        watched_dirs=(watched_dir,),
        post_fn=post_calls,
        now=NOW,
    )
    assert summary["alerted"] == 1
    assert "ERROR something blew up" in post_calls.calls[0]


def test_log_file_with_only_normal_lines_does_not_alert(
    watched_dir: Path, state_path: Path, post_calls
):
    log = watched_dir / "posttooluse.log"
    _write_with_mtime(
        log,
        "2026-05-12T12:00:00Z\torion\trecording_started\n"
        "2026-05-12T12:00:01Z\torion\trecording_completed\n",
        mtime=NOW,
    )
    summary = mod.run_once(
        state_path,
        watched_dirs=(watched_dir,),
        post_fn=post_calls,
        now=NOW,
    )
    assert summary["alerted"] == 0
    assert post_calls.calls == []


# ─── 3. Files not modified in last 5 min are ignored ───────────────────


def test_file_older_than_window_is_ignored(watched_dir: Path, state_path: Path, post_calls):
    err = watched_dir / "recorder.err"
    _write_with_mtime(
        err,
        "old failure from yesterday\n",
        mtime=NOW - timedelta(hours=1),
    )
    summary = mod.run_once(
        state_path,
        watched_dirs=(watched_dir,),
        post_fn=post_calls,
        now=NOW,
    )
    assert summary["findings"] == 0
    assert summary["alerted"] == 0


# ─── 4. Per-log-file dedupe within 5-min window ────────────────────────


def test_dedupes_per_log_file_within_window(watched_dir: Path, state_path: Path, post_calls):
    err = watched_dir / "recorder.err"
    _write_with_mtime(err, "first failure\n", mtime=NOW)
    s1 = mod.run_once(state_path, watched_dirs=(watched_dir,), post_fn=post_calls, now=NOW)
    assert s1["alerted"] == 1

    # Another failure 2 min later — same file, within dedupe window.
    later = NOW + timedelta(minutes=2)
    _write_with_mtime(err, "first failure\nsecond failure 2 min in\n", mtime=later)
    s2 = mod.run_once(state_path, watched_dirs=(watched_dir,), post_fn=post_calls, now=later)
    assert s2["findings"] == 1  # detected new bytes
    assert s2["alerted"] == 0  # but suppressed by dedupe
    assert len(post_calls.calls) == 1

    # 6 min after first alert — window cleared, re-alerts.
    much_later = NOW + timedelta(minutes=6)
    _write_with_mtime(
        err,
        "first failure\nsecond failure 2 min in\nthird failure 6 min in\n",
        mtime=much_later,
    )
    s3 = mod.run_once(state_path, watched_dirs=(watched_dir,), post_fn=post_calls, now=much_later)
    assert s3["alerted"] == 1
    assert len(post_calls.calls) == 2


# ─── 5. Slack post failure keeps last_alerted_iso unset, but advances bytes ─


def test_slack_failure_advances_bytes_but_not_last_alerted(watched_dir: Path, state_path: Path):
    err = watched_dir / "recorder.err"
    _write_with_mtime(err, "first failure\n", mtime=NOW)

    def failing_post(*_a, **_kw) -> bool:
        return False

    s = mod.run_once(
        state_path,
        watched_dirs=(watched_dir,),
        post_fn=failing_post,
        now=NOW,
    )
    assert s["findings"] == 1
    assert s["alerted"] == 0

    state = json.loads(state_path.read_text())
    entry = state[str(err)]
    # bytes_seen advances so we don't re-scan the same lines.
    assert entry["bytes_seen"] > 0
    # last_alerted_iso NOT set — so next sweep with new bytes will alert again.
    assert "last_alerted_iso" not in entry


# ─── 6. Empty watched dir is non-fatal ─────────────────────────────────


def test_empty_or_missing_watched_dir_is_non_fatal(state_path: Path, post_calls):
    missing = Path("/tmp/agency-os-nonexistent-test-dir-12345")
    s = mod.run_once(state_path, watched_dirs=(missing,), post_fn=post_calls, now=NOW)
    assert s == {"dirs_scanned": 1, "findings": 0, "alerted": 0}
    assert post_calls.calls == []


# ─── 7. Corrupt state file → treated as empty ──────────────────────────


def test_corrupt_state_file_treated_as_empty(watched_dir: Path, state_path: Path, post_calls):
    state_path.write_text("{ not valid json")
    err = watched_dir / "recorder.err"
    _write_with_mtime(err, "boom\n", mtime=NOW)
    s = mod.run_once(state_path, watched_dirs=(watched_dir,), post_fn=post_calls, now=NOW)
    assert s["alerted"] == 1


# ─── 8. Multiple findings → one aggregated alert ───────────────────────


def test_multiple_findings_one_aggregated_alert(watched_dir: Path, state_path: Path, post_calls):
    _write_with_mtime(watched_dir / "stop.err", "stop failed\n", mtime=NOW)
    _write_with_mtime(watched_dir / "posttooluse.log", "ERROR boom\n", mtime=NOW)
    s = mod.run_once(state_path, watched_dirs=(watched_dir,), post_fn=post_calls, now=NOW)
    assert s["findings"] == 2
    assert s["alerted"] == 2
    assert len(post_calls.calls) == 1
    assert "stop.err" in post_calls.calls[0]
    assert "posttooluse.log" in post_calls.calls[0]
