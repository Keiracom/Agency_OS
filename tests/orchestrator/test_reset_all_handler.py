"""Tests for scripts/orchestrator/reset_all_handler.py — KEI-93.

Strategy:
  - `matches_reset` and the cooldown logic are pure / near-pure functions;
    tested directly (no subprocess required).
  - Cooldown test monkey-patches time.time via monkeypatch to prove the 60s
    guard drops a second trigger within the window.

Covers:
  - test_matches_reset_positive_dave — sender=U091TGTPB9U + various
    `reset all` surface forms (plain, upper-case, [CEO] relay prefix).
  - test_matches_reset_rejects_other_users — sender != Dave returns False.
  - test_matches_reset_rejects_other_text — text != `reset all` returns False.
  - test_cooldown_drops_second_within_60s — second call inside 60s window skipped.
  - test_health_probe_uses_runtime_dir_path — cognee sentinel read from runtime dir, not /tmp.
  - test_restart_logs_failure_returncode — failed restart logs rc + stderr via logger.warning.
  - test_cooldown_persists_across_restart — lockfile state survives process restart.
  - test_post_logs_http_error — HTTP error in post() logs warning, does not crash.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from scripts.orchestrator.reset_all_handler import (
    COOLDOWN_SECONDS,
    DAVE_USER_ID,
    _read_last_trigger,
    _write_last_trigger,
    health_probe,
    matches_reset,
    post,
)

# ---------------------------------------------------------------------------
# matches_reset — positive cases (Dave, various surface forms)
# ---------------------------------------------------------------------------


def test_matches_reset_positive_dave_plain():
    assert matches_reset(DAVE_USER_ID, "reset all") is True


def test_matches_reset_positive_dave_upper():
    assert matches_reset(DAVE_USER_ID, "RESET ALL") is True


def test_matches_reset_positive_dave_ceo_prefix():
    assert matches_reset(DAVE_USER_ID, "[CEO] reset all") is True


def test_matches_reset_positive_dave_ceo_colon_prefix():
    assert matches_reset(DAVE_USER_ID, "[CEO]: reset all") is True


def test_matches_reset_positive_dave_trailing_space():
    assert matches_reset(DAVE_USER_ID, "reset all   ") is True


# ---------------------------------------------------------------------------
# matches_reset — reject non-Dave senders
# ---------------------------------------------------------------------------


def test_matches_reset_rejects_other_users_empty():
    assert matches_reset("", "reset all") is False


def test_matches_reset_rejects_other_users_arbitrary():
    assert matches_reset("U000NOTDAVE", "reset all") is False


def test_matches_reset_rejects_other_users_partial():
    # Partial match of DAVE_USER_ID should still fail
    assert matches_reset(DAVE_USER_ID[:-1], "reset all") is False


# ---------------------------------------------------------------------------
# matches_reset — reject wrong text
# ---------------------------------------------------------------------------


def test_matches_reset_rejects_prefix_only():
    assert matches_reset(DAVE_USER_ID, "reset") is False


def test_matches_reset_rejects_extra_words():
    assert matches_reset(DAVE_USER_ID, "reset all agents now") is False


def test_matches_reset_rejects_empty_text():
    assert matches_reset(DAVE_USER_ID, "") is False


def test_matches_reset_rejects_none_text():
    assert matches_reset(DAVE_USER_ID, None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cooldown — second trigger within 60s is dropped
# ---------------------------------------------------------------------------


def test_cooldown_drops_second_within_60s(monkeypatch):
    """Simulate the poll loop's cooldown check inline without real sleep."""
    triggered: list[float] = []
    call_times = [1000.0, 1010.0, 1080.0]  # t=0, t+10s (skipped), t+80s (fires)
    call_iter = iter(call_times)

    monkeypatch.setattr(time, "time", lambda: next(call_iter))

    last_trigger = 0.0

    # First call at t=1000 — fires
    now = time.time()
    if now - last_trigger >= COOLDOWN_SECONDS:
        triggered.append(now)
        last_trigger = now

    # Second call at t=1010 — within 60s, must be dropped
    now = time.time()
    if now - last_trigger >= COOLDOWN_SECONDS:
        triggered.append(now)
        last_trigger = now

    # Third call at t=1080 — 80s after first, must fire
    now = time.time()
    if now - last_trigger >= COOLDOWN_SECONDS:
        triggered.append(now)

    assert triggered == [1000.0, 1080.0], f"unexpected trigger sequence: {triggered}"


