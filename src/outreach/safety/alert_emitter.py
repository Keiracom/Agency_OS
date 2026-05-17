"""
Contract: src/outreach/safety/alert_emitter.py
Purpose: Production emitter for deliverability OperatorAlerts — posts to the
         Agency OS #alerts Slack channel with per-incident dedupe (same mailbox
         or LinkedIn account + same health transition should not alert twice
         within DEDUPE_WINDOW).
Layer:   3 - engines
Imports: stdlib + subprocess (slack_relay shim)
Consumers: DeliverabilityMonitor (as emit_operator_alert)

KEI-41 Phase 3: Telegram API removed. Now routes via scripts/slack_relay.py.
TelegramAlertEmitter alias retained for backward compatibility.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.outreach.safety.deliverability_monitor import Health, OperatorAlert

logger = logging.getLogger(__name__)

_RELAY = Path(__file__).resolve().parents[3] / "scripts" / "slack_relay.py"
DEDUPE_WINDOW = timedelta(hours=1)


def format_alert(alert: OperatorAlert) -> str:
    """Render an OperatorAlert into the canonical alert message string."""
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


def _send_to_alerts_channel(text: str) -> None:
    """Post to the Agency OS #alerts Slack channel via slack_relay.py."""
    with contextlib.suppress(Exception):
        subprocess.run(
            ["python3", str(_RELAY), "-c", "alerts", text],
            check=False,
            timeout=15,
        )


class SlackAlertEmitter:
    """Callable emitter with in-memory dedupe for DeliverabilityMonitor.

    Usage:
        emitter = SlackAlertEmitter()
        monitor = DeliverabilityMonitor(..., emit_operator_alert=emitter)

    Default send_fn posts to #alerts channel via slack_relay.py.
    """

    def __init__(
        self,
        send_fn: Callable[[str], None] | None = None,
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
        dedupe_window: timedelta = DEDUPE_WINDOW,
    ):
        self._send_fn = send_fn if send_fn is not None else _send_to_alerts_channel
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


# Backward-compatibility alias — callers importing TelegramAlertEmitter continue to work.
TelegramAlertEmitter = SlackAlertEmitter
