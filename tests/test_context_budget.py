"""Unit tests for src/relay/context_budget.py.

Covers role-ceiling lookup + token-count branches + summariser-fallback
+ rejection paths + alerts emit + DI surfaces.

bd: Agency_OS-blka (Cutover Blocker 3, Viktor lever 25).
"""

from __future__ import annotations

from typing import Any

import pytest

from src.relay.context_budget import (
    DECISION_REJECTED,
    DECISION_SPAWN_OK,
    DECISION_SUMMARISED,
    ROLE_BUILDER,
    ROLE_CEILINGS,
    ROLE_CHAT,
    ROLE_DELIBERATOR,
    ROLE_REVIEWER,
    ContextBudgetError,
    _default_token_counter,
    check_context_budget,
)

# ─── Anchor constants — Viktor lever 25 ceiling table ──────────────────────────


def test_role_ceilings_match_cat21_anchor():
    """Lever-25 anchor: Reviewer 8k / Deliberator 20k / Builder 12k / Chat 4k."""
    assert ROLE_CEILINGS[ROLE_REVIEWER] == 8_000
    assert ROLE_CEILINGS[ROLE_DELIBERATOR] == 20_000
    assert ROLE_CEILINGS[ROLE_BUILDER] == 12_000
    assert ROLE_CEILINGS[ROLE_CHAT] == 4_000


def test_role_ceilings_has_exactly_four_roles():
    """If a new role appears, the ceiling MUST be ratified per Dave directive."""
    assert set(ROLE_CEILINGS.keys()) == {
        ROLE_REVIEWER,
        ROLE_DELIBERATOR,
        ROLE_BUILDER,
        ROLE_CHAT,
    }


# ─── Default token counter ─────────────────────────────────────────────────────


def test_default_token_counter_is_chars_over_three():
    """Conservative chars/3 = slightly over-counts; ceiling decisions favor
    summarise-over-silent-overflow."""
    assert _default_token_counter("") == 0
    assert _default_token_counter("abc") == 1  # 3/3 = 1
    assert _default_token_counter("abcd") == 2  # ceil(4/3) = 2
    assert _default_token_counter("x" * 24_000) == 8_000  # ceiling-equal


# ─── check_context_budget — SPAWN_OK path ──────────────────────────────────────


def test_under_ceiling_returns_spawn_ok():
    """Reviewer ceiling 8000 tokens; 100 chars = 34 tokens → SPAWN_OK."""
    result = check_context_budget(ROLE_REVIEWER, "x" * 100)
    assert result.decision == DECISION_SPAWN_OK
    assert result.summarised is False
    assert result.context == "x" * 100  # original passed through
    assert result.ceiling_tokens == 8_000
    assert result.initial_tokens == 34
    assert result.final_tokens == 34


def test_at_ceiling_exactly_returns_spawn_ok():
    """Boundary case — token count == ceiling is OK (≤ comparison)."""
    # 24000 chars / 3 = 8000 tokens = reviewer ceiling exactly
    result = check_context_budget(ROLE_REVIEWER, "x" * 24_000)
    assert result.decision == DECISION_SPAWN_OK


# ─── check_context_budget — over-ceiling without summariser ────────────────────


def test_over_ceiling_without_summariser_returns_rejected():
    """No summariser provided → hard fail immediately."""
    # 30000 chars / 3 = 10000 tokens > 8000 reviewer ceiling
    result = check_context_budget(ROLE_REVIEWER, "x" * 30_000)
    assert result.decision == DECISION_REJECTED
    assert result.summarised is False
    assert result.initial_tokens == 10_000
    assert result.final_tokens == 10_000  # unchanged from initial
    assert result.reason is not None
    assert "no summariser configured" in result.reason


# ─── check_context_budget — summariser fires + succeeds ────────────────────────


