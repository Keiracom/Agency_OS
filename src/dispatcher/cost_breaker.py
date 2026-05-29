"""cost_breaker — fail-SAFE dispatcher circuit breaker on fleet LLM spend (Agency_OS-wdws).

The ephemeral model is per-token billing. This is the OUTER hard safety stop on
the dispatcher spawn path: before each spawn it reads the REAL accumulated fleet
spend (spend_tracker Valkey counters, $AUD cents) and, when a ceiling is crossed,
HALTs new spawns and pings #ceo.

Distinct from src/relay/budget_ceiling.BudgetCeilingGate (Agency_OS-6ah2), which is
a fail-OPEN, priority-routing budget POLICY gate. This breaker is fail-SAFE: if it
cannot read spend, it HALTs (a runaway spend leak is worse than a paused fleet).

Thresholds (Dave/Elliot spec 2026-05-29, all overridable via env):
  - daily alert  A$20  → spawn proceeds, #ceo pinged (KEIRACOM_COST_DAILY_ALERT_AUD)
  - daily halt   A$30  → HALT new spawns + #ceo (KEIRACOM_COST_DAILY_HALT_AUD)
  - monthly halt A$350 → HALT new spawns + #ceo (KEIRACOM_COST_MONTHLY_HALT_AUD); this
    is Dave's hard cap. A$30/day sustained would blow A$350/mo, so the monthly
    ceiling catches slow burn the daily tripwire misses.
(bd Agency_OS-wdws's older "A$50/mo" note is superseded by the dispatch spec.)

CEO never blocked: Dave-DM / force_override spawns BYPASS the HALT (still alerted),
mirroring BudgetCeilingGate's non-negotiable.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.dispatcher.spend_tracker import get_spend

log = logging.getLogger(__name__)

# Defaults in $AUD cents (LAW II — Australia First; spend_tracker stores cents).
DEFAULT_DAILY_ALERT_CENTS = 2000
DEFAULT_DAILY_HALT_CENTS = 3000
DEFAULT_MONTHLY_HALT_CENTS = 35000
# Operator/fleet tenant whose spend counters represent fleet spawns (Dave=tenant 1).
DEFAULT_FLEET_TENANT_ID = 1
# Min seconds between repeat #ceo pings at the same level (in-memory dedup).
NOTIFY_COOLDOWN_SECONDS = 600

# Task source that bypasses HALT — mirrors budget_ceiling.SOURCE_DAVE_DM.
SOURCE_DAVE_DM = "dave_dm"

DEFAULT_ALERTS_JSONL = Path("/tmp/keiracom_cost_breaker_alerts.jsonl")


class BreakerDecision(Enum):
    OK = "ok"  # under all ceilings
    ALERT = "alert"  # over daily alert band (or CEO bypass over ceiling) — spawn proceeds
    HALT = "halt"  # over a hard ceiling, or spend unreadable (fail-safe) — refuse spawn


# Decisions that allow the spawn to proceed.
PROCEED = frozenset({BreakerDecision.OK, BreakerDecision.ALERT})


@dataclass(frozen=True, kw_only=True)
class BreakerResult:
    decision: BreakerDecision
    daily_spend_aud: float
    monthly_spend_aud: float
    daily_alert_aud: float
    daily_halt_aud: float
    monthly_halt_aud: float
    reason: str


AlertEmitter = Callable[[dict[str, Any]], None]
SpendReader = Callable[[int, str], Awaitable[int]]  # (tenant_id, period) -> $AUD cents


class CostBreakerError(RuntimeError):
    """Raised on invalid config only — spend/alert failures fail-safe/open by design."""


def _env_cents(name: str, default_cents: int) -> int:
    """Read an env var expressed in whole $AUD, return $AUD cents; default on absent/invalid."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default_cents
    try:
        return int(round(float(raw) * 100))
    except ValueError:
        log.warning("invalid %s=%r — using default %d cents", name, raw, default_cents)
        return default_cents


def _default_alert_emitter(payload: dict[str, Any]) -> None:
    """Fallback #ceo alert sink — append-only JSONL audit trail. Production wires a
    real #ceo emitter via DI; this guarantees every firing is reviewable regardless."""
    import json

    DEFAULT_ALERTS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_ALERTS_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")


