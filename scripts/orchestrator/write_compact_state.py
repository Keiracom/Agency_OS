#!/usr/bin/env python3
"""write_compact_state.py — Continuously write Elliot's compact state summary.

Runs on a 5-min systemd timer (elliot-compact-state-writer.timer).
Output: /tmp/elliot-compact-state.md — overwritten each run.
Backup: Supabase ceo:elliot_compact_state (survives reboot).

Context-cycling watchdog reads this file to bootstrap a fresh session.
Keep it short — target ~500 words so it fits in a fresh context alongside CLAUDE.md.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
STATE_FILE = Path("/tmp/elliot-compact-state.md")

AGENTS = {
    "atlas": "atlas:0",
    "orion": "orion:0",
    "aiden": "aiden:0",
    "maxbot": "maxbot:0",
    "scout": "scout:0",
    "nova": "nova:0",
}

sys.path.insert(0, str(REPO))
from dotenv import load_dotenv
load_dotenv("/home/elliotbot/.config/agency-os/.env")


def pane_tail(target: str, lines: int = 3) -> str:
    try:
        r = subprocess.run(["tmux", "capture-pane", "-p", "-t", target],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return "UNAVAILABLE"
        tail = r.stdout.strip().split("\n")[-lines:]
        return " | ".join(l.strip() for l in tail if l.strip())
    except Exception:
        return "UNAVAILABLE"


def open_prs() -> list[str]:
    try:
        r = subprocess.run(
            ["gh", "pr", "list", "--limit", "5", "--json", "number,title,author"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO))
        if r.returncode != 0:
            return []
        return [f"#{p['number']} {p['title'][:55]}" for p in json.loads(r.stdout)]
    except Exception:
        return []


def last_directive() -> str:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return "unknown"
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{url}/rest/v1/ceo_memory?key=eq.ceo:directives.last_number&select=value",
            headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as r:
            rows = json.loads(r.read())
        return str(rows[0]["value"]) if rows else "unknown"
    except Exception:
        return "unknown"


def backup_to_supabase(content: str, ts: str) -> None:
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        return
    try:
        import urllib.request
        body = json.dumps({"key": "ceo:elliot_compact_state",
                           "value": {"content": content, "ts": ts}}).encode()
        req = urllib.request.Request(
            f"{url}/rest/v1/ceo_memory", data=body, method="POST",
            headers={"apikey": key, "Authorization": f"Bearer {key}",
                     "Content-Type": "application/json",
                     "Prefer": "resolution=merge-duplicates"})
        with urllib.request.urlopen(req, timeout=5):
            pass
    except Exception:
        pass


def main() -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    directive = last_directive()

    fleet_rows = []
    for name, pane in AGENTS.items():
        tail = pane_tail(pane)
        fleet_rows.append(f"| {name:<8} | {tail[:100]} |")

    prs = open_prs()
    pr_text = "\n".join(f"- {p}" for p in prs) if prs else "- none open"

    heartbeat = ""
    hb_path = REPO / "HEARTBEAT.md"
    if hb_path.exists():
        heartbeat = hb_path.read_text()[:800]

    content = f"""# Elliot Compact State — {ts}
**Directive counter:** {directive} | **Phase:** V2 migration — Phase 0 (verification gate) in progress

## Fleet status
| Agent | Pane tail |
|-------|-----------|
| elliot | (self — this file is my state) |
{chr(10).join(fleet_rows)}

## Open PRs
{pr_text}

## HEARTBEAT (from HEARTBEAT.md)
{heartbeat.strip() if heartbeat else "(HEARTBEAT.md not found)"}

## Resume instructions (for context-cycle restart)
1. Read IDENTITY.md and this file only — do NOT reload full history.
2. Run fleet sweep: working / correctly-waiting / finished-clear→dispatch / stuck→revive.
3. Dispatch any cleared work. Do NOT auto-authorise paid chain runs.
4. Post #ceo: "resumed at [phase/task], fleet: [one-line status]."
5. If anything needs Dave's decision → post to #ceo with the question.
"""
    STATE_FILE.write_text(content)
    backup_to_supabase(content, ts)
    print(f"compact state written: {len(content)} chars → {STATE_FILE}")


if __name__ == "__main__":
    main()
