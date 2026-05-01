"""src/coo_bot/tier_framework.py — Max COO autonomy tier gate.

MAX-COO-PHASE-B / Phase B File 1.

Tiered approval framework that decides whether the COO bot may post a
given action autonomously, based on:

  1. COO_APPROVAL_TIER env var (0..3, default 0)
  2. STOP MAX state file at /home/elliotbot/clawd/state/coo_tier_override
     (when present, force-tier-zero regardless of env)

Tier categories (per docs/architecture/MAX_COO_ARCHITECTURE.md):
  Tier 0 — nothing autonomous (every action goes to Dave)
  Tier 1 — pre-approved low-risk: governance flags, dispatch acks
  Tier 2 — Tier 1 + routine ops: status reports, memory writes, log queries
  Tier 3 — full proxy: anything Tier 2 plus directive issuance, peer dispatch

GOV-12: each tier check is a runtime conditional, not a comment.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

STOP_OVERRIDE_PATH = Path(
    os.environ.get(
        "COO_TIER_OVERRIDE_PATH",
        "/home/elliotbot/clawd/state/coo_tier_override",
    )
)

TIER_1_ACTIONS: frozenset[str] = frozenset({
    "governance_flag",
    "dispatch_ack",
})
TIER_2_ACTIONS: frozenset[str] = frozenset({
    "status_report",
    "memory_write",
    "log_query",
})
TIER_3_ACTIONS: frozenset[str] = frozenset({
    "directive_issuance",
    "peer_dispatch",
})


def force_tier_zero() -> bool:
    """Return True iff the STOP MAX override file is present."""
    return STOP_OVERRIDE_PATH.is_file()


def write_stop_override(reason: str = "") -> None:
    """Create the STOP MAX override file. Idempotent. Best-effort on parent
    dir creation."""
    try:
        STOP_OVERRIDE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STOP_OVERRIDE_PATH.write_text(reason or "stop", encoding="utf-8")
    except OSError as exc:
        logger.warning("[tier_framework] write_stop_override failed: %s", exc)


def clear_stop_override() -> None:
    """Remove the STOP MAX override file. No-op if absent."""
    try:
        STOP_OVERRIDE_PATH.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("[tier_framework] clear_stop_override failed: %s", exc)


def get_current_tier() -> int:
    """Resolve effective tier: STOP override wins, else env COO_APPROVAL_TIER
    (clamped to 0..3, non-int falls back to 0)."""
    if force_tier_zero():
        return 0
    raw = os.environ.get("COO_APPROVAL_TIER", "0")
    try:
        tier = int(raw)
    except (TypeError, ValueError):
        return 0
    if tier < 0:
        return 0
    if tier > 3:
        return 3
    return tier


def can_post(action_type: str, current_tier: int | None = None) -> bool:
    """Return True iff `action_type` is permitted at `current_tier`.

    `current_tier` defaults to get_current_tier() when None. Unknown action
    types are denied (closed-by-default)."""
    tier = current_tier if current_tier is not None else get_current_tier()
    if tier <= 0:
        return False
    if tier >= 1 and action_type in TIER_1_ACTIONS:
        return True
    if tier >= 2 and action_type in TIER_2_ACTIONS:
        return True
    if tier >= 3 and action_type in TIER_3_ACTIONS:
        return True
    return False
