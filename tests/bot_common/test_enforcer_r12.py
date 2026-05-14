"""Tests for R12 AUTO-KEI-ENFORCER (KEI-18 / Linear KEI-18).

R12 fires when a CEO directive in #ceo from Dave does NOT result in a new
Linear KEI within 5 minutes. Stateless detector + stateful timer:
  - is_r12_directive(text, channel, callsign) — pattern + channel + callsign gate
  - check_r12(directive_text, directive_ts, now, linear_keis_since_count) — fires
    if 5+ min elapsed AND no new KEI

Same composition as R13 + R14 (Aiden's pre-restart cascade pattern).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.bot_common.enforcer_deterministic import (
    _R12_CEO_CHANNEL_ID,
    _R12_KEI_CREATE_WINDOW_SECONDS,
    check_r12,
    is_r12_directive,
)


# ─── is_r12_directive ──────────────────────────────────────────────────────


def test_is_r12_directive_urgent_imperative_dave_in_ceo_returns_true():
    """Canonical CEO directive shape — URGENT + imperative verb in #ceo from Dave."""
    text = "URGENT — build the Auto-KEI enforcer now. Drop everything else."
    assert is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="dave") is True


def test_is_r12_directive_imperative_only_returns_true():
    """Imperative verb alone is enough — no URGENT keyword required."""
    text = "Build the secret redaction middleware. KEI-57 pre-condition for KEI-46."
    assert is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="dave") is True


def test_is_r12_directive_should_must_with_action_returns_true():
    """'should be done' / 'must be shipped' style directives."""
    text = "This should be shipped before the weekend."
    assert is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="dave") is True


def test_is_r12_directive_question_returns_false():
    """Trailing question mark on the last sentence — NOT a directive."""
    text = "Should we build the Auto-KEI enforcer now?"
    assert is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="dave") is False


def test_is_r12_directive_wrong_channel_returns_false():
    """Channel-gated to #ceo. #execution traffic is not subject to R12."""
    text = "URGENT — fix the rate-limit bug now."
    assert is_r12_directive(text, channel="C0B3QB0K1GQ", callsign="dave") is False


def test_is_r12_directive_wrong_callsign_returns_false():
    """Callsign-gated to Dave. Elliot posting in #ceo is governance-mirror, not directive."""
    text = "URGENT — build this now."
    assert is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="elliot") is False


def test_is_r12_directive_empty_text_returns_false():
    """Whitespace-only post is never a directive."""
    assert is_r12_directive("   \n  ", channel=_R12_CEO_CHANNEL_ID, callsign="dave") is False


def test_is_r12_directive_ceo_alias_accepted():
    """callsign='ceo' or Dave's user ID U091TGTPB9U also matches."""
    text = "Build the auto-record mechanism. URGENT."
    assert is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="CEO") is True
    assert (
        is_r12_directive(text, channel=_R12_CEO_CHANNEL_ID, callsign="U091TGTPB9U") is True
    )


# ─── check_r12 — timer + Linear-count gate ──────────────────────────────────


def test_check_r12_fires_when_directive_aged_5min_and_no_kei():
    """Canonical R12 fire: directive >5min old + 0 new Linear KEIs since."""
    directive_ts = datetime.now(UTC) - timedelta(seconds=_R12_KEI_CREATE_WINDOW_SECONDS + 30)
    result = check_r12(
        "URGENT — build the redaction module now.",
        directive_ts,
        linear_keis_since_count=0,
        channel=_R12_CEO_CHANNEL_ID,
        callsign="dave",
    )
    assert result is not None
    assert result["violation"] is True
    assert result["rule_number"] == 12
    assert "AUTO-KEI" in result["rule_name"]
    assert "[R12-REMINDER:elliot]" in result["fire_message"]


def test_check_r12_passes_when_directive_under_5min():
    """Window not yet elapsed — no fire even if no KEI yet."""
    directive_ts = datetime.now(UTC) - timedelta(seconds=60)  # 1 min old
    result = check_r12(
        "URGENT — build the redaction module now.",
        directive_ts,
        linear_keis_since_count=0,
        channel=_R12_CEO_CHANNEL_ID,
        callsign="dave",
    )
    assert result is None


def test_check_r12_passes_when_kei_already_created():
    """5+ min elapsed but at least one Linear KEI created since directive — pass."""
    directive_ts = datetime.now(UTC) - timedelta(seconds=_R12_KEI_CREATE_WINDOW_SECONDS + 30)
    result = check_r12(
        "URGENT — build the redaction module now.",
        directive_ts,
        linear_keis_since_count=1,
        channel=_R12_CEO_CHANNEL_ID,
        callsign="dave",
    )
    assert result is None


def test_check_r12_passes_for_non_directive_text():
    """is_r12_directive returns False → check_r12 no-op even with window elapsed."""
    directive_ts = datetime.now(UTC) - timedelta(seconds=_R12_KEI_CREATE_WINDOW_SECONDS + 30)
    result = check_r12(
        "Are we on track for the weekend release?",  # question, not directive
        directive_ts,
        linear_keis_since_count=0,
        channel=_R12_CEO_CHANNEL_ID,
        callsign="dave",
    )
    assert result is None


def test_check_r12_uses_injected_now():
    """`now` argument overrides datetime.now() for deterministic testing."""
    directive_ts = datetime(2026, 5, 14, 0, 0, 0, tzinfo=UTC)
    now = directive_ts + timedelta(seconds=_R12_KEI_CREATE_WINDOW_SECONDS + 60)
    result = check_r12(
        "URGENT — ship the cap fix.",
        directive_ts,
        now=now,
        linear_keis_since_count=0,
        channel=_R12_CEO_CHANNEL_ID,
        callsign="dave",
    )
    assert result is not None
    assert result["rule_number"] == 12
