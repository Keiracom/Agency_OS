"""context_budget — per-role context-window ceiling enforcement.

Cutover Readiness Gate INFRASTRUCTURE-SIDE — "context window budget per role"
criterion (Viktor lever 25 in Cat 21, Dave directive 2026-05-27).

Mechanical pre-spawn check that bounds the assembled-context token count per
role. The dispatcher (PR #1188 + future src/dispatcher consumers) calls
check_context_budget() BEFORE handing the prompt to claude. Path:

  1. Count tokens of assembled context (system prompt + skills + atoms + task).
  2. If under ceiling → SPAWN_OK (caller proceeds with original context).
  3. If over ceiling → call summariser (cheap Sonnet) to compress to budget.
  4. If summary still over → REJECTED + alerts emit + caller MUST NOT spawn.

Module placement note: dispatch named `src/dispatcher/context_budget.py` but
the dispatcher binary already lives at `scripts/dispatcher/` (PR #1188).
Creating `src/dispatcher/` would split the namespace. This module lives at
`src/relay/` alongside spawn_composer.py + envelope_schema.py +
paused_tasks.py — consistent library-layer placement.

bd: Agency_OS-blka
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

# Role ceilings per Viktor lever 25 / Dave directive 2026-05-27.
# Tokens, not chars. Reviewer is the tightest (verbatim-code-quote review
# rarely needs more than 8k). Deliberator is the loosest (multi-PR
# cross-cite scope). Builder middles (typical task context). Chat is small
# (Dave-DM conversational turns).
ROLE_REVIEWER = "reviewer"
ROLE_DELIBERATOR = "deliberator"
ROLE_BUILDER = "builder"
ROLE_CHAT = "chat"

ROLE_CEILINGS: Mapping[str, int] = {
    ROLE_REVIEWER: 8_000,
    ROLE_DELIBERATOR: 20_000,
    ROLE_BUILDER: 12_000,
    ROLE_CHAT: 4_000,
}

# Decision values returned from check_context_budget().
DECISION_SPAWN_OK = "spawn_ok"
DECISION_SUMMARISED = "summarised"
DECISION_REJECTED = "rejected"


class ContextBudgetError(ValueError):
    """Raised on unknown role or empty context (invariant violations)."""


@dataclass(frozen=True, kw_only=True)
class BudgetResult:
    """What check_context_budget() returns."""

    decision: str
    role: str
    ceiling_tokens: int
    initial_tokens: int
    final_tokens: int
    context: str  # the context the caller should pass to spawn (original OR summarised)
    summarised: bool
    reason: str | None = None  # populated on REJECTED


# Conservative token estimator. Same chars/4 shape as
# src/keiracom_system/cache/litellm_helpers.py::_estimate_tokens — under-
# estimates by ~10-20% on English prose, MORE on dense code. For ceiling
# enforcement we WANT slight over-counting (better one extra summarise call
# than a silent over-ceiling spawn), so we use chars/3 instead of chars/4.
# Caller can override via `token_counter` for accurate counts (e.g. tiktoken).
_DEFAULT_CHARS_PER_TOKEN = 3


def _default_token_counter(text: str) -> int:
    """Conservative chars/3 token estimator — slightly OVER-counts to favor
    summarise-over-silent-overflow at ceiling decisions."""
    return (len(text) + _DEFAULT_CHARS_PER_TOKEN - 1) // _DEFAULT_CHARS_PER_TOKEN


TokenCounter = Callable[[str], int]
Summariser = Callable[[str, int], str]  # (over_budget_context, target_tokens) -> summary
AlertEmitter = Callable[[Mapping[str, Any]], None]


def _no_op_alerts(_payload: Mapping[str, Any]) -> None:
    """Default fallback when caller doesn't provide an alerts emitter."""


