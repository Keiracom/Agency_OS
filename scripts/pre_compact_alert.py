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
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pre_compact_alert")

EXECUTION_CHANNEL = "C0B3QB0K1GQ"
HEARTBEAT_PATH = Path("HEARTBEAT.md")

# KEI-36 — placeholder text → auto-populate source. Each key is the literal
# `<...>` placeholder as it appears in HEARTBEAT.md; value comes from
# auto_populate_heartbeat() arguments.
_PLACEHOLDER_PATTERN = re.compile(r"<[^>\n]+>")

# KEI-53 — fallback callsign → model map used only when agent_profiles
# Supabase read fails (network down, RLS blocked, etc). Primary source of
# truth is public.agent_profiles.configured_model (migration
# 20260514_kei53_agent_profiles.sql). Values stay in lockstep with seed.
_CONFIGURED_MODEL_FALLBACK = {
    "aiden": "claude-opus-4-7",
    "max": "claude-opus-4-7",
    "elliot": "claude-opus-4-7",
    "atlas": "claude-sonnet-4-6",
    "orion": "claude-sonnet-4-6",
    "scout": "claude-sonnet-4-6",
}

# KEI-53 — Supabase PostgREST endpoint for agent_profiles reads. Public
# anon-readable per migration; we only SELECT, never write here.
_SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jatzvazlbusedwsnqxzr.supabase.co").rstrip(
    "/"
)
_SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Placeholders that are intentional agent-fill (no mechanical source). The
# residual-detector skips lines containing these so [HEARTBEAT-INCOMPLETE]
# doesn't fire on fields the auto-populate isn't expected to handle.
_AGENT_FILL_PLACEHOLDERS = frozenset(
    {
        "<one-line>",
        "<scope/decompose/execute/verify/report>",
    }
)


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


