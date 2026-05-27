"""budget_ceiling — dispatcher-level pre-spawn budget gate (Agency_OS-6ah2).

Cutover-blocker 2 / Viktor non-negotiable cutover-gate item per Dave directive
2026-05-27. Mechanical enforcement at the dispatcher pre-spawn check: when
daily fleet spend exceeds the Dave-set threshold (default 25 AUD/day), apply
the policy table below.

POLICY TABLE (per dispatch):
  1. Priority tasks → spawn, BUT log overage to alerts channel
  2. Non-priority tasks → queued to next day OR dropped with log entry
  3. Dave direct-message tasks → ALWAYS spawn on Haiku tier; NEVER block
     ("CEO never blocked" — non-negotiable)
  4. --force-spawn override → spawn with logged justification, for emergencies

CALL SITE: scripts/fleet_supervisor.py dispatcher pre-spawn (separate KEI
wires this in; this module ships the gate logic + tests).

DI: caller passes any DB cursor implementing _DBProtocol + an alerts emitter.
No asyncpg/psycopg import here — matches PR #1173/#1185/#1194 DI pattern.

ANCHORING:
  - Daily fleet budget default: 25 AUD (KEIRACOM_DAILY_FLEET_BUDGET_AUD env).
  - LAW II: 1 USD = 1.55 AUD; spend reads are AUD throughout.
  - Bounded-spawn baseline 0.79 AUD per spawn → ~31 spawns/day default budget.
  - Cutover readiness gate COST_TELEMETRY.budget_ceiling_firing (restated
    2026-05-27 outbox orion-cutover-gate-verbatim-restate-resumed).
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)

# Dave-set default threshold (overridable via env).
DEFAULT_DAILY_FLEET_BUDGET_AUD: float = 25.0

# Source-of-task constants — input to check_budget().
SOURCE_DAVE_DM: str = "dave_dm"
SOURCE_FLEET: str = "fleet"
SOURCE_AUTOMATED: str = "automated"

# Priority constants — input to check_budget().
PRIORITY_HIGH: str = "high"
PRIORITY_NORMAL: str = "normal"
PRIORITY_LOW: str = "low"

VALID_PRIORITIES: frozenset[str] = frozenset({PRIORITY_HIGH, PRIORITY_NORMAL, PRIORITY_LOW})

# Per-dispatch acceptance criterion (d): alerts channel posts on each fire.
# Fallback path lets the dispatcher emit even when Better Stack is unreachable.
DEFAULT_ALERTS_JSONL: Path = Path("/tmp/keiracom_budget_alerts.jsonl")


class BudgetDecision(Enum):
    """The verdict returned to the dispatcher pre-spawn check."""

    SPAWN_OK = "spawn_ok"
    OVERAGE_LOG_AND_SPAWN = "overage_log_and_spawn"  # priority over budget
    QUEUE_NEXT_DAY = "queue_next_day"  # non-priority over budget, deferred
    DROP_WITH_LOG = "drop_with_log"  # non-priority over budget, not deferrable
    DAVE_BYPASS = "dave_bypass"  # CEO never blocked (Haiku tier)
    FORCE_OVERRIDE = "force_override"  # --force-spawn + justification


@dataclass(frozen=True, kw_only=True)
class BudgetCheckResult:
    """Caller acts on this — decision + recommended tier + alert payload."""

    decision: BudgetDecision
    current_day_spend_aud: float
    daily_budget_aud: float
    recommended_tier: str | None = None  # e.g. "haiku" for Dave bypass
    reason: str = ""


class BudgetCeilingError(RuntimeError):
    """Raised on invalid input only — DB / alerts failures fail-open by design."""


class _DBProtocol(Protocol):
    """Subset of a DB cursor used to read fleet spend. Mirrors PR #1185 + #1194 DI."""

    def execute(self, query: str, *params: Any) -> Any: ...
    def fetchone(self) -> Any: ...


AlertEmitter = Callable[[dict[str, Any]], None]


