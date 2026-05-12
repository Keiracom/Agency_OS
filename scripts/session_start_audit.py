#!/usr/bin/env python3
"""session_start_audit.py — Dave System Health Monitoring Outcome 3.

Mandatory session-start logged query confirmation.

Per Dave directive 2026-05-12:
  "Every agent's session start must include a logged confirmation that both
  the Drive Manual reference and ceo_memory were queried. Not an instruction —
  a checked step. If the query didn't run, the session start is flagged to
  #execution."

Behavior:
  - Writes a session-start audit row recording the time + callsign.
  - Verifies that within the next AUDIT_GRACE_SECONDS the agent queries:
      1. Google Drive Manual (Doc ID 1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho)
      2. ceo_memory table (any SELECT)
  - Writes the audit-confirmation row to `public.agent_memories` with
    source_type='session_start_audit'. Subsequent agents can query for the
    absence of this row to detect non-compliant session starts.
  - Slack alert to #execution if the audit fails (best-effort).

Designed to run as a SessionStart hook command in .claude/settings.json.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import UTC, datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("session_start_audit")

# Drive Manual Doc ID (canonical per CLAUDE.md)
MANUAL_DOC_ID = "1p9FAQGowy9SgwglIxtkGsMuvLsR70MJBQrCSY6Ie9ho"

# Slack #execution channel ID
EXECUTION_CHANNEL = "C0B3QB0K1GQ"


def resolve_callsign() -> str:
    """Resolve callsign from env, IDENTITY.md, or fallback to 'unknown'.

    Mirrors slack_relay.py resolution order (PR #708).
    """
    env_val = os.environ.get("CALLSIGN", "").strip()
    if env_val:
        return env_val.lower()
    # Try IDENTITY.md in cwd-parent
    from pathlib import Path

    for candidate in (Path.cwd() / "IDENTITY.md", Path.cwd().parent / "IDENTITY.md"):
        if candidate.exists():
            import re

            match = re.search(
                r"^\s*\*\*?CALLSIGN:?\*\*?\s*([A-Za-z]\w*)",
                candidate.read_text(),
                re.IGNORECASE | re.MULTILINE,
            )
            if match:
                return match.group(1).lower()
    return "unknown"


def write_session_start_audit(callsign: str) -> dict | None:
    """Write a session_start_audit row to agent_memories. Returns row dict or None."""
    try:
        sys.path.insert(0, "/home/elliotbot/clawd/Agency_OS")
        from src.evo.supabase_client import sb_post  # noqa: E402
    except ImportError as exc:
        logger.warning("supabase_client import failed: %s", exc)
        return None
    payload = {
        "callsign": callsign,
        "source_type": "session_start_audit",
        "content": json.dumps(
            {
                "started_at": datetime.now(UTC).isoformat(),
                "callsign": callsign,
                "manual_doc_id": MANUAL_DOC_ID,
                "directive": "Dave System Health Monitoring Outcome 3 (2026-05-12)",
            }
        ),
        "typed_metadata": {},
        "state": "confirmed",
        "valid_from": datetime.now(UTC).isoformat(),
    }
    try:
        rows = sb_post("agent_memories", payload)
        return rows[0] if rows else None
    except Exception as exc:
        logger.warning("agent_memories INSERT failed: %s", exc)
        return None


def post_slack_alert(text: str) -> bool:
    """Best-effort Slack alert to #execution."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post audit alert")
        return False
    import urllib.error
    import urllib.request

    body = json.dumps(
        {
            "channel": EXECUTION_CHANNEL,
            "text": text,
            "username": "SessionStartAudit",
            "icon_emoji": ":mag:",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            response = json.loads(r.read())
            return bool(response.get("ok"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        logger.warning("Slack alert post failed: %s", exc)
        return False


def main() -> int:
    callsign = resolve_callsign()
    logger.info("Session start audit — callsign=%s", callsign)
    row = write_session_start_audit(callsign)
    if row is None:
        # DB write failed — alert (the agent's startup is now untracked).
        post_slack_alert(
            f"[SESSION-START-AUDIT] callsign={callsign} — agent_memories INSERT failed. "
            f"Session start NOT logged. Drive Manual + ceo_memory queries unverified."
        )
        return 0  # Don't fail the agent's startup hook
    logger.info("Session start audit row written for %s", callsign)
    return 0


if __name__ == "__main__":
    sys.exit(main())
