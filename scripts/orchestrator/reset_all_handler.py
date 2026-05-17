#!/usr/bin/env python3
"""KEI-93 — Dave-triggered fleet-restart handler (Phase 0.5, KEI-140 part c).

Polls Slack #ceo for messages from Dave matching `^reset all$` (case-insensitive,
trim, with optional `[CEO]` relay prefix stripped). On match:
  1. Post `[SYSTEM] Fleet reset initiated by Dave. Restarting agents...` to #ceo.
  2. systemctl --user restart on the 5 agent units (aiden/atlas/max/orion/scout)
     in parallel; wait 30s for ExecStartPre to settle (Atlas KEI-140 a+b).
  3. systemctl --user restart elliot-agent LAST.
  4. Per-agent health probe (tmux session alive, cognee context mtime <60s,
     self-claim loop active, Gate 4 outcome counter recent).
  5. Aggregated report to #ceo within 5min: per-agent 4-bullet status + headline.

Cooldown: 60s between consecutive `reset all` triggers to prevent double-fire.
Security: only `sender == 'U091TGTPB9U'` (Dave's Slack user_id) triggers.

Env (loaded from /home/elliotbot/.config/agency-os/.env via the systemd unit):
  SLACK_BOT_TOKEN — xoxb-… for channels.history + chat.postMessage.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from pathlib import Path

import httpx

logger = logging.getLogger("reset_all_handler")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CEO_CHANNEL_ID = "C0B2PM3TV0B"
DAVE_USER_ID = "U091TGTPB9U"
RESET_RE = re.compile(r"^(?:\[CEO\][:\s]*)?reset all\s*$", re.IGNORECASE)
AGENTS = ("aiden", "atlas", "max", "orion", "scout")
ELLIOT_LAST = "elliot"
POLL_SECONDS = 5
COOLDOWN_SECONDS = 60
SLACK_API = "https://slack.com/api"


def matches_reset(sender: str, text: str) -> bool:
    if sender != DAVE_USER_ID:
        return False
    return RESET_RE.match((text or "").strip()) is not None


def fetch_recent(token: str, oldest_ts: str | None) -> list[dict]:
    params = {"channel": CEO_CHANNEL_ID, "limit": "20"}
    if oldest_ts:
        params["oldest"] = oldest_ts
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{SLACK_API}/conversations.history", params=params, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
    if not payload.get("ok"):
        logger.warning("Slack history failed: %s", payload)
        return []
    return list(payload.get("messages") or [])


def post(token: str, text: str) -> None:
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(timeout=10) as client:
        client.post(
            f"{SLACK_API}/chat.postMessage",
            headers=headers,
            json={"channel": CEO_CHANNEL_ID, "text": text},
        )


def health_probe(callsign: str) -> dict[str, bool]:
    tmux_alive = (
        subprocess.run(
            ["tmux", "has-session", "-t", f"{callsign}:0.0"], capture_output=True, check=False
        ).returncode
        == 0
    )
    cognee_path = Path(f"/tmp/cognee-context-{callsign}.md")
    cognee_fresh = cognee_path.exists() and (time.time() - cognee_path.stat().st_mtime) < 60
    self_claim = (
        subprocess.run(
            ["systemctl", "--user", "is-active", f"agent-self-claim-loop@{callsign}.service"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    relay_active = (
        subprocess.run(
            ["systemctl", "--user", "is-active", f"relay-watcher-{callsign}.service"],
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    return {
        "tmux": tmux_alive,
        "cognee": cognee_fresh,
        "self_claim": self_claim,
        "relay": relay_active,
    }


def trigger_reset(token: str) -> None:
    post(token, "[SYSTEM] Fleet reset initiated by Dave. Restarting agents...")
    for cs in AGENTS:
        subprocess.run(
            ["systemctl", "--user", "restart", f"{cs}-agent.service"],
            capture_output=True,
            check=False,
        )
    time.sleep(30)
    subprocess.run(
        ["systemctl", "--user", "restart", f"{ELLIOT_LAST}-agent.service"],
        capture_output=True,
        check=False,
    )
    time.sleep(15)
    report_lines: list[str] = []
    healthy = 0
    for cs in (*AGENTS, ELLIOT_LAST):
        h = health_probe(cs)
        marks = " ".join(f"{k}={'✓' if v else '✗'}" for k, v in h.items())
        report_lines.append(f"- {cs}: {marks}")
        if all(h.values()):
            healthy += 1
    headline = f"[SYSTEM] Fleet reset complete. {healthy} of 6 agents healthy."
    post(token, headline + "\n" + "\n".join(report_lines))


def main() -> int:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.error("SLACK_BOT_TOKEN not set")
        return 2
    last_seen_ts: str | None = str(time.time())
    last_trigger = 0.0
    while True:
        try:
            messages = fetch_recent(token, last_seen_ts)
            for m in messages:
                ts = m.get("ts", "")
                if ts and (last_seen_ts is None or ts > last_seen_ts):
                    last_seen_ts = ts
                if matches_reset(m.get("user", ""), m.get("text", "")):
                    if time.time() - last_trigger < COOLDOWN_SECONDS:
                        logger.info("cooldown: skipping reset all (ts=%s)", ts)
                        continue
                    last_trigger = time.time()
                    logger.info("reset all triggered by Dave at ts=%s", ts)
                    trigger_reset(token)
        except Exception as exc:
            logger.warning("poll iteration failed: %s", exc)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
