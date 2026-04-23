"""
Contract: src/outreach/safety/alert_emitter.py
Purpose: Production emitter for deliverability OperatorAlerts — posts to the
         Agency OS Telegram supergroup with per-incident dedupe (same mailbox
         or LinkedIn account + same health transition should not alert twice
         within DEDUPE_WINDOW).
Layer:   3 - engines
Imports: stdlib + tg_notify helper
Consumers: DeliverabilityMonitor (as emit_operator_alert)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Callable

from src.outreach.safety.deliverability_monitor import Health, OperatorAlert

logger = logging.getLogger(__name__)

TELEGRAM_SUPERGROUP_ID = "-1003926592540"
DEDUPE_WINDOW = timedelta(hours=1)


def format_alert(alert: OperatorAlert) -> str:
    """Render an OperatorAlert into the canonical Telegram message string."""
    if alert.health == Health.PAUSED:
        if alert.mailbox_id:
            return (
                f"[DELIVERABILITY] Mailbox {alert.mailbox_id} paused 72hr "
                f"— {alert.reason} (threshold 5%)"
            )
        if alert.linkedin_account_id:
            return (
                f"[DELIVERABILITY] LinkedIn account {alert.linkedin_account_id} "
                f"paused 7d — 402/429 response"
            )

    if alert.health == Health.QUARANTINED:
        return (
            f"[DELIVERABILITY] Mailbox {alert.mailbox_id} QUARANTINED "
            f"— spam complaint {alert.reason} (threshold 0.1%)"
        )

    # HEALTHY / DEGRADED — monitor should not emit these, but be defensive
    target = alert.mailbox_id or alert.linkedin_account_id or "unknown"
    return f"[DELIVERABILITY] {target} health={alert.health.value}: {alert.reason}"


def _send_to_supergroup(text: str) -> None:
    """Post directly to the Agency OS supergroup, ignoring TELEGRAM_CHAT_ID env."""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.warning("TELEGRAM_TOKEN not set — deliverability alert suppressed")
        return
    import httpx
    httpx.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": TELEGRAM_SUPERGROUP_ID, "text": text},
        timeout=10,
    )


class TelegramAlertEmitter:
    """Callable emitter with in-memory dedupe for DeliverabilityMonitor.

    Usage:
        emitter = TelegramAlertEmitter(send_fn=tg_send)
        monitor = DeliverabilityMonitor(..., emit_operator_alert=emitter)

    Default send_fn posts to TELEGRAM_SUPERGROUP_ID, not the env TELEGRAM_CHAT_ID.
    """

    def __init__(
        self,
        send_fn: Callable[[str], None] | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        dedupe_window: timedelta = DEDUPE_WINDOW,
    ):
        self._send_fn = send_fn if send_fn is not None else _send_to_supergroup
        self._now_fn = now_fn
        self._dedupe_window = dedupe_window
        # key -> last fired datetime
        self._last_sent: dict[tuple[str | None, str], datetime] = {}

    def _dedupe_key(self, alert: OperatorAlert) -> tuple[str | None, str]:
        target = alert.mailbox_id or alert.linkedin_account_id
        return (target, alert.health.value)

    def __call__(self, alert: OperatorAlert) -> None:
        """Format + dedupe-check + send. Never raises."""
        try:
            key = self._dedupe_key(alert)
            now = self._now_fn()
            last = self._last_sent.get(key)
            if last is not None and (now - last) < self._dedupe_window:
                logger.debug("Dedupe suppressed alert for key=%s", key)
                return

            text = format_alert(alert)
            self._send_fn(text)
            self._last_sent[key] = now
        except Exception:
            logger.warning("Failed to emit deliverability alert", exc_info=True)
