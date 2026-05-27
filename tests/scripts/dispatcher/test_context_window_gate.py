"""Tests for scripts/dispatcher/_context_window_gate.py (cutover step 4.5 PR #3).

Covers:
  - disabled fail-open (rollout phase 1)
  - empty-context fail-open
  - PROCEED on SPAWN_OK
  - PROCEED on SUMMARISED (when summariser injected)
  - SKIP_SPAWN on REJECTED (over ceiling, no summariser)
  - Role derivation (explicit > task_type > builder default)
  - Context derivation (multi-field concat)
"""

from __future__ import annotations

from typing import Any

import pytest

from scripts.dispatcher import _context_window_gate
from src.relay.context_budget import (
    DECISION_REJECTED,
    DECISION_SPAWN_OK,
    DECISION_SUMMARISED,
    ROLE_BUILDER,
    ROLE_CEILINGS,
    ROLE_CHAT,
    ROLE_DELIBERATOR,
    ROLE_REVIEWER,
)

# ----- disabled fail-open -----


def test_disabled_returns_proceed_none() -> None:
    action, result = _context_window_gate.evaluate(
        {"from": "elliot", "type": "task_dispatch", "brief": "x"}
    )
    assert action == _context_window_gate.ContextWindowAction.PROCEED
    assert result is None


# ----- empty-context fail-open -----


def test_empty_context_proceeds() -> None:
    action, result = _context_window_gate.evaluate(
        {"from": "elliot", "type": "task_dispatch"},
        enabled=True,
    )
    assert action == _context_window_gate.ContextWindowAction.PROCEED
    assert result is None


# ----- PROCEED on SPAWN_OK -----


def test_under_ceiling_proceeds() -> None:
    # Short brief — well under any ceiling.
    action, result = _context_window_gate.evaluate(
        {
            "from": "elliot",
            "type": "task_dispatch",
            "task_type": "build",
            "brief": "short brief",
        },
        enabled=True,
    )
    assert action == _context_window_gate.ContextWindowAction.PROCEED
    assert result is not None
    assert result.decision == DECISION_SPAWN_OK


# ----- SKIP_SPAWN on REJECTED -----


def test_over_ceiling_no_summariser_skips() -> None:
    # CHAT ceiling is 4K tokens. Chars/3 conservative counter →
    # 4K tokens ≈ 12K chars. Send 60K chars to ensure over.
    huge_brief = "x" * 60_000
    action, result = _context_window_gate.evaluate(
        {
            "from": "atlas",
            "type": "task_dispatch",
            "role": ROLE_CHAT,
            "brief": huge_brief,
        },
        enabled=True,
    )
    assert action == _context_window_gate.ContextWindowAction.SKIP_SPAWN
    assert result is not None
    assert result.decision == DECISION_REJECTED


# ----- PROCEED on SUMMARISED -----


def test_summariser_compresses_to_proceed() -> None:
    huge_brief = "x" * 60_000
    summariser_calls: list[tuple[str, int]] = []

    def fake_summariser(context: str, ceiling: int) -> str:
        summariser_calls.append((context[:10], ceiling))
        return "compressed"  # tiny → well under ceiling

    action, result = _context_window_gate.evaluate(
        {
            "from": "atlas",
            "type": "task_dispatch",
            "role": ROLE_CHAT,
            "brief": huge_brief,
        },
        enabled=True,
        summariser=fake_summariser,
    )
    assert action == _context_window_gate.ContextWindowAction.PROCEED
    assert result is not None
    assert result.decision == DECISION_SUMMARISED
    assert len(summariser_calls) == 1


# ----- Role derivation -----


@pytest.mark.parametrize(
    "envelope,expected_role",
    [
        ({"role": ROLE_REVIEWER}, ROLE_REVIEWER),
        ({"role": ROLE_DELIBERATOR}, ROLE_DELIBERATOR),
        ({"role": ROLE_BUILDER}, ROLE_BUILDER),
        ({"role": ROLE_CHAT}, ROLE_CHAT),
        ({"task_type": "pr_review"}, ROLE_REVIEWER),
        ({"task_type": "deliberation"}, ROLE_DELIBERATOR),
        ({"task_type": "build"}, ROLE_BUILDER),
        ({"task_type": "chat"}, ROLE_CHAT),
        ({}, ROLE_BUILDER),  # default
        ({"task_type": "unknown_task"}, ROLE_BUILDER),  # unknown task → default
        ({"role": "bogus"}, ROLE_BUILDER),  # unknown role → fallback
    ],
)
def test_role_derivation(envelope: dict[str, Any], expected_role: str) -> None:
    assert _context_window_gate._envelope_to_role(envelope) == expected_role


# ----- Context derivation -----


def test_context_concat_multi_field() -> None:
    envelope = {"brief": "B", "summary": "S", "text": "T", "task_ref": "R"}
    assert _context_window_gate._envelope_to_context(envelope) == "B S T R"


def test_context_skips_empty_fields() -> None:
    envelope = {"brief": "B", "summary": "", "text": None, "task_ref": "R"}
    assert _context_window_gate._envelope_to_context(envelope) == "B R"


def test_context_empty_envelope() -> None:
    assert _context_window_gate._envelope_to_context({}) == ""


# ----- All ceilings represented -----


def test_role_ceilings_complete() -> None:
    """Smoke: all 4 ceiling roles map distinctly + task_type taxonomy is exhaustive."""
    assert set(ROLE_CEILINGS) == {ROLE_REVIEWER, ROLE_DELIBERATOR, ROLE_BUILDER, ROLE_CHAT}
    assert set(_context_window_gate._TASK_TYPE_TO_ROLE.values()) == {
        ROLE_REVIEWER,
        ROLE_DELIBERATOR,
        ROLE_BUILDER,
        ROLE_CHAT,
    }
