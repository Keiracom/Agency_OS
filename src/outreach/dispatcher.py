"""
Contract: src/outreach/dispatcher.py
Purpose: Unified outreach dispatch pipeline — timing -> compliance -> rate -> send -> record.
Layer:   services
Imports: integrations (Salesforge, Unipile, ElevenAgents), safety (timing, compliance, rate)
Consumers: src/orchestration/flows/hourly_cadence_flow.py

Pipeline (every touch, every channel):
    1. timing_engine.check()
    2. compliance_guard.check()
    3. rate_limiter.consume()  (soft-imported — may not exist yet)
    4. dispatch to provider (Salesforge | Unipile | ElevenAgents)
    5. INSERT cis_outreach_outcomes

All provider calls are async and wrapped in try/except so a single failure
never crashes the flow. The dispatcher never raises — every outcome is
returned as a DispatchResult for the caller to record.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.config.settings import settings
from src.outreach.safety.compliance_guard import ComplianceGuard
from src.outreach.safety.timing_engine import Channel, TimingEngine

try:  # rate_limiter is ORION's work and may not be merged yet
    from src.outreach.safety.rate_limiter import RateLimiter  # type: ignore
except ImportError:  # pragma: no cover — exercised by test_dispatcher_no_rate_limiter
    RateLimiter = None  # type: ignore[assignment,misc]

try:  # send_pacer may not be merged yet in parallel branches
    from src.outreach.safety.send_pacer import SendPacer  # type: ignore
except ImportError:  # pragma: no cover
    SendPacer = None  # type: ignore[assignment,misc]

try:  # LinkedIn FSM from slice 5
    from src.outreach.safety.linkedin_account_state import (  # type: ignore
        LinkedInAccountState,
    )
except ImportError:  # pragma: no cover
    LinkedInAccountState = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_UNSET = object()  # sentinel — distinguishes "not provided" from explicit None


@dataclass
class DispatchResult:
    """Outcome of a single dispatch attempt. Never raised — always returned."""

    status: str  # sent | skipped | failed
    channel: str
    reason: str = ""
    provider: str | None = None
    provider_message_id: str | None = None
    recorded: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


class OutreachDispatcher:
    """
    Contract: src/outreach/dispatcher.py — OutreachDispatcher
    Purpose:  Run the full pre-flight -> send -> record pipeline for one touch.
    Layer:    services

    All providers and safety modules are injected so tests can mock each independently.
    """

    def __init__(
        self,
        *,
        salesforge_client: Any | None = None,
        unipile_client: Any | None = None,
        elevenagents_client: Any | None = None,
        timing_engine: TimingEngine | None = None,
        compliance_guard: ComplianceGuard | None = None,
        rate_limiter: Any = _UNSET,
        send_pacer: Any = _UNSET,
        linkedin_state: Any = _UNSET,
        db_conn: Any | None = None,
    ) -> None:
        self.salesforge = salesforge_client
        self.unipile = unipile_client
        self.elevenagents = elevenagents_client
        self.timing = timing_engine or TimingEngine()
        self.compliance = compliance_guard or ComplianceGuard()
        # None => disabled; _UNSET => auto-create if class available
        self.rate_limiter = (
            rate_limiter if rate_limiter is not _UNSET
            else (RateLimiter() if RateLimiter else None)
        )
        # send_pacer is opt-in: None (or _UNSET) => disabled; explicit instance => active
        self.send_pacer = send_pacer if send_pacer is not _UNSET else None
        # linkedin_state is opt-in: when provided, gates DM sends through FSM
        self.linkedin_state = (
            linkedin_state if linkedin_state is not _UNSET else None
        )
        self.db = db_conn

    # -- public entrypoint ---------------------------------------------------

    async def dispatch(self, touch: dict) -> DispatchResult:
        """
        Run the pipeline for a single touch.

        Expected touch dict keys:
            channel:    'email' | 'linkedin' | 'voice' | 'sms'
            prospect:   dict with email/phone/tz/has_unsubscribed
            client_id:  UUID
            lead_id:    UUID
            activity_id: UUID
            campaign_id: UUID (optional)
            content:    dict with channel-specific payload (subject/body/etc.)
        """
        # Demo-mode gate — when IS_DEMO_MODE is set process-wide we never
        # touch a real provider. Returns a 'skipped' result so the caller
        # records the touch as deliberately suppressed (not failed).
        if getattr(settings, "IS_DEMO_MODE", False):
            channel_str = (touch.get("channel") or "").lower()
            return DispatchResult(
                status="skipped", channel=channel_str,
                reason="demo_mode:no_real_send",
            )

        channel_str = (touch.get("channel") or "").lower()
        try:
            channel = Channel(channel_str)
        except ValueError:
            return DispatchResult(
                status="failed", channel=channel_str,
                reason=f"unknown channel: {channel_str!r}",
            )

        now = datetime.now(UTC)

        # 1. Timing gate ------------------------------------------------------
        timing_dec = self.timing.check(
            channel=channel,
            now=now,
            prospect_tz=(touch.get("prospect") or {}).get("tz"),
        )
        if not timing_dec.allowed:
            return DispatchResult(
                status="skipped", channel=channel_str,
                reason=f"timing:{timing_dec.reason}",
            )

        # 2. Compliance gate --------------------------------------------------
        compliance_dec = self.compliance.check(
            channel=channel,
            prospect=touch.get("prospect") or {},
            now=now,
        )
        if not compliance_dec.allowed:
            return DispatchResult(
                status="skipped", channel=channel_str,
                reason=f"compliance:{compliance_dec.reason}",
                extra={"violations": compliance_dec.violations},
            )

        # 3. Rate limit gate --------------------------------------------------
        if self.rate_limiter is not None:
            try:
                allowed = await self.rate_limiter.consume(
                    client_id=touch.get("client_id"),
                    channel=channel_str,
                )
                if not allowed:
                    return DispatchResult(
                        status="skipped", channel=channel_str,
                        reason="rate_limit:quota_exhausted",
                    )
            except Exception as exc:
                logger.warning("rate_limiter.consume raised — allowing send: %s", exc)

        # 4. Send-pacer jitter -----------------------------------------------
        if self.send_pacer is not None:
            delay = self.send_pacer.compute_delay(
                channel=channel,
                account_id=touch.get("account_id", "*"),
                last_send_at=touch.get("last_send_at"),
            )
            if delay > 0:
                await asyncio.sleep(delay)

        # 5/6. Provider dispatch ---------------------------------------------
        sender = {
            "email":    self.send_email,
            "linkedin": self.send_linkedin,
            "voice":    self.send_voice,
        }.get(channel_str)

        if sender is None:
            return DispatchResult(
                status="failed", channel=channel_str,
                reason=f"no sender for channel {channel_str}",
            )

        result = await sender(touch)

        # 7. Record outcome + pacer tick --------------------------------------
        if result.status == "sent":
            result.recorded = await self._record_outcome(touch, result, now)
            if self.send_pacer is not None:
                self.send_pacer.record_send(
                    channel=channel,
                    account_id=touch.get("account_id", "*"),
                    at=now,
                )

        return result

    # -- per-channel senders -------------------------------------------------

    async def send_email(self, touch: dict) -> DispatchResult:
        if self.salesforge is None:
            return DispatchResult(
                status="failed", channel="email",
                reason="salesforge_client not configured",
            )
        content = touch.get("content") or {}
        prospect = touch.get("prospect") or {}
        try:
            resp = await self.salesforge.send_email(
                from_email=content.get("from_email", ""),
                to_email=prospect.get("email", ""),
                subject=content.get("subject", ""),
                html_body=content.get("html_body", ""),
                text_body=content.get("text_body"),
                tags={
                    "lead_id": str(touch.get("lead_id", "")),
                    "client_id": str(touch.get("client_id", "")),
                },
            )
            return DispatchResult(
                status="sent", channel="email", provider="salesforge",
                provider_message_id=str(resp.get("message_id", "")),
                reason="ok",
            )
        except Exception as exc:
            logger.exception("salesforge.send_email failed")
            return DispatchResult(
                status="failed", channel="email", provider="salesforge",
                reason=f"provider_error:{type(exc).__name__}:{exc}",
            )

    async def send_linkedin(self, touch: dict) -> DispatchResult:
        if self.unipile is None:
            return DispatchResult(
                status="failed", channel="linkedin",
                reason="unipile_client not configured",
            )
        content = touch.get("content") or {}
        # LinkedIn connect-state gate — DM sends require accepted connection.
        # event_type='connect' bypasses the gate (connects reach 'accepted').
        if self.linkedin_state is not None:
            event_type = (content.get("event_type") or "message").lower()
            if event_type in {"message", "dm"}:
                account_id = content.get("unipile_account_id") or ""
                prospect_id = str(touch.get("prospect_id") or touch.get("lead_id") or "")
                if not self.linkedin_state.allows_dm(account_id, prospect_id):
                    return DispatchResult(
                        status="skipped", channel="linkedin",
                        reason="linkedin_gate:connect_not_accepted",
                        extra={
                            "account_id": account_id,
                            "prospect_id": prospect_id,
                            "event_type": event_type,
                        },
                    )
        try:
            resp = await self.unipile.send_message(
                account_id=content.get("unipile_account_id", ""),
                chat_id=content.get("chat_id", ""),
                text=content.get("text", ""),
            )
            return DispatchResult(
                status="sent", channel="linkedin", provider="unipile",
                provider_message_id=str(resp.get("message_id", "")),
                reason="ok",
            )
        except Exception as exc:
            logger.exception("unipile.send_message failed")
            return DispatchResult(
                status="failed", channel="linkedin", provider="unipile",
                reason=f"provider_error:{type(exc).__name__}:{exc}",
            )

    async def send_voice(self, touch: dict) -> DispatchResult:
        if self.elevenagents is None:
            return DispatchResult(
                status="failed", channel="voice",
                reason="elevenagents_client not configured",
            )
        prospect = touch.get("prospect") or {}
        content = touch.get("content") or {}
        try:
            resp = await self.elevenagents.initiate_call(
                phone=prospect.get("phone", ""),
                compiled_context=content.get("compiled_context", {}),
                lead_id=str(touch.get("lead_id", "")),
                agency_id=str(touch.get("client_id", "")),
                campaign_id=str(touch.get("campaign_id")) if touch.get("campaign_id") else None,
            )
            success = getattr(resp, "success", False)
            if not success:
                return DispatchResult(
                    status="failed", channel="voice", provider="elevenagents",
                    reason=f"provider_error:{getattr(resp, 'error', 'unknown')}",
                )
            return DispatchResult(
                status="sent", channel="voice", provider="elevenagents",
                provider_message_id=str(getattr(resp, "call_id", "")),
                reason="ok",
            )
        except Exception as exc:
            logger.exception("elevenagents.initiate_call failed")
            return DispatchResult(
                status="failed", channel="voice", provider="elevenagents",
                reason=f"provider_error:{type(exc).__name__}:{exc}",
            )

    # -- recording -----------------------------------------------------------

    async def _record_outcome(
        self, touch: dict, result: DispatchResult, sent_at: datetime,
    ) -> bool:
        """INSERT one row into cis_outreach_outcomes. Returns True on success."""
        if self.db is None:
            logger.debug("dispatcher.db not wired — skipping outcome record")
            return False
        try:
            await self.db.execute(
                """
                INSERT INTO cis_outreach_outcomes (
                    activity_id, lead_id, client_id, campaign_id,
                    channel, sequence_step, sent_at, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                touch.get("activity_id"),
                touch.get("lead_id"),
                touch.get("client_id"),
                touch.get("campaign_id"),
                result.channel,
                touch.get("sequence_step"),
                sent_at,
            )
            return True
        except Exception as exc:
            logger.exception("cis_outreach_outcomes INSERT failed: %s", exc)
            return False
