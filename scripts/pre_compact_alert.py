#!/usr/bin/env python3
"""pre_compact_alert.py — Claude Code PreCompact hook → Slack alert.

Per Dave System Health Monitoring directive 2026-05-12 Outcome 5:
  "Pre-compaction alert at 70% + HEARTBEAT.md template stub."

When Claude Code is about to auto-compact context (≈95% threshold internally;
the directive's "70%" is the *self-alert target* in CLAUDE.md, not a value
this hook can observe), this script fires once. It dumps:

  - callsign + UTC timestamp
  - HEARTBEAT.md snapshot (agent-maintained state)
  - last 3 git commits in the worktree
  - branch name + clean/dirty status

…to #execution. Best-effort: failures DO NOT block compaction. Compaction
proceeds either way; the alert is observability, not a gate.

Wired in .claude/settings.json under "PreCompact" matcher.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pre_compact_alert")

EXECUTION_CHANNEL = "C0B3QB0K1GQ"
HEARTBEAT_PATH = Path("HEARTBEAT.md")


def resolve_callsign() -> str:
    """env → IDENTITY.md → 'unknown' (mirrors session_start_audit.py)."""
    env_val = os.environ.get("CALLSIGN", "").strip()
    if env_val:
        return env_val.lower()
    import re

    for candidate in (Path.cwd() / "IDENTITY.md", Path.cwd().parent / "IDENTITY.md"):
        if candidate.exists():
            match = re.search(
                r"^\s*\*\*?CALLSIGN:?\*\*?\s*([A-Za-z]\w*)",
                candidate.read_text(),
                re.IGNORECASE | re.MULTILINE,
            )
            if match:
                return match.group(1).lower()
    return "unknown"


def read_heartbeat() -> str:
    """Read HEARTBEAT.md from worktree root. '' if missing."""
    if HEARTBEAT_PATH.exists():
        try:
            text = HEARTBEAT_PATH.read_text()
            # Cap to 2000 chars to keep Slack message bounded
            return text[:2000]
        except OSError as exc:
            logger.warning("HEARTBEAT.md read failed: %s", exc)
    return ""


def _run(args: list[str]) -> str:
    """Run a git command, return stdout stripped. '' on failure."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        logger.warning("git command %s failed: %s", args, exc)
        return ""


def git_context() -> dict:
    """Branch + last 3 commits + dirty/clean."""
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    log = _run(["git", "log", "--oneline", "-3"])
    porcelain = _run(["git", "status", "--porcelain"])
    return {
        "branch": branch or "?",
        "log": log or "(no commits)",
        "dirty": bool(porcelain),
        "porcelain": porcelain[:500],
    }


def format_alert(callsign: str, hook_input: dict, heartbeat: str, git: dict) -> str:
    when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    trigger = hook_input.get("trigger", "unknown")
    heartbeat_block = heartbeat.strip() or "(HEARTBEAT.md empty or missing)"
    dirty_marker = " [DIRTY]" if git["dirty"] else ""
    return (
        f"[PRE-COMPACT] callsign={callsign} branch={git['branch']}{dirty_marker} "
        f"trigger={trigger} when={when}\n"
        f"HEARTBEAT:\n```\n{heartbeat_block}\n```\n"
        f"Recent commits:\n```\n{git['log']}\n```"
    )


def post_to_slack(text: str, channel: str = EXECUTION_CHANNEL) -> bool:
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — cannot post pre-compact alert")
        return False
    import urllib.error
    import urllib.request

    body = json.dumps(
        {
            "channel": channel,
            "text": text,
            "username": "PreCompact",
            "icon_emoji": ":card_index_dividers:",
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


def read_hook_input() -> dict:
    """Read JSON hook input from stdin. {} if stdin empty / invalid."""
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        logger.warning("PreCompact hook input not JSON: %s", exc)
        return {}


def main() -> int:
    hook_input = read_hook_input()
    callsign = resolve_callsign()
    heartbeat = read_heartbeat()
    git = git_context()
    text = format_alert(callsign, hook_input, heartbeat, git)
    posted = post_to_slack(text)
    logger.info(
        "PreCompact alert: callsign=%s branch=%s posted=%s",
        callsign,
        git["branch"],
        posted,
    )
    return 0  # Best-effort: never block compaction


if __name__ == "__main__":
    sys.exit(main())