def test_over_ceiling_with_summariser_returns_summarised():
    """Summariser produces in-budget output → SUMMARISED with summary as context."""
    over_context = "x" * 30_000  # 10000 tokens

    def fake_summariser(over_context: str, target_tokens: int) -> str:
        # Return a 5000-token summary (within 8000 ceiling)
        return "compressed " * 1_500  # 16_500 chars / 3 = 5500 tokens

    result = check_context_budget(
        ROLE_REVIEWER,
        over_context,
        summariser=fake_summariser,
    )
    assert result.decision == DECISION_SUMMARISED
    assert result.summarised is True
    assert result.context.startswith("compressed")
    assert result.initial_tokens == 10_000
    assert result.final_tokens == 5_500
    assert result.ceiling_tokens == 8_000


# ─── check_context_budget — summariser fires + still over → REJECTED ───────────


def test_summariser_still_over_ceiling_returns_rejected_and_alerts():
    """Summariser ran but output still > ceiling → REJECTED + alerts emitted."""
    alerts_seen: list[dict[str, Any]] = []

    def fake_summariser(_ctx: str, _target: int) -> str:
        # Returns 9000 tokens > 8000 reviewer ceiling
        return "still big " * 2_700  # 27_000 chars / 3 = 9000 tokens

    result = check_context_budget(
        ROLE_REVIEWER,
        "x" * 30_000,
        summariser=fake_summariser,
        alerts_emitter=alerts_seen.append,
    )
    assert result.decision == DECISION_REJECTED
    assert result.summarised is False
    assert result.final_tokens == 9_000
    assert result.reason is not None
    assert "still over ceiling" in result.reason
    # Alert MUST have fired
    assert len(alerts_seen) == 1
    payload = alerts_seen[0]
    assert payload["kind"] == "context_budget_rejected"
    assert payload["role"] == ROLE_REVIEWER
    assert payload["ceiling_tokens"] == 8_000
    assert payload["initial_tokens"] == 10_000
    assert payload["final_tokens"] == 9_000


def test_no_summariser_rejection_still_emits_alert():
    """REJECTED via no-summariser path MUST also emit the alert."""
    alerts_seen: list[dict[str, Any]] = []
    check_context_budget(
        ROLE_REVIEWER,
        "x" * 30_000,
        alerts_emitter=alerts_seen.append,
    )
    assert len(alerts_seen) == 1
    assert alerts_seen[0]["kind"] == "context_budget_rejected"


# ─── check_context_budget — summariser exception → REJECTED + alerts ───────────


def test_summariser_raises_returns_rejected_with_exception_reason():
    """Summariser is an injected boundary; failures swallowed + REJECTED."""
    alerts_seen: list[dict[str, Any]] = []

    def broken_summariser(_ctx: str, _target: int) -> str:
        raise RuntimeError("LLM rate-limited")

    result = check_context_budget(
        ROLE_REVIEWER,
        "x" * 30_000,
        summariser=broken_summariser,
        alerts_emitter=alerts_seen.append,
    )
    assert result.decision == DECISION_REJECTED
    assert result.reason is not None
    assert "summariser raised: RuntimeError: LLM rate-limited" in result.reason
    assert len(alerts_seen) == 1


def test_summariser_returns_empty_string_returns_rejected():
    """Summariser returning empty / non-string output is treated as failure."""

    def empty_summariser(_ctx: str, _target: int) -> str:
        return ""

    result = check_context_budget(
        ROLE_REVIEWER,
        "x" * 30_000,
        summariser=empty_summariser,
    )
    assert result.decision == DECISION_REJECTED
    assert result.reason is not None
    assert "empty / non-string output" in result.reason


# ─── alerts emitter robustness ─────────────────────────────────────────────────


def test_alerts_emitter_raising_does_not_block_rejection():
    """Alerts channel down MUST NEVER block the decision return."""

    def broken_alerts(_payload: dict[str, Any]) -> None:
        raise ConnectionError("Better Stack 500")

    result = check_context_budget(
        ROLE_REVIEWER,
        "x" * 30_000,
        alerts_emitter=broken_alerts,
    )
    # Decision STILL returned — caller never blocks on alert failure
    assert result.decision == DECISION_REJECTED


