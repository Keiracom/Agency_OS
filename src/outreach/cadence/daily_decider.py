"""
Contract: src/outreach/cadence/daily_decider.py
Purpose: Nightly decision loop — evaluates every active prospect and decides next action.
Layer:   services
Imports: stdlib + cadence_orchestrator + timing_engine
Consumers: src/orchestration/flows/daily_decider_flow.py

Runs once per day (scheduler at 9am AEST). For every active prospect per client,
decide one of: schedule_next | skip | suppress | escalate | nurture.

Writes one row to scheduled_touches per 'schedule_next' or 'nurture' action.
Does NOT fire touches — that's hourly_cadence_flow's job once scheduled_at <= now().
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from src.outreach.safety.timing_engine import Channel, TimingEngine
from src.pipeline.cadence_orchestrator import (
    get_channel_for_step,
    get_default_sequence,
    get_next_step,
)

logger = logging.getLogger(__name__)

MAX_STEP = max(s["step"] for s in get_default_sequence())
NURTURE_INTERVAL_DAYS = 30
OOO_RESUME_OFFSET_DAYS = 2

# Any of these response intents mean we don't schedule anything new.
# Spans both reply_router vocabulary and reply_intent taxonomy.
_SKIP_REPLIED_INTENTS = frozenset(
    {
        "positive",
        "positive_interested",
        "booked",
        "meeting_booked",
        "meeting_request",
        "booking_request",
        "question",
    }
)
_SKIP_SUPPRESSED_INTENTS = frozenset(
    {
        "unsubscribe",
        "opt_out",
        "not_interested",
        "bounce",
    }
)


@dataclass
class DeciderAction:
    """One decision per prospect. Executor writes to scheduled_touches (or no-ops)."""

    lead_id: str
    action: str  # schedule_next | skip | suppress | escalate | nurture
    channel: str | None = None
    scheduled_at: datetime | None = None
    reason: str = ""
    sequence_step: int | None = None


class DailyDecider:
    """
    Contract: src/outreach/cadence/daily_decider.py — DailyDecider
    Purpose:  Evaluate all active prospects for a client and decide next outreach action.
    Layer:    services (pure once prospects are loaded)
    """

    def __init__(self, timing: TimingEngine | None = None) -> None:
        self.timing = timing or TimingEngine()

    async def evaluate_all(self, db_conn: Any, client_id: str) -> list[DeciderAction]:
        """Return a DeciderAction per active prospect for this client."""
        if db_conn is None:
            return []
        prospects = await self._load_prospects(db_conn, client_id)
        logger.info("daily_decider: client=%s prospects=%d", client_id, len(prospects))
        return [self._decide_one(p) for p in prospects]

    # -- per-prospect decision ----------------------------------------------

    def _decide_one(self, p: dict) -> DeciderAction:
        lead_id = str(p.get("lead_id"))

        # 9. Meeting booked → skip permanently
        if p.get("meeting_booked_at"):
            return DeciderAction(
                lead_id=lead_id, action="skip", reason="meeting_booked — sequence complete"
            )

        last_intent = (p.get("last_reply_intent") or "").strip().lower() or None

        # 5 + 6. Replied (positive / question) or suppressed → skip
        if last_intent in _SKIP_SUPPRESSED_INTENTS:
            return DeciderAction(
                lead_id=lead_id, action="skip", reason=f"suppressed (intent={last_intent})"
            )
        if last_intent in _SKIP_REPLIED_INTENTS:
            return DeciderAction(
                lead_id=lead_id,
                action="skip",
                reason=f"replied (intent={last_intent}) — webhook owns",
            )

        # 7. Out-of-office → skip until return_date + 2 days
        if last_intent in {"ooo", "out_of_office"}:
            return self._handle_ooo(p, lead_id)

        total_sent = int(p.get("total_touches_sent") or 0)
        current_step = int(p.get("current_sequence_step") or 0)

        # 8. Full sequence exhausted → nurture drip
        if current_step >= MAX_STEP and total_sent >= MAX_STEP:
            return self._schedule_nurture(p, lead_id)

        # 2. First touch ever → schedule Step 1 today/tomorrow
        if total_sent == 0:
            return self._schedule_step(
                p, lead_id, step=1, delay_days=0, reason="no touches yet — scheduling step 1"
            )

        # 3 + 4. Gap since last touch governs scheduling
        next_info = get_next_step(lead_id, current_step, last_response=last_intent)
        action = next_info.get("action")

        if action == "complete":
            return self._schedule_nurture(p, lead_id)
        if action in ("pause", "suppress"):
            return DeciderAction(
                lead_id=lead_id,
                action="skip",
                reason=f"cadence_orchestrator {action}: {next_info.get('reason', '')}",
            )

        target_step = int(next_info["next_step"])
        delay_days = int(next_info["delay_days"])
        last_sent = _to_dt(p.get("last_touch_sent_at"))
        now = datetime.now(UTC)
        gap_days = (now - last_sent).days if last_sent else delay_days

        if gap_days < delay_days:
            return DeciderAction(
                lead_id=lead_id,
                action="skip",
                reason=f"too soon (gap={gap_days}d < required={delay_days}d)",
            )

        return self._schedule_step(
            p,
            lead_id,
            step=target_step,
            delay_days=0,
            reason=f"gap satisfied — scheduling step {target_step}",
        )

    # -- helpers ------------------------------------------------------------

    def _schedule_step(
        self,
        p: dict,
        lead_id: str,
        *,
        step: int,
        delay_days: int,
        reason: str,
    ) -> DeciderAction:
        channel = get_channel_for_step(
            step=step,
            has_email=bool(p.get("has_email")),
            has_phone=bool(p.get("has_phone")),
            has_linkedin=bool(p.get("has_linkedin")),
        )
        if channel is None:
            return DeciderAction(
                lead_id=lead_id, action="escalate", reason="no usable channel for prospect"
            )

        start = datetime.now(UTC) + timedelta(days=delay_days)
        scheduled_at = self._next_valid_window(channel, start, p.get("timezone"))
        return DeciderAction(
            lead_id=lead_id,
            action="schedule_next",
            channel=channel,
            scheduled_at=scheduled_at,
            sequence_step=step,
            reason=reason,
        )

    def _schedule_nurture(self, p: dict, lead_id: str) -> DeciderAction:
        channel = "email" if p.get("has_email") else None
        if channel is None:
            return DeciderAction(
                lead_id=lead_id,
                action="escalate",
                reason="sequence exhausted + no email for nurture drip",
            )
        start = datetime.now(UTC) + timedelta(days=NURTURE_INTERVAL_DAYS)
        scheduled_at = self._next_valid_window(channel, start, p.get("timezone"))
        return DeciderAction(
            lead_id=lead_id,
            action="nurture",
            channel=channel,
            scheduled_at=scheduled_at,
            reason=f"sequence exhausted — nurture drip in {NURTURE_INTERVAL_DAYS}d",
        )

    def _handle_ooo(self, p: dict, lead_id: str) -> DeciderAction:
        raw = p.get("ooo_return_date") or p.get("last_reply_extracted", {}).get("return_date")
        resume = _to_dt(raw) or (datetime.now(UTC) + timedelta(days=7))
        resume = resume + timedelta(days=OOO_RESUME_OFFSET_DAYS)
        if datetime.now(UTC) < resume:
            return DeciderAction(
                lead_id=lead_id,
                action="skip",
                reason=f"ooo — resume after {resume.date().isoformat()}",
            )
        # Past the OOO window — resume at the next step
        return self._schedule_step(
            p,
            lead_id,
            step=int(p.get("current_sequence_step") or 1),
            delay_days=0,
            reason="ooo window passed — resuming",
        )

    def _next_valid_window(
        self,
        channel: str,
        start: datetime,
        prospect_tz: str | None,
    ) -> datetime:
        """Ask timing_engine when the next allowed send window begins."""
        try:
            ch = Channel(channel)
        except ValueError:
            return start
        dec = self.timing.check(channel=ch, now=start, prospect_tz=prospect_tz)
        if dec.allowed:
            return start
        return dec.next_window_start or (start + timedelta(days=1))

    # -- DB loader (override in tests) --------------------------------------

    async def _load_prospects(self, db_conn: Any, client_id: str) -> list[dict]:
        rows = await db_conn.fetch(
            """
            SELECT lead_id, last_reply_intent, last_reply_extracted,
                   last_touch_sent_at, current_sequence_step, total_touches_sent,
                   meeting_booked_at, has_email, has_phone, has_linkedin,
                   timezone, ooo_return_date
            FROM active_prospects_view
            WHERE client_id = $1
            """,
            client_id,
        )
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Executor — turn DeciderActions into scheduled_touches INSERTs
# ---------------------------------------------------------------------------


async def apply_actions(
    db_conn: Any,
    client_id: str,
    actions: list[DeciderAction],
) -> dict[str, int]:
    """Write schedule_next + nurture actions to scheduled_touches. Never raises.

    Also updates business_universe lifecycle columns alongside each touch
    insert / suppression:
      - schedule_next | nurture  -> outreach_status pending->active (idempotent),
                                    last_outreach_at[channel] = scheduled_at,
                                    signal_snapshot_at = NOW()
      - suppress                 -> outreach_status = 'suppressed'
    BU UPDATEs are best-effort — failures are logged but do not abort the
    touch insert or bump the errors counter beyond the insert path.
    """
    counts = {
        "scheduled": 0,
        "nurture": 0,
        "skipped": 0,
        "suppressed": 0,
        "escalated": 0,
        "errors": 0,
    }
    for a in actions:
        try:
            if a.action in ("schedule_next", "nurture") and a.scheduled_at and a.channel:
                await db_conn.execute(
                    """
                    INSERT INTO scheduled_touches (
                        client_id, lead_id, channel, sequence_step,
                        scheduled_at, status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, 'pending', NOW(), NOW())
                    """,
                    client_id,
                    a.lead_id,
                    a.channel,
                    a.sequence_step or 1,
                    a.scheduled_at,
                )
                counts["scheduled" if a.action == "schedule_next" else "nurture"] += 1
                await _bu_mark_active(db_conn, a.lead_id, a.channel, a.scheduled_at)
            elif a.action == "skip":
                counts["skipped"] += 1
            elif a.action == "suppress":
                counts["suppressed"] += 1
                await _bu_mark_suppressed(db_conn, a.lead_id)
            elif a.action == "escalate":
                counts["escalated"] += 1
        except Exception as exc:
            counts["errors"] += 1
            logger.exception("apply_actions insert failed for lead=%s: %s", a.lead_id, exc)
    return counts


async def _bu_mark_active(
    db_conn: Any,
    lead_id: str,
    channel: str,
    scheduled_at: datetime,
) -> None:
    """Transition BU row to 'active' (from 'pending' only) and record last-touch
    timestamp per channel. Idempotent: repeated calls for an already-active row
    update last_outreach_at without regressing the enum."""
    try:
        await db_conn.execute(
            """
            UPDATE business_universe
            SET outreach_status = CASE
                    WHEN outreach_status = 'pending' THEN 'active'::bu_outreach_status
                    ELSE outreach_status
                END,
                last_outreach_at = COALESCE(last_outreach_at, '{}'::jsonb)
                    || jsonb_build_object($2::text, $3::timestamptz::text),
                signal_snapshot_at = NOW(),
                updated_at = NOW()
            WHERE id = $1
            """,
            lead_id,
            channel,
            scheduled_at,
        )
    except Exception as exc:
        logger.warning("bu_mark_active failed for lead=%s: %s", lead_id, exc)


async def _bu_mark_suppressed(db_conn: Any, lead_id: str) -> None:
    """Flip BU row to 'suppressed'. Terminal; does not regress from 'converted'."""
    try:
        await db_conn.execute(
            """
            UPDATE business_universe
            SET outreach_status = 'suppressed'::bu_outreach_status,
                signal_snapshot_at = NOW(),
                updated_at = NOW()
            WHERE id = $1 AND outreach_status != 'converted'
            """,
            lead_id,
        )
    except Exception as exc:
        logger.warning("bu_mark_suppressed failed for lead=%s: %s", lead_id, exc)


# ---------------------------------------------------------------------------
# Tiny helpers
# ---------------------------------------------------------------------------


def _to_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None
