#!/usr/bin/env python3
"""live_state_probe.py — Snapshot live operational state on wake.

Per Dave directive 2026-05-19: complement the Slack-history wake hook with a
small live probe. Slack tells me what we discussed; this tells me what is
actually running on the host right now — PIDs, active services, current bd
work, last commit. Two together = full wake recovery.

Output: /tmp/elliot-live-state.md
Fail-open: any error logs to stderr and exits 0.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = Path(os.environ.get("LIVE_STATE_PATH", "/tmp/elliot-live-state.md"))
BD = os.path.expanduser("~/.local/bin/bd-original")


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "") + (r.stderr or "")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return f"(err: {e})"


def background_processes() -> str:
    """Grep ps for our known long-running scripts."""
    lines = []
    out = run(["ps", "-eo", "pid,etime,pcpu,pmem,comm,args"])
    keywords = ("session_transcript_indexer", "agent_memories_indexer", "elliot_memories_indexer",
                "governance_docs_indexer", "discovery_log_indexer", "nats_to_inbox_bridge",
                "elliot_socket_listener", "elliot_inbox_watcher", "backfill", "nats sub")
    for line in out.splitlines():
        if any(kw in line for kw in keywords) and "grep" not in line:
            lines.append("  " + line.strip()[:200])
    return "\n".join(lines) if lines else "  (none matching known patterns)"


def systemd_services() -> str:
    """List active services we care about."""
    out = run(["systemctl", "--user", "list-units", "--type=service", "--state=active",
               "--no-pager", "--no-legend"])
    interesting = []
    keywords = ("indexer", "watcher", "listener", "bridge", "weaviate", "cognee", "nats", "dispatcher",
                "self-claim", "atlas", "orion", "scout", "max", "aiden", "nova")
    for line in out.splitlines():
        if any(kw in line.lower() for kw in keywords):
            interesting.append("  " + line.strip()[:200])
    return "\n".join(interesting) if interesting else "  (none matching)"


def bd_state() -> str:
    """bd ready + in_progress for elliot."""
    ready = run([BD, "ready"], timeout=10)
    inprog = run([BD, "list", "--status=in_progress", "--assignee=elliot"], timeout=10)
    return f"## bd ready\n```\n{ready[:1500]}\n```\n\n## bd in_progress (elliot)\n```\n{inprog[:1500]}\n```"


def git_state() -> str:
    """Last commit + dirty state."""
    last = run(["git", "-C", "/home/elliotbot/clawd/Agency_OS", "log", "-1", "--oneline"], timeout=5)
    status = run(["git", "-C", "/home/elliotbot/clawd/Agency_OS", "status", "--short"], timeout=5)
    return f"  last commit: {last.strip()[:200]}\n  dirty?:\n{status[:800]}"


def cursors() -> str:
    """Indexer cursor file states."""
    out_lines = []
    for p in ("/tmp/session_indexer_cursor.json",
              "/home/elliotbot/clawd/Agency_OS/.agent_memories_indexer.cursor",
              "/home/elliotbot/clawd/Agency_OS/.governance_docs_indexer.cursor"):
        path = Path(p)
        if not path.exists():
            out_lines.append(f"  {path.name}: (missing)")
            continue
        try:
            d = json.loads(path.read_text())
            if isinstance(d, dict):
                if "last_created_at" in d:
                    out_lines.append(f"  {path.name}: last_created_at={d.get('last_created_at')}")
                else:
                    out_lines.append(f"  {path.name}: {len(d)} entries tracked")
        except Exception as e:
            out_lines.append(f"  {path.name}: (parse err: {e})")
    return "\n".join(out_lines) if out_lines else "  (none)"


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Elliot live operational state",
        f"_Snapshot: {now}_",
        "",
        "> Per Dave directive 2026-05-19: read this on wake alongside the Slack-history file.",
        "> Slack tells you what was discussed; this tells you what is actually running right now.",
        "",
        "## Background processes (known patterns)",
        background_processes(),
        "",
        "## Active services (curated)",
        systemd_services(),
        "",
        "## Git state (elliot worktree)",
        git_state(),
        "",
        "## Indexer cursors",
        cursors(),
        "",
        bd_state(),
        "",
    ]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines))
    sys.stderr.write(f"[live_state_probe] wrote → {OUTPUT}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
