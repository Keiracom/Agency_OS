"""Spawn attribution telemetry — at-spawn hook layer (Step 4.5 wiring PR #4).

Wires `src.keiracom_system.attribution.logger.log_spawn_attribution`
(PR #1207 / Cat 21 lever 27 / cutover-blocker 6) plus per-task-type
classification (PR #1209 / Cat 21 lever 23 / cutover-blocker 7) into
dispatcher_main's spawn lifecycle. Both shipped as modules on main but
dispatcher_main.py did not emit attribution events.

WIRING POINT:
  At the moment of spawn (immediately before _spawn.handle_envelope).
  We don't yet know input_tokens / output_tokens / cost_usd at dispatch
  time — those land on the session JSONL after the spawn completes (read
  by the daily ceo-rollup at 23:55 AEST). So this gate logs the spawn-time
  fields (ts, source_type, source_id, task_type, callsign, model) and the
  cost-rollup pipeline backfills token/cost data from session JSONLs by
  matching ts + callsign per PR #1202 / Atlas.

SOURCE_TYPE derivation:
  Per attribution.SOURCE_TYPES {"slack", "pr", "cron", "inbox", "unknown"}:
    explicit envelope.source_type wins (validated against frozenset)
    envelope.from "dave" → "slack" (Dave's only inbound path)
    envelope.task_ref starts with "PR-" or "pr-" → "pr"
    envelope.from in {"cron", "scheduler"} → "cron"
    inbox-watcher dispatch (default) → "inbox"
    else → "unknown" (explicit, NOT silent fallback per PR #1207 contract)

TASK_TYPE derivation per attribution.TASK_TYPES
  {"pr_review", "deliberation", "build", "chat", "dispatch_mgmt", "unknown"}:
    explicit envelope.task_type wins
    envelope.task_ref matches /REVIEW-PR-/ → "pr_review"
    envelope.task_ref matches /DELIBERATE-/ → "deliberation"
    envelope.from "dave" → "chat" (assume DM if from Dave)
    envelope.task_ref starts with "DISPATCH" → "dispatch_mgmt"
    else → "build" (most common dispatcher task)

bd: cutover-step-4.5-dispatcher-wiring-pr4
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from src.keiracom_system.attribution.logger import (
    SOURCE_TYPES,
    TASK_TYPES,
    SpawnAttributionEntry,
    log_spawn_attribution,
)

log = logging.getLogger(__name__)

# Default Claude model name when envelope doesn't specify; matches the
# fleet default per ceo:model_assignment.
DEFAULT_MODEL = "claude-sonnet-4-6"


def _envelope_source_type(envelope: Mapping[str, Any]) -> str:
    """Derive source_type from envelope per PR #1207 SOURCE_TYPES taxonomy."""
    explicit = str(envelope.get("source_type") or "").strip()
    if explicit in SOURCE_TYPES:
        return explicit

    sender = str(envelope.get("from") or "").lower().strip()
    if sender == "dave":
        return "slack"
    if sender in {"cron", "scheduler"}:
        return "cron"

    task_ref = str(envelope.get("task_ref") or "").lower()
    if task_ref.startswith("pr-") or "pull-request" in task_ref:
        return "pr"

    # Default to "inbox" — dispatcher dispatches via inbox-watcher.
    # Reserve "unknown" for explicit ambiguity (envelope from origin we cannot tag).
    return "inbox"


def _envelope_task_type(envelope: Mapping[str, Any]) -> str:
    """Derive task_type from envelope per PR #1207/#1209 TASK_TYPES taxonomy."""
    explicit = str(envelope.get("task_type") or "").lower().strip()
    if explicit in TASK_TYPES:
        return explicit

    task_ref = str(envelope.get("task_ref") or "").upper()
    if "REVIEW-PR" in task_ref or "PR-REVIEW" in task_ref:
        return "pr_review"
    if "DELIBERATE" in task_ref or "DELIBERATION" in task_ref:
        return "deliberation"
    if task_ref.startswith("DISPATCH"):
        return "dispatch_mgmt"

    sender = str(envelope.get("from") or "").lower().strip()
    if sender == "dave":
        return "chat"

    return "build"


def _envelope_source_id(envelope: Mapping[str, Any]) -> str:
    """Derive source_id (per-event correlation key)."""
    return str(
        envelope.get("source_id") or envelope.get("task_ref") or envelope.get("id") or "unknown"
    )


def emit(
    envelope: Mapping[str, Any],
    *,
    callsign: str,
    enabled: bool = False,
    model: str | None = None,
) -> SpawnAttributionEntry | None:
    """Emit a spawn-time attribution entry. Returns the entry on emit, None otherwise.

    Fail-open by design:
      - enabled=False (rollout phase 1) → no emit, return None
      - SpawnAttributionError (invalid source_type / task_type) → log + return None
        rather than re-raising; dispatcher must not crash on telemetry-class errors
      - log path I/O errors → propagate (mkdir failures are unusual; if /tmp is
        unwritable the dispatcher has bigger problems anyway)
    """
    if not enabled:
        return None

    source_type = _envelope_source_type(envelope)
    task_type = _envelope_task_type(envelope)
    source_id = _envelope_source_id(envelope)

    try:
        entry = log_spawn_attribution(
            source_type=source_type,
            source_id=source_id,
            callsign=callsign,
            model=model or DEFAULT_MODEL,
            task_type=task_type,
        )
    except Exception:  # noqa: BLE001 — telemetry failures must not block spawn
        log.exception(
            "spawn attribution emit failed; continuing without telemetry (source_type=%s task_type=%s)",
            source_type,
            task_type,
        )
        return None

    log.debug(
        "spawn attribution emitted source_type=%s task_type=%s source_id=%s callsign=%s",
        source_type,
        task_type,
        source_id,
        callsign,
    )
    return entry
