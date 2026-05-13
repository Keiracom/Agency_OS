"""Unit tests for scripts/idle_enforcer.py (KEI-45 Layer 3 idle daemon)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from scripts import idle_enforcer

# Weekly-cap detection ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "expected_hit", "expected_resets_substr"),
    [
        (
            "You've used 92% of your weekly limit · resets 2026-05-20",
            True,
            "2026-05-20",
        ),
        (
            "You've used 100% of your weekly limit. Resets Friday at 10am UTC",
            True,
            "Friday",
        ),
        (
            # Loosely-formatted but still parseable (em-dash + lowercase 'resets').
            "you've used 80% of your weekly limit - resets 2026-06-01",
            True,
            "2026-06-01",
        ),
        ("Server is temporarily limiting requests. retry-after: 60", False, None),
        ("HTTP 429 Too Many Requests", False, None),
        ("normal pane output, nothing rate-limit-shaped", False, None),
    ],
)
def test_weekly_cap_detection(
    text: str, expected_hit: bool, expected_resets_substr: str | None
) -> None:
    hit, resets = idle_enforcer.detect_weekly_cap(text)
    assert hit is expected_hit
    if expected_resets_substr is not None:
        assert resets is not None
        assert expected_resets_substr in resets


# BUSY guard ────────────────────────────────────────────────────────────────


def test_busy_guard_matches_own_callsign() -> None:
    pane = "some chatter\n[BUSY:atlas:KEI-45] running\nmore output"
    assert idle_enforcer.detect_busy(pane, "atlas") is True


def test_busy_guard_skips_other_callsign() -> None:
    pane = "[BUSY:aiden:KEI-22] doing things"
    assert idle_enforcer.detect_busy(pane, "atlas") is False


def test_busy_guard_no_match_on_empty() -> None:
    assert idle_enforcer.detect_busy("", "atlas") is False


# Idle minutes from HEARTBEAT mtime ─────────────────────────────────────────


def test_compute_idle_minutes_uses_heartbeat_mtime(tmp_path: Path) -> None:
    fake_worktree = tmp_path / "Agency_OS-fake"
    fake_worktree.mkdir()
    hb = fake_worktree / "HEARTBEAT.md"
    hb.write_text("# HEARTBEAT.md\n")
    now = datetime.now(UTC)
    old_mtime = (now - timedelta(minutes=42)).timestamp()
    import os

    os.utime(hb, (old_mtime, old_mtime))

    with mock.patch.dict(idle_enforcer.CALLSIGN_TO_WORKTREE, {"fake": str(fake_worktree)}):
        idle, last = idle_enforcer._compute_idle_minutes("fake", now)

    assert 41 <= idle <= 43, f"expected ~42 min idle, got {idle}"
    assert last.startswith(now.strftime("%Y-%m-%dT")[:8]) or "T" in last


def test_compute_idle_minutes_returns_zero_when_heartbeat_missing(
    tmp_path: Path,
) -> None:
    with mock.patch.dict(idle_enforcer.CALLSIGN_TO_WORKTREE, {"missing": str(tmp_path)}):
        idle, _ = idle_enforcer._compute_idle_minutes("missing", datetime.now(UTC))
    assert idle == 0


# inject_dispatch — verify it issues the right tmux command shape ──────────


def test_inject_dispatch_calls_send_keys_when_session_alive() -> None:
    calls: list[list[str]] = []

    def fake_run(cmd, *_a, **_kw):  # type: ignore[no-untyped-def]
        calls.append(list(cmd))
        # has-session returncode=0 (alive); send-keys ignored.
        result = mock.Mock()
        result.returncode = 0
        return result

    with mock.patch("scripts.idle_enforcer.subprocess.run", side_effect=fake_run):
        ok = idle_enforcer.inject_dispatch("atlas", "[ENFORCER] pick up KEI-99")
    assert ok is True
    # First call: has-session check.
    assert calls[0][:2] == ["tmux", "has-session"]
    # Subsequent calls: send-keys with brief, then Enter.
    send_calls = [c for c in calls if c[:2] == ["tmux", "send-keys"]]
    assert any("[ENFORCER]" in " ".join(c) for c in send_calls)
    assert any(c[-1] == "Enter" for c in send_calls)


def test_inject_dispatch_aborts_when_session_dead() -> None:
    def fake_run(_cmd, *_a, **_kw):  # type: ignore[no-untyped-def]
        result = mock.Mock()
        result.returncode = 1  # has-session: not found
        return result

    with mock.patch("scripts.idle_enforcer.subprocess.run", side_effect=fake_run):
        assert idle_enforcer.inject_dispatch("atlas", "x") is False


# bd_ready_for — JSON parsing happy + sad paths ─────────────────────────────


def test_bd_ready_for_parses_json_array() -> None:
    proc = mock.Mock()
    proc.returncode = 0
    proc.stdout = json.dumps([{"id": "Agency_OS-abc", "title": "do thing"}])
    with mock.patch("scripts.idle_enforcer.subprocess.run", return_value=proc):
        out = idle_enforcer.bd_ready_for("atlas")
    assert out == [{"id": "Agency_OS-abc", "title": "do thing"}]


def test_bd_ready_for_returns_empty_on_bad_json() -> None:
    proc = mock.Mock()
    proc.returncode = 0
    proc.stdout = "not-json"
    with mock.patch("scripts.idle_enforcer.subprocess.run", return_value=proc):
        assert idle_enforcer.bd_ready_for("atlas") == []


def test_bd_ready_for_returns_empty_on_nonzero_exit() -> None:
    proc = mock.Mock()
    proc.returncode = 2
    proc.stdout = ""
    with mock.patch("scripts.idle_enforcer.subprocess.run", return_value=proc):
        assert idle_enforcer.bd_ready_for("atlas") == []


# process_callsign — wiring through the layers ──────────────────────────────


def test_process_callsign_skips_dispatch_when_weekly_cap_active() -> None:
    pane = "You've used 95% of your weekly limit · resets 2026-05-20"
    now = datetime.now(UTC)
    with (
        mock.patch("scripts.idle_enforcer._capture_pane_tail", return_value=pane),
        mock.patch(
            "scripts.idle_enforcer._compute_idle_minutes", return_value=(99, now.isoformat())
        ),
        mock.patch("scripts.idle_enforcer.bd_ready_for") as bd_mock,
        mock.patch("scripts.idle_enforcer.inject_dispatch") as inj_mock,
        mock.patch("scripts.idle_enforcer.post_ceo") as ceo_mock,
    ):
        state = idle_enforcer.process_callsign("atlas", now)
    # Weekly cap → no bd ready, no injection.
    bd_mock.assert_not_called()
    inj_mock.assert_not_called()
    # First weekly hit posts to #ceo (dedup map empty).
    ceo_mock.assert_called_once()
    assert state.rate_limit_state.startswith("weekly_cap_until=")


def test_process_callsign_skips_when_busy() -> None:
    pane = "[BUSY:atlas:KEI-45] running tests"
    now = datetime.now(UTC)
    with (
        mock.patch("scripts.idle_enforcer._capture_pane_tail", return_value=pane),
        mock.patch(
            "scripts.idle_enforcer._compute_idle_minutes", return_value=(20, now.isoformat())
        ),
        mock.patch("scripts.idle_enforcer.bd_ready_for") as bd_mock,
        mock.patch("scripts.idle_enforcer.inject_dispatch") as inj_mock,
    ):
        state = idle_enforcer.process_callsign("atlas", now)
    bd_mock.assert_not_called()
    inj_mock.assert_not_called()
    assert state.idle_minutes == 0  # BUSY counts as activity


def test_process_callsign_injects_when_idle_with_work() -> None:
    now = datetime.now(UTC)
    work_item = {"id": "Agency_OS-test", "title": "do the thing"}
    with (
        mock.patch("scripts.idle_enforcer._capture_pane_tail", return_value="ok"),
        mock.patch(
            "scripts.idle_enforcer._compute_idle_minutes", return_value=(15, now.isoformat())
        ),
        mock.patch("scripts.idle_enforcer.bd_ready_for", return_value=[work_item]),
        mock.patch("scripts.idle_enforcer.inject_dispatch", return_value=True) as inj_mock,
        mock.patch("scripts.idle_enforcer.post_ceo"),
    ):
        state = idle_enforcer.process_callsign("atlas", now)
    inj_mock.assert_called_once()
    args, _ = inj_mock.call_args
    assert args[0] == "atlas"
    assert "Agency_OS-test" in args[1]
    assert state.last_dispatch_at is not None
    assert state.work_available_count == 1


def test_process_callsign_no_inject_under_threshold() -> None:
    now = datetime.now(UTC)
    with (
        mock.patch("scripts.idle_enforcer._capture_pane_tail", return_value=""),
        mock.patch(
            "scripts.idle_enforcer._compute_idle_minutes", return_value=(5, now.isoformat())
        ),
        mock.patch(
            "scripts.idle_enforcer.bd_ready_for",
            return_value=[{"id": "x", "title": "y"}],
        ),
        mock.patch("scripts.idle_enforcer.inject_dispatch") as inj_mock,
    ):
        state = idle_enforcer.process_callsign("atlas", now)
    inj_mock.assert_not_called()
    assert state.last_dispatch_at is None


def test_escalation_fires_at_30_minutes_with_work() -> None:
    now = datetime.now(UTC)
    idle_enforcer._last_escalation_at.clear()  # reset dedup map
    with (
        mock.patch("scripts.idle_enforcer._capture_pane_tail", return_value=""),
        mock.patch(
            "scripts.idle_enforcer._compute_idle_minutes",
            return_value=(35, now.isoformat()),
        ),
        mock.patch(
            "scripts.idle_enforcer.bd_ready_for",
            return_value=[{"id": "x", "title": "y"}],
        ),
        mock.patch("scripts.idle_enforcer.inject_dispatch", return_value=True),
        mock.patch("scripts.idle_enforcer.post_ceo") as ceo_mock,
    ):
        idle_enforcer.process_callsign("atlas", now)
    ceo_mock.assert_called_once()


def test_escalation_deduped_within_window() -> None:
    now = datetime.now(UTC)
    idle_enforcer._last_escalation_at.clear()
    # Prime the dedup map.
    idle_enforcer._last_escalation_at["idle:atlas"] = now - timedelta(minutes=10)
    with (
        mock.patch("scripts.idle_enforcer._capture_pane_tail", return_value=""),
        mock.patch(
            "scripts.idle_enforcer._compute_idle_minutes",
            return_value=(35, now.isoformat()),
        ),
        mock.patch(
            "scripts.idle_enforcer.bd_ready_for",
            return_value=[{"id": "x", "title": "y"}],
        ),
        mock.patch("scripts.idle_enforcer.inject_dispatch", return_value=True),
        mock.patch("scripts.idle_enforcer.post_ceo") as ceo_mock,
    ):
        idle_enforcer.process_callsign("atlas", now)
    ceo_mock.assert_not_called()