class CostBreaker:
    """Fail-SAFE pre-spawn cost circuit breaker. Call ``await check(...)`` before
    every spawn; HALT means refuse the spawn."""

    def __init__(
        self,
        *,
        fleet_tenant_id: int | None = None,
        daily_alert_cents: int | None = None,
        daily_halt_cents: int | None = None,
        monthly_halt_cents: int | None = None,
        alert_emitter: AlertEmitter | None = None,
        spend_reader: SpendReader | None = None,
        now: Callable[[], float] | None = None,
    ):
        self._fleet_tenant_id = (
            fleet_tenant_id
            if fleet_tenant_id is not None
            else int(os.environ.get("KEIRACOM_FLEET_TENANT_ID", DEFAULT_FLEET_TENANT_ID))
        )
        self._daily_alert = (
            daily_alert_cents
            if daily_alert_cents is not None
            else _env_cents("KEIRACOM_COST_DAILY_ALERT_AUD", DEFAULT_DAILY_ALERT_CENTS)
        )
        self._daily_halt = (
            daily_halt_cents
            if daily_halt_cents is not None
            else _env_cents("KEIRACOM_COST_DAILY_HALT_AUD", DEFAULT_DAILY_HALT_CENTS)
        )
        self._monthly_halt = (
            monthly_halt_cents
            if monthly_halt_cents is not None
            else _env_cents("KEIRACOM_COST_MONTHLY_HALT_AUD", DEFAULT_MONTHLY_HALT_CENTS)
        )
        if min(self._daily_alert, self._daily_halt, self._monthly_halt) <= 0:
            raise CostBreakerError("all ceilings must be > 0 cents")
        if self._daily_halt < self._daily_alert:
            raise CostBreakerError(
                f"daily_halt ({self._daily_halt}) must be >= daily_alert ({self._daily_alert})"
            )
        self._alerts = alert_emitter or _default_alert_emitter
        self._spend_reader = spend_reader or get_spend
        self._now = now or time.monotonic
        self._notified: dict[str, float] = {}

    async def spend_snapshot(self) -> dict[str, float]:
        """Expose current fleet spend in $AUD (for rehearsal cost-per-loop logging).
        Fail-open: returns -1.0 sentinels if spend is unreadable (never raises)."""
        try:
            daily = await self._spend_reader(self._fleet_tenant_id, "daily")
            monthly = await self._spend_reader(self._fleet_tenant_id, "monthly")
        except Exception:  # noqa: BLE001 — snapshot must never raise
            log.exception("cost breaker: spend_snapshot read failed")
            return {"daily_spend_aud": -1.0, "monthly_spend_aud": -1.0}
        return {"daily_spend_aud": daily / 100, "monthly_spend_aud": monthly / 100}

    async def check(self, *, source: str = "fleet", force_override: bool = False) -> BreakerResult:
        """Pre-spawn breaker. HALT = refuse spawn. Fail-SAFE: spend read error → HALT.
        Dave-DM / force_override bypass HALT (CEO never blocked) but still alert."""
        try:
            daily_cents = await self._spend_reader(self._fleet_tenant_id, "daily")
            monthly_cents = await self._spend_reader(self._fleet_tenant_id, "monthly")
        except Exception as exc:  # noqa: BLE001 — fail-SAFE
            log.exception("cost breaker: spend read failed — failing SAFE (HALT)")
            res = self._result(BreakerDecision.HALT, -1, -1, f"spend_unreadable_failsafe: {exc}")
            self._notify("halt", res)
            return res

        over_halt = daily_cents >= self._daily_halt or monthly_cents >= self._monthly_halt
        if over_halt:
            if source == SOURCE_DAVE_DM or force_override:
                res = self._result(
                    BreakerDecision.ALERT, daily_cents, monthly_cents, "over_ceiling_ceo_bypass"
                )
                self._notify("halt", res)
                return res
            res = self._result(
                BreakerDecision.HALT, daily_cents, monthly_cents, "spend ceiling exceeded — HALT"
            )
            self._notify("halt", res)
            return res

        if daily_cents >= self._daily_alert:
            res = self._result(
                BreakerDecision.ALERT, daily_cents, monthly_cents, "daily alert threshold crossed"
            )
            self._notify("alert", res)
            return res

        return self._result(BreakerDecision.OK, daily_cents, monthly_cents, "under ceilings")

    def _result(self, decision, daily_cents, monthly_cents, reason) -> BreakerResult:
        return BreakerResult(
            decision=decision,
            daily_spend_aud=daily_cents / 100,
            monthly_spend_aud=monthly_cents / 100,
            daily_alert_aud=self._daily_alert / 100,
            daily_halt_aud=self._daily_halt / 100,
            monthly_halt_aud=self._monthly_halt / 100,
            reason=reason,
        )

    def _notify(self, level: str, res: BreakerResult) -> None:
        """Ping #ceo, deduped per level by cooldown. Fail-open: an alert failure
        never changes the breaker decision."""
        now = self._now()
        last = self._notified.get(level)
        if last is not None and (now - last) < NOTIFY_COOLDOWN_SECONDS:
            return
        self._notified[level] = now
        try:
            self._alerts(
                {
                    "kind": f"cost_breaker_{level}",
                    "decision": res.decision.value,
                    "daily_spend_aud": res.daily_spend_aud,
                    "monthly_spend_aud": res.monthly_spend_aud,
                    "daily_halt_aud": res.daily_halt_aud,
                    "monthly_halt_aud": res.monthly_halt_aud,
                    "reason": res.reason,
                }
            )
        except Exception:  # noqa: BLE001 — alert emit must not block the breaker
            log.exception("cost breaker: #ceo alert emit failed (non-blocking)")