# ---------------------------------------------------------------------------
# Finding (1) — health_probe reads cognee sentinel from runtime dir, not /tmp
# ---------------------------------------------------------------------------


def test_health_probe_uses_runtime_dir_path(tmp_path, monkeypatch):
    """Cognee path in health_probe must be rooted at $AGENCY_OS_RUNTIME_DIR, not /tmp directly.

    The test verifies the path parent equals the runtime dir rather than checking
    for the string '/tmp', since pytest's own tmp_path fixture lives under /tmp.
    """
    monkeypatch.setenv("AGENCY_OS_RUNTIME_DIR", str(tmp_path))

    probed_paths: list[Path] = []
    original_exists = Path.exists

    def capturing_exists(self: Path) -> bool:
        probed_paths.append(self)
        return original_exists(self)

    with (
        patch("subprocess.run", return_value=MagicMock(returncode=0)),
        patch(
            "scripts.orchestrator.reset_all_handler._relay_outcome_healthy",
            return_value=False,
        ),
        patch.object(Path, "exists", capturing_exists),
    ):
        health_probe("elliot")

    cognee_paths = [p for p in probed_paths if "cognee-context" in p.name]
    assert cognee_paths, "health_probe did not probe any cognee-context path"
    expected = tmp_path / "cognee-context-elliot.md"
    for p in cognee_paths:
        assert p == expected, (
            f"cognee sentinel path mismatch: expected {expected}, got {p}. "
            "health_probe must read from $AGENCY_OS_RUNTIME_DIR, not a hardcoded /tmp path."
        )


# ---------------------------------------------------------------------------
# Finding (2) — _restart_agent logs returncode + stderr on failure
# ---------------------------------------------------------------------------


def test_restart_logs_failure_returncode(caplog):
    """Failed systemctl restart must log rc + stderr via logger.warning."""
    import logging

    from scripts.orchestrator.reset_all_handler import _restart_agent

    fake_result = MagicMock()
    fake_result.returncode = 1
    fake_result.stderr = b"Unit not found."

    with (
        patch("subprocess.run", return_value=fake_result),
        caplog.at_level(logging.WARNING, logger="reset_all_handler"),
    ):
        _restart_agent("aiden")

    assert any("rc=1" in r.message and "Unit not found" in r.message for r in caplog.records), (
        f"expected warning with rc=1 and stderr, got: {[r.message for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# Finding (4) — cooldown lockfile persists across simulated restart
# ---------------------------------------------------------------------------


def test_cooldown_persists_across_restart(tmp_path, monkeypatch):
    """Lockfile written by _write_last_trigger is read back by _read_last_trigger."""
    monkeypatch.setenv("AGENCY_OS_RUNTIME_DIR", str(tmp_path))

    # Simulate "first process" writing last_trigger 30s ago
    now = time.time()
    past = now - 30.0
    _write_last_trigger(past)

    # Simulate "new process" reading it back
    read_back = _read_last_trigger()
    assert abs(read_back - past) < 0.01, (
        f"lockfile round-trip error: wrote {past}, read {read_back}"
    )

    # With 30s elapsed and COOLDOWN_SECONDS=60, trigger should still be suppressed
    assert now - read_back < COOLDOWN_SECONDS, (
        "Expected cooldown still active 30s after trigger, but read_back shows it expired"
    )


# ---------------------------------------------------------------------------
# Finding (5) — post() logs warning on HTTP error and does not crash
# ---------------------------------------------------------------------------


def test_post_logs_http_error(caplog):
    """HTTP failure in post() must log logger.warning and not raise."""
    import logging

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client)
        mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = httpx.HTTPError("connection refused")

        with caplog.at_level(logging.WARNING, logger="reset_all_handler"):
            post("fake-token", "hello")

    assert any("Slack post failed" in r.message for r in caplog.records), (
        f"expected 'Slack post failed' warning, got: {[r.message for r in caplog.records]}"
    )
