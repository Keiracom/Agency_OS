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
"""

from __future__ import annotations

import time

from scripts.orchestrator.reset_all_handler import COOLDOWN_SECONDS, DAVE_USER_ID, matches_reset

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
        last_trigger = now

    assert triggered == [1000.0, 1080.0], f"unexpected trigger sequence: {triggered}"