# ─── invariant violations ──────────────────────────────────────────────────────


def test_unknown_role_raises():
    with pytest.raises(ContextBudgetError, match="unknown role"):
        check_context_budget("auditor", "x" * 100)


def test_empty_context_raises():
    with pytest.raises(ContextBudgetError, match="non-empty"):
        check_context_budget(ROLE_REVIEWER, "")


# ─── per-role ceiling end-to-end smoke ─────────────────────────────────────────


def test_each_role_enforces_its_own_ceiling():
    """Same 5000-token context: under for deliberator/builder, over for reviewer
    (5000 < 8000 — wait, that's under). Use larger context that's over chat (4k)
    + builder (12k) thresholds."""
    # 15000-token context (45000 chars / 3 = 15000)
    big_context = "y" * 45_000
    assert (
        check_context_budget(ROLE_DELIBERATOR, big_context).decision == DECISION_SPAWN_OK
    )  # 15k < 20k
    assert (
        check_context_budget(ROLE_BUILDER, big_context).decision == DECISION_REJECTED
    )  # 15k > 12k
    assert (
        check_context_budget(ROLE_REVIEWER, big_context).decision == DECISION_REJECTED
    )  # 15k > 8k
    assert check_context_budget(ROLE_CHAT, big_context).decision == DECISION_REJECTED  # 15k > 4k


# ─── token_counter DI ──────────────────────────────────────────────────────────


def test_custom_token_counter_used_for_decision():
    """Caller injects a real tokeniser (e.g. tiktoken) — must be honored."""
    # tiny string but inject a counter that always reports 100_000 tokens
    result = check_context_budget(
        ROLE_REVIEWER,
        "tiny",
        token_counter=lambda _: 100_000,
    )
    # Without summariser → REJECTED because counter says over-budget
    assert result.decision == DECISION_REJECTED
    assert result.initial_tokens == 100_000


# ─── e2e verbatim acceptance criterion (5) ─────────────────────────────────────


def test_e2e_verbatim_over_budget_compressed_or_rejected():
    """Acceptance criterion (5) per dispatch: verbatim test showing over-budget
    context is compressed-or-rejected.

    Stages:
      1. Over-budget context → no summariser → REJECTED
      2. Same context + working summariser → SUMMARISED
      3. Same context + broken summariser → REJECTED with exception reason
      4. Same context + summariser that still over-shoots → REJECTED
    """
    over_context = "z" * 30_000  # 10000 tokens > 8000 reviewer ceiling

    # Stage 1 — REJECTED, no summariser
    r1 = check_context_budget(ROLE_REVIEWER, over_context)
    assert r1.decision == DECISION_REJECTED
    assert r1.initial_tokens == 10_000

    # Stage 2 — SUMMARISED via working summariser
    r2 = check_context_budget(
        ROLE_REVIEWER,
        over_context,
        summariser=lambda _ctx, _tgt: "compressed " * 1_500,
    )
    assert r2.decision == DECISION_SUMMARISED
    assert r2.context.startswith("compressed")
    assert r2.final_tokens < r2.initial_tokens

    # Stage 3 — REJECTED via broken summariser
    def broken(_ctx: str, _tgt: int) -> str:
        raise ValueError("boom")

    r3 = check_context_budget(
        ROLE_REVIEWER,
        over_context,
        summariser=broken,
    )
    assert r3.decision == DECISION_REJECTED
    assert r3.reason is not None
    assert "ValueError: boom" in r3.reason

    # Stage 4 — REJECTED via summariser that still over-shoots
    r4 = check_context_budget(
        ROLE_REVIEWER,
        over_context,
        summariser=lambda _ctx, _tgt: "still big " * 2_700,  # 9000 tokens > 8000
    )
    assert r4.decision == DECISION_REJECTED
    assert r4.reason is not None
    assert "still over ceiling" in r4.reason
