"""
Contract: Evaluate deliverability health per mailbox / LinkedIn account.
Purpose:  Auto-pause/quarantine based on bounce, complaint, and LinkedIn 402/429 rates.
Layer:    Outreach Safety — no DB dependency; all I/O via injected callables.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable


class Health(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"        # soft warning — approaching threshold
    PAUSED = "paused"            # auto-pause: bounce >5% over 100+ sends, 72hr
    QUARANTINED = "quarantined"  # spam complaint >0.1%, indefinite


@dataclass
class HealthDecision:
    health: Health
    reason: str
    resume_at: datetime | None = None
    stats: dict = field(default_factory=dict)


@dataclass
class OperatorAlert:
    mailbox_id: str | None
    linkedin_account_id: str | None
    health: Health
    reason: str


# Thresholds — module-level for override in tests
BOUNCE_RATE_PAUSE_THRESHOLD = 0.05        # 5%
BOUNCE_MIN_SEND_SAMPLE = 100
BOUNCE_PAUSE_DURATION = timedelta(hours=72)
SPAM_COMPLAINT_QUARANTINE = 0.001         # 0.1%
LINKEDIN_COOLDOWN = timedelta(days=7)
DEGRADED_BOUNCE_WARN = 0.03              # 3% warning before 5% pause


class DeliverabilityMonitor:
    """Evaluates deliverability health per mailbox / LinkedIn account.

    Injected callables (unit-testable without DB):
      get_mailbox_stats(mailbox_id)
          -> {"sends": int, "bounces": int, "complaints": int,
              "since": datetime, "paused_until": datetime|None}
      get_linkedin_stats(account_id)
          -> {"last_402_at": datetime|None, "last_429_at": datetime|None,
              "cooldown_until": datetime|None}
      emit_operator_alert(alert: OperatorAlert) -> None
    """

    def __init__(
        self,
        get_mailbox_stats: Callable,
        get_linkedin_stats: Callable,
        emit_operator_alert: Callable = lambda _: None,
        now_fn: Callable = lambda: datetime.utcnow(),
    ):
        self._get_mailbox_stats = get_mailbox_stats
        self._get_linkedin_stats = get_linkedin_stats
        self._emit_operator_alert = emit_operator_alert
        self._now = now_fn

    def check_mailbox(self, mailbox_id: str) -> HealthDecision:
        """Apply bounce/complaint thresholds. Emit operator alert on transitions
        into PAUSED or QUARANTINED."""
        stats = self._get_mailbox_stats(mailbox_id)
        now = self._now()

        # Honour existing pause — no stat evaluation, no re-alert
        paused_until = stats.get("paused_until")
        if paused_until and paused_until > now:
            return HealthDecision(
                health=Health.PAUSED,
                reason=f"existing pause active until {paused_until.isoformat()}",
                resume_at=paused_until,
                stats=stats,
            )

        sends = stats.get("sends", 0)
        if sends < BOUNCE_MIN_SEND_SAMPLE:
            return HealthDecision(
                health=Health.HEALTHY,
                reason=f"insufficient sample (N<{BOUNCE_MIN_SEND_SAMPLE})",
                stats=stats,
            )

        bounces = stats.get("bounces", 0)
        complaints = stats.get("complaints", 0)
        bounce_rate = bounces / sends
        complaint_rate = complaints / sends

        # QUARANTINED — highest priority
        if complaint_rate >= SPAM_COMPLAINT_QUARANTINE:
            decision = HealthDecision(
                health=Health.QUARANTINED,
                reason=f"spam complaint rate {complaint_rate:.4%} >= {SPAM_COMPLAINT_QUARANTINE:.4%}",
                resume_at=None,
                stats=stats,
            )
            self._emit_operator_alert(
                OperatorAlert(
                    mailbox_id=mailbox_id,
                    linkedin_account_id=None,
                    health=Health.QUARANTINED,
                    reason=decision.reason,
                )
            )
            return decision

        # PAUSED — bounce rate too high
        if bounce_rate >= BOUNCE_RATE_PAUSE_THRESHOLD:
            resume_at = now + BOUNCE_PAUSE_DURATION
            decision = HealthDecision(
                health=Health.PAUSED,
                reason=f"bounce rate {bounce_rate:.4%} >= {BOUNCE_RATE_PAUSE_THRESHOLD:.4%}",
                resume_at=resume_at,
                stats=stats,
            )
            self._emit_operator_alert(
                OperatorAlert(
                    mailbox_id=mailbox_id,
                    linkedin_account_id=None,
                    health=Health.PAUSED,
                    reason=decision.reason,
                )
            )
            return decision

        # DEGRADED — soft warning
        if bounce_rate >= DEGRADED_BOUNCE_WARN:
            return HealthDecision(
                health=Health.DEGRADED,
                reason=f"bounce rate {bounce_rate:.4%} >= degraded warn {DEGRADED_BOUNCE_WARN:.4%}",
                stats=stats,
            )

        return HealthDecision(
            health=Health.HEALTHY,
            reason=f"bounce rate {bounce_rate:.4%}, complaint rate {complaint_rate:.4%}",
            stats=stats,
        )

    def check_linkedin_account(self, account_id: str) -> HealthDecision:
        """Apply 402/429 cooldown window."""
        stats = self._get_linkedin_stats(account_id)
        now = self._now()

        cooldown_until = stats.get("cooldown_until")

        # Honour existing recorded cooldown — no new alert
        if cooldown_until and cooldown_until > now:
            return HealthDecision(
                health=Health.PAUSED,
                reason=f"LinkedIn cooldown active until {cooldown_until.isoformat()}",
                resume_at=cooldown_until,
                stats=stats,
            )

        last_402_at = stats.get("last_402_at")
        last_429_at = stats.get("last_429_at")
        cutoff = now - LINKEDIN_COOLDOWN

        recent_events = [
            t for t in (last_402_at, last_429_at) if t and t > cutoff
        ]

        if recent_events:
            latest = max(recent_events)
            resume_at = latest + LINKEDIN_COOLDOWN
            reason = (
                f"LinkedIn rate-limit event at {latest.isoformat()}; "
                f"cooldown until {resume_at.isoformat()}"
            )
            self._emit_operator_alert(
                OperatorAlert(
                    mailbox_id=None,
                    linkedin_account_id=account_id,
                    health=Health.PAUSED,
                    reason=reason,
                )
            )
            return HealthDecision(
                health=Health.PAUSED,
                reason=reason,
                resume_at=resume_at,
                stats=stats,
            )

        return HealthDecision(
            health=Health.HEALTHY,
            reason="no recent 402/429 events within cooldown window",
            stats=stats,
        )
