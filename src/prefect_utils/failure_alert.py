import logging
import os

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7267788033")


def send_failure_alert(
    flow_name: str,
    flow_run_id: str,
    error_message: str,
    timestamp: str,
) -> None:
    """Send a Telegram alert when a Prefect flow fails."""
    text = (
        "🚨 *Prefect Flow FAILED*\n"
        f"Flow: {flow_name}\n"
        f"Run ID: {flow_run_id}\n"
        f"Error: {error_message}\n"
        f"Time: {timestamp}"
    )
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
    }
    try:
        response = httpx.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("Failure alert sent for flow '%s'", flow_name)
    except Exception as exc:
        logger.error("Failed to send Telegram alert: %s", exc)
