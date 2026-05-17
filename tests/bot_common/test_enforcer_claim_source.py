"""tests/bot_common/test_enforcer_claim_source.py — KEI-95 enforcer exemption.

Covers:
  - check_r8: auto_loop lookup → Rule 8 does NOT fire
  - check_r8: manual lookup → Rule 8 fires as today
  - check_r2: auto_loop lookup → Step-0 gate does NOT fire
  - check_r2: manual lookup → Step-0 gate fires as today
  - check_r8: DB unreachable (lookup raises) → safe default = 'manual' → fires
  - check_r2: DB unreachable (lookup raises) → safe default = 'manual' → fires
  - check_r8: lookup returns None (no active task) → fires (governance-preserving)
  - check_r2: lookup returns None (no active task) → fires (governance-preserving)
"""

from __future__ import annotations

from src.bot_common.enforcer_deterministic import check_r2, check_r8

# ─── Dispatch text that triggers R8 ─────────────────────────────────────────
_R8_TRIGGER = "atlas dispatched to KEI-95 build task"

# ─── Execution text that triggers R2 (no Step-0 in context) ─────────────────
_R2_TRIGGER = "Committing migration and pushing to origin."

# ─── check_r8 — auto_loop exemption ─────────────────────────────────────────


def test_r8_auto_loop_skips_dispatch_coordination() -> None:
    """Rule 8 does NOT fire when claim_source lookup returns 'auto_loop'."""

    def lookup(callsign: str) -> str:
        return "auto_loop"

    result = check_r8(
        _R8_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is None, f"Expected no violation but got: {result}"


def test_r8_manual_still_fires_as_before() -> None:
    """Rule 8 fires normally when claim_source is 'manual'."""

    def lookup(callsign: str) -> str:
        return "manual"

    result = check_r8(
        _R8_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is not None
    assert result["rule_number"] == 8


def test_r8_lookup_raises_treats_as_manual() -> None:
    """If lookup raises, safe default is 'manual' — R8 still fires."""

    def lookup(callsign: str) -> str:
        raise ConnectionError("DB unreachable")

    result = check_r8(
        _R8_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is not None
    assert result["rule_number"] == 8


def test_r8_lookup_returns_none_treats_as_manual() -> None:
    """None return (no active task) → governance-preserving → fires."""

    def lookup(callsign: str) -> None:
        return None

    result = check_r8(
        _R8_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is not None
    assert result["rule_number"] == 8


def test_r8_no_lookup_provided_behaves_as_before() -> None:
    """Backwards-compat: no claim_source_lookup → R8 fires on dispatch trigger."""
    result = check_r8(_R8_TRIGGER, recent_messages=[])
    assert result is not None
    assert result["rule_number"] == 8


# ─── check_r2 — auto_loop exemption ─────────────────────────────────────────


def test_r2_auto_loop_skips_step0_gate() -> None:
    """Step-0 gate (R2) does NOT fire when claim_source lookup returns 'auto_loop'."""

    def lookup(callsign: str) -> str:
        return "auto_loop"

    result = check_r2(
        _R2_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is None, f"Expected no violation but got: {result}"


def test_r2_manual_still_fires_as_before() -> None:
    """Step-0 gate fires normally when claim_source is 'manual'."""

    def lookup(callsign: str) -> str:
        return "manual"

    result = check_r2(
        _R2_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is not None
    assert result["rule_number"] == 2


def test_r2_lookup_raises_treats_as_manual() -> None:
    """If lookup raises, safe default is 'manual' — R2 still fires."""

    def lookup(callsign: str) -> str:
        raise ConnectionError("DB unreachable")

    result = check_r2(
        _R2_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is not None
    assert result["rule_number"] == 2


def test_r2_lookup_returns_none_treats_as_manual() -> None:
    """None return (no active task) → governance-preserving → fires."""

    def lookup(callsign: str) -> None:
        return None

    result = check_r2(
        _R2_TRIGGER,
        recent_messages=[],
        callsign="aiden",
        claim_source_lookup=lookup,
    )
    assert result is not None
    assert result["rule_number"] == 2


def test_r2_no_lookup_provided_behaves_as_before() -> None:
    """Backwards-compat: no claim_source_lookup → R2 fires when no Step-0 in context."""
    result = check_r2(_R2_TRIGGER, recent_messages=[])
    assert result is not None
    assert result["rule_number"] == 2


# ─── callsign=None guard ─────────────────────────────────────────────────────


def test_r8_no_callsign_skips_lookup() -> None:
    """No callsign → lookup not invoked → R8 fires as normal."""
    calls: list = []

    def lookup(callsign: str) -> str:
        calls.append(callsign)
        return "auto_loop"

    result = check_r8(
        _R8_TRIGGER,
        recent_messages=[],
        callsign=None,
        claim_source_lookup=lookup,
    )
    assert not calls, "lookup should not be called when callsign=None"
    assert result is not None


def test_r2_no_callsign_skips_lookup() -> None:
    """No callsign → lookup not invoked → R2 fires as normal (no Step-0 in context)."""
    calls: list = []

    def lookup(callsign: str) -> str:
        calls.append(callsign)
        return "auto_loop"

    result = check_r2(
        _R2_TRIGGER,
        recent_messages=[],
        callsign=None,
        claim_source_lookup=lookup,
    )
    assert not calls, "lookup should not be called when callsign=None"
    assert result is not None