def fleet_spend_for_day(db: _DBProtocol, day: date) -> float:
    """Read total fleet LLM spend in AUD for `day` from keiracom_tenant_metering.

    Token counts are converted to AUD via the model_cost_calibration weight
    (PR #1173 budget policy) — but for the pre-spawn check we use a simple
    heuristic: bounded-spawn baseline 0.79 AUD/spawn × request_count, then
    refined per-model at Phase 2 when provider-billing-API integration lands
    (deferred per PR #1128 §5).

    Returns 0.0 if there's no metering row for the day (fresh day, no traffic
    yet).
    """
    db.execute(
        "SELECT COALESCE(SUM(request_count), 0)::bigint AS req_count "
        "FROM public.keiracom_tenant_metering WHERE date_utc = %s",
        day,
    )
    row = db.fetchone()
    if row is None:
        return 0.0
    req_count = int(row[0] or 0)
    # Bounded-spawn baseline 0.79 AUD per spawn (anchored to the
    # cutover-readiness-gate COST_TELEMETRY criterion). When provider-billing-
    # API integration lands (PR #1128 §5 follow-up), this switches to actual
    # USD→AUD conversion via the metering pipeline cost columns.
    return float(req_count) * 0.79


def _resolve_daily_budget_aud() -> float:
    """Read KEIRACOM_DAILY_FLEET_BUDGET_AUD env var; fall back to default."""
    raw = os.environ.get("KEIRACOM_DAILY_FLEET_BUDGET_AUD")
    if raw is None or raw == "":
        return DEFAULT_DAILY_FLEET_BUDGET_AUD
    try:
        return float(raw)
    except ValueError:
        log.warning("invalid KEIRACOM_DAILY_FLEET_BUDGET_AUD=%r — using default", raw)
        return DEFAULT_DAILY_FLEET_BUDGET_AUD


def _default_jsonl_alert_emitter(payload: dict[str, Any]) -> None:
    """Fallback alerts emitter — appends JSONL to /tmp/keiracom_budget_alerts.jsonl.

    Used when caller doesn't inject a Better Stack emitter. Append-only so
    every budget firing has a reviewable audit trail even if no real alerts
    channel is wired.
    """
    DEFAULT_ALERTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_ALERTS_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


