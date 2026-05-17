"""slack_notify.py (formerly tg_notify.py) — thin Slack send helper for the callback poller.

Replaces the removed Telegram API call with a subprocess call to scripts/slack_relay.py,
preserving the same tg_send() interface so all callers work without changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_RELAY = Path(__file__).resolve().parents[2] / "scripts" / "slack_relay.py"


def tg_send(text: str) -> None:
    """Send text to the #alerts Slack channel via slack_relay.py.

    Function name retained for backward compatibility with callers in
    callback_poller, auth_gate, and task_consumer.
    """
    import contextlib

    with contextlib.suppress(Exception):
        subprocess.run(
            ["python3", str(_RELAY), "-c", "alerts", text],
            check=False,
            timeout=15,
        )
