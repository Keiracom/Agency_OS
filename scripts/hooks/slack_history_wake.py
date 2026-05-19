#!/usr/bin/env python3
"""slack_history_wake.py — Fetch last N Slack #ceo messages on wake.

Per Dave directive 2026-05-19: the wake-recovery context for elliot should be
the most recent Slack #ceo conversation, not a complex pre-clear-directive
capture hook. The Slack channel IS the durable record because Dave and elliot
only talk there. So on every session start we read the last 40 messages and
write them as readable markdown for the fresh session to inject as context.

Output: /tmp/elliot-slack-history.md
Fail-open: any error logs to stderr and exits 0 (never blocks session start).
"""
from __future__ import annotations
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CHANNEL_ID = os.environ.get("SLACK_CEO_CHANNEL_ID", "C0B2PM3TV0B")
LIMIT = int(os.environ.get("SLACK_WAKE_HISTORY_LIMIT", "40"))
OUTPUT = Path(os.environ.get("SLACK_WAKE_HISTORY_PATH", "/tmp/elliot-slack-history.md"))


def main() -> int:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        sys.stderr.write("[slack_history_wake] SLACK_BOT_TOKEN unset — skipping\n")
        return 0
    url = "https://slack.com/api/conversations.history"
    data = urllib.parse.urlencode({"channel": CHANNEL_ID, "limit": LIMIT}).encode()
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        raw = urllib.request.urlopen(req, timeout=10).read()
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        sys.stderr.write(f"[slack_history_wake] fetch failed: {e}\n")
        return 0
    try:
        resp = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"[slack_history_wake] bad JSON: {e}\n")
        return 0
    if not resp.get("ok"):
        sys.stderr.write(f"[slack_history_wake] slack error: {resp.get('error','?')}\n")
        return 0
    messages = resp.get("messages", [])
    # Slack returns newest first; reverse so oldest → newest for natural reading
    messages.reverse()
    lines: list[str] = []
    lines.append(f"# Slack #ceo recent history — last {len(messages)} messages")
    lines.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}_")
    lines.append("")
    lines.append("> Per Dave directive 2026-05-19: this is the wake-recovery context for elliot.")
    lines.append("> Read here first to know what Dave most recently asked, what I last replied,")
    lines.append("> what was in-flight when this session started. Slack ceo is the only Dave-elliot")
    lines.append("> channel so this captures everything substantive.")
    lines.append("")
    for m in messages:
        ts_raw = m.get("ts", "")
        try:
            ts = datetime.fromtimestamp(float(ts_raw), timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        except (ValueError, TypeError):
            ts = ts_raw
        user = m.get("user") or m.get("bot_id") or "?"
        username = m.get("username") or ""
        sender = username or user
        text = (m.get("text") or "").strip()
        if not text:
            continue
        # Strip slack-emoji surrogates / minimal cleaning
        lines.append(f"### [{ts}] {sender}")
        lines.append("")
        lines.append(text)
        lines.append("")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines))
    sys.stderr.write(f"[slack_history_wake] wrote {len(messages)} messages → {OUTPUT}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