def check_context_budget(
    role: str,
    context: str,
    *,
    summariser: Summariser | None = None,
    token_counter: TokenCounter = _default_token_counter,
    alerts_emitter: AlertEmitter = _no_op_alerts,
) -> BudgetResult:
    """Pre-spawn budget check + optional summarise fallback.

    Args:
        role: one of ROLE_CEILINGS keys (reviewer / deliberator / builder / chat).
        context: assembled context string (system prompt + skills + atoms + task).
        summariser: optional callable to compress over-budget context. If None,
            over-budget context is REJECTED immediately (no summarise attempt).
        token_counter: callable for token counting. Default is chars/3
            conservative estimator; production callers should inject tiktoken
            or similar.
        alerts_emitter: callable invoked with a payload when REJECTED fires.
            Defaults to no-op so callers without alerting wired up still work.

    Returns:
        BudgetResult with decision in {SPAWN_OK, SUMMARISED, REJECTED} and the
        context the caller should use (original on SPAWN_OK, summary on
        SUMMARISED, original on REJECTED — caller MUST NOT spawn).

    Raises:
        ContextBudgetError on unknown role or empty context.
    """
    if role not in ROLE_CEILINGS:
        raise ContextBudgetError(f"unknown role {role!r}; valid roles: {sorted(ROLE_CEILINGS)}")
    if not context:
        raise ContextBudgetError("context must be a non-empty string")

    ceiling = ROLE_CEILINGS[role]
    initial = token_counter(context)

    if initial <= ceiling:
        return BudgetResult(
            decision=DECISION_SPAWN_OK,
            role=role,
            ceiling_tokens=ceiling,
            initial_tokens=initial,
            final_tokens=initial,
            context=context,
            summarised=False,
        )

    # Over ceiling. Attempt summarise fallback if caller provided one.
    if summariser is None:
        return _reject(
            role=role,
            ceiling=ceiling,
            initial=initial,
            final=initial,
            context=context,
            reason="over ceiling and no summariser configured",
            alerts_emitter=alerts_emitter,
        )

    try:
        summary = summariser(context, ceiling)
    except Exception as exc:  # noqa: BLE001 — summariser is an injected boundary
        return _reject(
            role=role,
            ceiling=ceiling,
            initial=initial,
            final=initial,
            context=context,
            reason=f"summariser raised: {type(exc).__name__}: {exc}",
            alerts_emitter=alerts_emitter,
        )

    if not isinstance(summary, str) or not summary:
        return _reject(
            role=role,
            ceiling=ceiling,
            initial=initial,
            final=initial,
            context=context,
            reason="summariser returned empty / non-string output",
            alerts_emitter=alerts_emitter,
        )

    final = token_counter(summary)
    if final > ceiling:
        return _reject(
            role=role,
            ceiling=ceiling,
            initial=initial,
            final=final,
            context=context,
            reason=f"summary still over ceiling ({final} > {ceiling})",
            alerts_emitter=alerts_emitter,
        )

    return BudgetResult(
        decision=DECISION_SUMMARISED,
        role=role,
        ceiling_tokens=ceiling,
        initial_tokens=initial,
        final_tokens=final,
        context=summary,
        summarised=True,
    )


def _reject(
    *,
    role: str,
    ceiling: int,
    initial: int,
    final: int,
    context: str,
    reason: str,
    alerts_emitter: AlertEmitter,
) -> BudgetResult:
    """Build a REJECTED result + fire the alert. Alert failures swallowed."""
    payload: dict[str, Any] = {
        "kind": "context_budget_rejected",
        "role": role,
        "ceiling_tokens": ceiling,
        "initial_tokens": initial,
        "final_tokens": final,
        "reason": reason,
    }
    # Alerts channel down must NEVER block the rejection signal.
    # Alerts emitter is an injected boundary; swallow all exceptions.
    with contextlib.suppress(Exception):
        alerts_emitter(payload)
    return BudgetResult(
        decision=DECISION_REJECTED,
        role=role,
        ceiling_tokens=ceiling,
        initial_tokens=initial,
        final_tokens=final,
        context=context,
        summarised=False,
        reason=reason,
    )
