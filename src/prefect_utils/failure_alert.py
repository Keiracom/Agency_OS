from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_RELAY = Path(__file__).resolve().parents[2] / "scripts" / "slack_relay.py"


def send_failure_alert(
    flow_name: str,
    flow_run_id: str,
    error_message: str,
    timestamp: str,
) -> None:
    """Send a Slack alert when a Prefect flow fails.

    Routes via scripts/slack_relay.py to #alerts channel.
    Formerly posted to Telegram API — removed in KEI-41 Phase 3.
    """
    text = (
        "[PREFECT FAILURE] "
        f"Flow: {flow_name} | "
        f"Run ID: {flow_run_id} | "
        f"Error: {error_message} | "
        f"Time: {timestamp}"
    )
    try:
        subprocess.run(
            ["python3", str(_RELAY), "-c", "alerts", text],
            check=False,
            timeout=15,
        )
        logger.info("Failure alert sent for flow '%s'", flow_name)
    except Exception as exc:
        logger.error("Failed to send Slack failure alert: %s", exc)