def _bd_ready_first() -> str:
    """KEI-36 — first ready issue from `bd ready --json`. '' on any failure."""
    try:
        result = subprocess.run(  # noqa: S603
            ["bd", "ready", "--json"], capture_output=True, text=True, timeout=10, check=False
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ""
    if not isinstance(rows, list) or not rows:
        return ""
    first = rows[0]
    if not isinstance(first, dict):
        return ""
    ident = first.get("id") or first.get("Identifier") or ""
    title = first.get("title") or first.get("Title") or ""
    return f"{ident}: {title}".strip(": ").strip() or ""


def _bd_blocked_list() -> str:
    """KEI-36 — blockers from `bd list --status=blocked --json`. 'none' if empty."""
    try:
        result = subprocess.run(  # noqa: S603
            ["bd", "list", "--status=blocked", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    try:
        rows = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ""
    if not isinstance(rows, list) or not rows:
        return "none"
    bullets = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        ident = r.get("id") or ""
        title = r.get("title") or ""
        if ident or title:
            bullets.append(f"{ident}: {title}".strip(": ").strip())
    return "; ".join(bullets) if bullets else "none"


def _git_files_touched(branch: str) -> str:
    """KEI-36 — files changed on current branch vs origin/main. '' on failure."""
    if not branch or branch == "main":
        return ""
    out = _run(["git", "diff", "--name-only", "origin/main...HEAD"])
    if not out:
        return ""
    files = [line for line in out.splitlines() if line.strip()]
    if not files:
        return ""
    return ", ".join(files[:10]) + (f" (+{len(files) - 10} more)" if len(files) > 10 else "")


def _git_short_sha() -> str:
    return _run(["git", "rev-parse", "--short", "HEAD"])


def _git_commit_subject() -> str:
    return _run(["git", "log", "-1", "--pretty=%s"])


def _configured_model_for_callsign(callsign: str) -> str:
    """KEI-53 — look up configured model from public.agent_profiles.

    Primary path: SELECT configured_model FROM public.agent_profiles
    WHERE callsign=$1 via Supabase PostgREST. Times out at 3s.
    Fallback path: _CONFIGURED_MODEL_FALLBACK map (kept in lockstep with
    migration seed). Returns '' if callsign unknown and Supabase down.
    """
    cs = callsign.lower()
    if _SUPABASE_ANON_KEY:
        try:
            import urllib.error
            import urllib.parse
            import urllib.request

            qs = urllib.parse.urlencode({"callsign": f"eq.{cs}", "select": "configured_model"})
            req = urllib.request.Request(
                f"{_SUPABASE_URL}/rest/v1/agent_profiles?{qs}",
                headers={
                    "apikey": _SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {_SUPABASE_ANON_KEY}",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=3) as r:
                rows = json.loads(r.read())
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                model = rows[0].get("configured_model")
                if isinstance(model, str) and model:
                    return model
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            # urllib.error.URLError is an OSError subclass — kept implicit per Sonar S5713.
            logger.warning("agent_profiles lookup for %s failed (%s); using fallback map", cs, exc)
    return _CONFIGURED_MODEL_FALLBACK.get(cs, "")


def _running_model() -> str:
    """KEI-36 follow-up — actual --model the process is running.

    Reads CLAUDE_MODEL env var (set by tmux session launch script if known).
    Falls back to 'unknown — check tmux session launch command' which matches
    the HEARTBEAT.md template's documented fallback.
    """
    val = os.environ.get("CLAUDE_MODEL", "").strip()
    if val:
        return val
    return "unknown — check tmux session launch command"


def _directive_from_branch(branch: str) -> str:
    """KEI-36 — extract directive label from branch name like 'aiden/kei36-...'."""
    if not branch or branch == "main":
        return ""
    m = re.search(
        r"(kei[\s\-_]*\d+|directive[\s\-_]*\d+|agency_os[\s\-_]*\w+)", branch, re.IGNORECASE
    )
    return m.group(1).upper().replace("-", "-") if m else ""


def auto_populate_heartbeat(
    text: str,
    *,
    git_short_sha: str,
    branch: str,
    commit_subject: str,
    files_touched: str,
    directive: str,
    blockers: str,
    next_action: str,
    configured_model: str = "",
    running_model: str = "",
) -> str:
    """KEI-36 — fill HEARTBEAT.md placeholder fields from mechanical sources.

    Empty-string args are skipped (placeholder preserved → triggers
    [HEARTBEAT-INCOMPLETE] warning downstream UNLESS the placeholder is in
    _AGENT_FILL_PLACEHOLDERS). Phase + Goal stay as agent-fill; Model fields
    now auto-populate from callsign map + CLAUDE_MODEL env (KEI-36 follow-up).
    """
    long_configured = (
        "<callsign-from-IDENTITY.md → lookup in ceo_memory key "
        "`orchestration:model_assignment` (SQL-anchored Elliot UPSERT "
        "2026-05-12 22:45:30 UTC)>"
    )
    long_running = (
        "<actual `--model` flag at startup, if known; otherwise "
        '"unknown — check tmux session launch command">'
    )
    replacements = {
        "<git short-sha>": git_short_sha,
        "<branch-name>": branch,
        "<commit subject line>": commit_subject,
        "<list>": files_touched,
        "<directive number or label>": directive,
        '<bulleted list, or "none">': blockers,
        "<single concrete next step the next session should execute>": next_action,
        long_configured: configured_model,
        long_running: running_model,
    }
    for placeholder, value in replacements.items():
        if value:
            text = text.replace(placeholder, value, 1)
    return text


def find_residual_placeholders(text: str) -> list[str]:
    """KEI-36 — return list of `<...>` strings still in the text.

    Excludes literal-template fences inside heading-cadence section (lines
    starting with '- 40%' / '- 50%' etc.) so 'if >60%' references aren't
    counted as placeholders.
    """
    found: list[str] = []
    in_skip_block = False
    for line in text.splitlines():
        if line.startswith("## Heartbeat Cadence"):
            in_skip_block = True
            continue
        if line.startswith("## "):
            in_skip_block = False
        if in_skip_block:
            continue
        for match in _PLACEHOLDER_PATTERN.findall(line):
            # KEI-36 follow-up — skip intentional agent-fill placeholders so
            # [HEARTBEAT-INCOMPLETE] doesn't fire on Phase/Goal fields the
            # auto-populate isn't expected to handle mechanically.
            if match not in _AGENT_FILL_PLACEHOLDERS:
                found.append(match)
    return found


def post_heartbeat_incomplete_warning(
    residual: list[str], channel: str = EXECUTION_CHANNEL
) -> bool:
    """KEI-36 — post [HEARTBEAT-INCOMPLETE] listing residual placeholders."""
    if not residual:
        return False
    fields = ", ".join(sorted(set(residual)))
    text = f"[HEARTBEAT-INCOMPLETE] residual placeholders pre-snapshot: {fields}"
    return post_to_slack(text, channel=channel)


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
    git = git_context()
    # KEI-36 — auto-populate HEARTBEAT.md placeholders BEFORE snapshotting.
    if HEARTBEAT_PATH.exists():
        try:
            raw = HEARTBEAT_PATH.read_text()
            populated = auto_populate_heartbeat(
                raw,
                git_short_sha=_git_short_sha(),
                branch=git["branch"] if git["branch"] != "?" else "",
                commit_subject=_git_commit_subject(),
                files_touched=_git_files_touched(git["branch"]),
                directive=_directive_from_branch(git["branch"]),
                blockers=_bd_blocked_list(),
                next_action=_bd_ready_first(),
                configured_model=_configured_model_for_callsign(callsign),
                running_model=_running_model(),
            )
            if populated != raw:
                HEARTBEAT_PATH.write_text(populated)
            residual = find_residual_placeholders(populated)
            if residual:
                post_heartbeat_incomplete_warning(residual)
        except OSError as exc:
            logger.warning("HEARTBEAT auto-populate failed: %s", exc)
    heartbeat = read_heartbeat()
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