class BudgetCeilingGate:
    """Dispatcher pre-spawn budget gate.

    Caller invokes `check_budget(...)` BEFORE every spawn. The returned
    `BudgetCheckResult.decision` tells the dispatcher how to proceed.

    Fail-open by design: DB read failure or alerts emit failure → SPAWN_OK.
    Silently suppressing spawns on transient telemetry hiccups would be
    worse than letting one extra spawn through.
    """

    def __init__(
        self,
        *,
        db: _DBProtocol,
        alerts_emitter: AlertEmitter | None = None,
        daily_budget_aud: float | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ):
        self._db = db
        self._alerts = alerts_emitter or _default_jsonl_alert_emitter
        self._daily_budget = (
            daily_budget_aud if daily_budget_aud is not None else _resolve_daily_budget_aud()
        )
        if self._daily_budget <= 0:
            raise BudgetCeilingError(f"daily_budget_aud must be > 0; got {self._daily_budget}")
        self._now = now_provider or (lambda: datetime.now(UTC))

    @property
    def daily_budget_aud(self) -> float:
        return self._daily_budget

    def check_budget(
        self,
        *,
        task_priority: str,
        source: str,
        force_override: bool = False,
        force_justification: str | None = None,
        deferrable: bool = True,
    ) -> BudgetCheckResult:
        """Pre-spawn budget gate.

        Args:
            task_priority: "high" / "normal" / "low".
            source: e.g. SOURCE_DAVE_DM, SOURCE_FLEET, SOURCE_AUTOMATED.
            force_override: True when dispatcher was invoked with --force-spawn.
            force_justification: required + non-empty when force_override=True.
            deferrable: True if the task can wait until tomorrow (most automated
                tasks); False for tasks that must drop-with-log on overage.

        Returns:
            BudgetCheckResult — caller acts on the decision.
        """
        if task_priority not in VALID_PRIORITIES:
            raise BudgetCeilingError(
                f"task_priority {task_priority!r} not in {sorted(VALID_PRIORITIES)}"
            )

        # 1. --force-spawn override fires FIRST. Justification required.
        if force_override:
            if not force_justification:
                raise BudgetCeilingError(
                    "force_override=True requires non-empty force_justification"
                )
            spend = self._safe_fleet_spend()
            self._emit_alert(
                {
                    "kind": "budget_force_override",
                    "task_priority": task_priority,
                    "source": source,
                    "force_justification": force_justification,
                    "current_day_spend_aud": spend,
                    "daily_budget_aud": self._daily_budget,
                    "ts": self._now().isoformat(),
                }
            )
            return BudgetCheckResult(
                decision=BudgetDecision.FORCE_OVERRIDE,
                current_day_spend_aud=spend,
                daily_budget_aud=self._daily_budget,
                reason=f"force-spawn override: {force_justification}",
            )

        # 2. Dave bypass — CEO never blocked. Always spawn on Haiku tier.
        if source == SOURCE_DAVE_DM:
            spend = self._safe_fleet_spend()
            # We still LOG the bypass for audit, even though it always passes.
            self._emit_alert(
                {
                    "kind": "budget_dave_bypass",
                    "task_priority": task_priority,
                    "source": source,
                    "current_day_spend_aud": spend,
                    "daily_budget_aud": self._daily_budget,
                    "over_budget": spend >= self._daily_budget,
                    "ts": self._now().isoformat(),
                }
            )
            return BudgetCheckResult(
                decision=BudgetDecision.DAVE_BYPASS,
                current_day_spend_aud=spend,
                daily_budget_aud=self._daily_budget,
                recommended_tier="haiku",
                reason="CEO never blocked (Dave direct message)",
            )

        # 3. Read current-day spend; apply policy.
        spend = self._safe_fleet_spend()
        over_budget = spend >= self._daily_budget

        if not over_budget:
            return BudgetCheckResult(
                decision=BudgetDecision.SPAWN_OK,
                current_day_spend_aud=spend,
                daily_budget_aud=self._daily_budget,
                reason="under daily budget",
            )

        # Over budget — branch by priority.
        common_alert = {
            "task_priority": task_priority,
            "source": source,
            "current_day_spend_aud": spend,
            "daily_budget_aud": self._daily_budget,
            "ts": self._now().isoformat(),
        }
        if task_priority == PRIORITY_HIGH:
            self._emit_alert({**common_alert, "kind": "budget_overage_priority_spawn"})
            return BudgetCheckResult(
                decision=BudgetDecision.OVERAGE_LOG_AND_SPAWN,
                current_day_spend_aud=spend,
                daily_budget_aud=self._daily_budget,
                reason="priority task spawned despite budget overage",
            )

        # Non-priority over budget.
        if deferrable:
            self._emit_alert({**common_alert, "kind": "budget_overage_queue_next_day"})
            return BudgetCheckResult(
                decision=BudgetDecision.QUEUE_NEXT_DAY,
                current_day_spend_aud=spend,
                daily_budget_aud=self._daily_budget,
                reason="non-priority queued until next day",
            )
        self._emit_alert({**common_alert, "kind": "budget_overage_drop"})
        return BudgetCheckResult(
            decision=BudgetDecision.DROP_WITH_LOG,
            current_day_spend_aud=spend,
            daily_budget_aud=self._daily_budget,
            reason="non-priority + non-deferrable dropped on overage",
        )

    # ------------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------------

    def _safe_fleet_spend(self) -> float:
        """Read fleet spend with fail-open semantics. DB error → 0.0 (treat as
        under budget rather than blocking spawns on transient telemetry failure)."""
        try:
            today = self._now().date()
            return fleet_spend_for_day(self._db, today)
        except Exception:  # noqa: BLE001
            log.exception("budget gate: DB read failed; treating as under budget")
            return 0.0

    def _emit_alert(self, payload: dict[str, Any]) -> None:
        """Emit one alert event. Fail-open — alerts emit failure must not block
        dispatch logic."""
        try:
            self._alerts(payload)
        except Exception:  # noqa: BLE001
            log.exception("budget gate: alerts emit failed (non-blocking)")
