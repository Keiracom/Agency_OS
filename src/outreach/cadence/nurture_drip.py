"""
Contract: src/outreach/cadence/nurture_drip.py
Purpose: Cold-prospect nurture drip — monthly 1-touch cadence alternating
         Email and LinkedIn every 30 days, capped at 6 touches.
Layer:   services (stateless once store is injected)
Imports: stdlib
Consumers: src/orchestration/flows/monthly_cycle_close_flow.py post-close hook

Lifecycle:
  - Cold prospect (cycle complete, no reply, not suppressed, not converted)
    -> enqueue(prospect_id) schedules touch 1 (Email, T+30 days).
  - Each successful send advances the count. Next touch scheduled at
    T+30 from the prior send.
  - At touch 6 the drip graduates — no further touches. Entry in the
    nurture state row is marked 'exhausted'.

State table (nurture_drip_state):
  prospect_id UUID PK
  client_id UUID
  next_channel TEXT (email | linkedin)
  next_scheduled_at TIMESTAMPTZ
  touches_sent INT
  status TEXT (active | exhausted | paused)
  started_at TIMESTAMPTZ
  updated_at TIMESTAMPTZ

The drip itself does NOT dispatch touches — it writes rows into
scheduled_touches just like daily_decider. The hourly cadence flow
dispatches them as normal.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

logger = logging.getLogger(__name__)

NURTURE_INTERVAL_DAYS = 30
NURTURE_MAX_TOUCHES = 6
NURTURE_FIRST_TOUCH_OFFSET_DAYS = 30

# Alternating pattern: even touches (1, 3, 5) email; odd (2, 4, 6) linkedin.
# touches_sent 0 -> next is touch 1 -> email
# touches_sent 1 -> next is touch 2 -> linkedin
_CHANNEL_BY_TOUCH = ["email", "linkedin", "email", "linkedin", "email", "linkedin"]


class NurtureStatus(StrEnum):
    ACTIVE = "active"
    EXHAUSTED = "exhausted"
    PAUSED = "paused"


@dataclass
class NurtureState:
    prospect_id: str
    client_id: str
    next_channel: str | None
    next_scheduled_at: datetime | None
    touches_sent: int
    status: NurtureStatus
    started_at: datetime
    updated_at: datetime | None = None


@dataclass
class EnqueueResult:
    prospect_id: str
    status: NurtureStatus
    action: str  # "enqueued" | "skipped" | "exhausted" | "already-active"
    reason: str = ""
    state: NurtureState | None = None


def next_channel_for(touches_sent: int) -> str | None:
    """Return 'email' or 'linkedin' based on zero-indexed position.
    Returns None when touches_sent >= NURTURE_MAX_TOUCHES."""
    if touches_sent >= NURTURE_MAX_TOUCHES:
        return None
    return _CHANNEL_BY_TOUCH[touches_sent]


class NurtureDrip:
    """Stateless drip scheduler. Store access via injected callables.

    Required callables:
      get_prospect_status(prospect_id)
          -> {"outreach_status": str, "has_reply": bool, "has_meeting": bool}
      get_state(prospect_id) -> NurtureState | None
      upsert_state(state: NurtureState) -> None
      insert_scheduled_touch(prospect_id, client_id, channel, scheduled_at,
                             sequence_step=None) -> None
      now_fn -> Callable[[], datetime]

    NurtureDrip NEVER raises — all methods swallow exceptions and log them.
    """

    def __init__(
        self,
        get_prospect_status: Callable,
        get_state: Callable,
        upsert_state: Callable,
        insert_scheduled_touch: Callable,
        now_fn: Callable = lambda: datetime.now(UTC),
    ):
        self._get_prospect_status = get_prospect_status
        self._get_state = get_state
        self._upsert_state = upsert_state
        self._insert_scheduled_touch = insert_scheduled_touch
        self._now_fn = now_fn

    def is_eligible(self, prospect_id: str) -> tuple[bool, str]:
        """Check cold-prospect eligibility. Returns (eligible, reason)."""
        try:
            info = self._get_prospect_status(prospect_id)
        except Exception as exc:
            logger.exception(
                "nurture_drip.is_eligible: status lookup failed prospect=%s: %s", prospect_id, exc
            )
            return False, "status_lookup_error"

        status = info.get("outreach_status", "")

        if status == "suppressed":
            return False, "suppressed"
        if status != "complete":
            return False, f"not_cold (status={status})"
        if info.get("has_reply"):
            return False, "has_reply"
        if info.get("has_meeting"):
            return False, "has_meeting"

        return True, ""

    def enqueue(self, prospect_id: str, client_id: str) -> EnqueueResult:
        """Enqueue a cold prospect into the drip. Idempotent."""
        try:
            eligible, reason = self.is_eligible(prospect_id)
            if not eligible:
                return EnqueueResult(
                    prospect_id=prospect_id,
                    status=NurtureStatus.PAUSED,
                    action="skipped",
                    reason=reason,
                )

            existing = self._get_state(prospect_id)
            if existing is not None:
                if existing.status == NurtureStatus.ACTIVE:
                    return EnqueueResult(
                        prospect_id=prospect_id,
                        status=NurtureStatus.ACTIVE,
                        action="already-active",
                        state=existing,
                    )
                if existing.status == NurtureStatus.EXHAUSTED:
                    return EnqueueResult(
                        prospect_id=prospect_id,
                        status=NurtureStatus.EXHAUSTED,
                        action="exhausted",
                        state=existing,
                    )

            now = self._now_fn()
            first_touch_at = now + timedelta(days=NURTURE_FIRST_TOUCH_OFFSET_DAYS)
            state = NurtureState(
                prospect_id=prospect_id,
                client_id=client_id,
                next_channel="email",
                next_scheduled_at=first_touch_at,
                touches_sent=0,
                status=NurtureStatus.ACTIVE,
                started_at=now,
                updated_at=now,
            )
            self._upsert_state(state)
            self._insert_scheduled_touch(
                prospect_id,
                client_id,
                "email",
                first_touch_at,
                sequence_step=100,
            )
            logger.info(
                "nurture_drip.enqueue: prospect=%s enqueued touch-1 at %s",
                prospect_id,
                first_touch_at.isoformat(),
            )
            return EnqueueResult(
                prospect_id=prospect_id,
                status=NurtureStatus.ACTIVE,
                action="enqueued",
                state=state,
            )

        except Exception as exc:
            logger.exception(
                "nurture_drip.enqueue: unexpected error prospect=%s: %s", prospect_id, exc
            )
            return EnqueueResult(
                prospect_id=prospect_id,
                status=NurtureStatus.PAUSED,
                action="skipped",
                reason=f"internal_error: {exc}",
            )

    def record_send(self, prospect_id: str) -> EnqueueResult:
        """Called after a drip touch dispatches. Advances touches_sent,
        schedules the next touch if under cap, else marks exhausted."""
        try:
            state = self._get_state(prospect_id)
            if state is None:
                return EnqueueResult(
                    prospect_id=prospect_id,
                    status=NurtureStatus.PAUSED,
                    action="skipped",
                    reason="no drip state",
                )

            now = self._now_fn()
            state.touches_sent += 1
            state.updated_at = now

            if state.touches_sent >= NURTURE_MAX_TOUCHES:
                state.status = NurtureStatus.EXHAUSTED
                state.next_scheduled_at = None
                state.next_channel = None
                self._upsert_state(state)
                logger.info(
                    "nurture_drip.record_send: prospect=%s exhausted after %d touches",
                    prospect_id,
                    state.touches_sent,
                )
                return EnqueueResult(
                    prospect_id=prospect_id,
                    status=NurtureStatus.EXHAUSTED,
                    action="exhausted",
                    state=state,
                )

            next_ch = next_channel_for(state.touches_sent)
            next_at = now + timedelta(days=NURTURE_INTERVAL_DAYS)
            state.next_channel = next_ch
            state.next_scheduled_at = next_at
            self._upsert_state(state)
            self._insert_scheduled_touch(
                prospect_id,
                state.client_id,
                next_ch,
                next_at,
                sequence_step=100,
            )
            logger.info(
                "nurture_drip.record_send: prospect=%s touch=%d next=%s at %s",
                prospect_id,
                state.touches_sent,
                next_ch,
                next_at.isoformat(),
            )
            return EnqueueResult(
                prospect_id=prospect_id,
                status=NurtureStatus.ACTIVE,
                action="enqueued",
                state=state,
            )

        except Exception as exc:
            logger.exception(
                "nurture_drip.record_send: unexpected error prospect=%s: %s", prospect_id, exc
            )
            return EnqueueResult(
                prospect_id=prospect_id,
                status=NurtureStatus.PAUSED,
                action="skipped",
                reason=f"internal_error: {exc}",
            )
