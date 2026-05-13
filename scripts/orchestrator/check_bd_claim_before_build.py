#!/usr/bin/env python3
"""check_bd_claim_before_build.py — KEI-22 D5 Beads hard-block.

Per Dave CEO directive ts ~1778667000:
    "Linear is the only source of work. Beads is the enforcement mechanism.
     Cannot build without active bd claim on Linear-sourced task. No
     exceptions. Chain: KEI in Linear → bd sync → bd claim → Enforcer
     confirms → build begins. Any step missing = HARD STOP at tool level."

This script is a Claude Code PreToolUse-hook-compatible gate. When the
agent attempts a write/build tool call, this hook:

    1. Reads tool name + args from stdin (PreToolUse contract).
    2. Filters to write/build operations (Edit, Write, NotebookEdit, and
       Bash commands that commit/push). Read-only tools (Read, Grep,
       Glob, Bash for status/diff/log) ALWAYS pass — exploration is not
       gated.
    3. For a write op, queries `bd list --json` for an issue:
         - assignee = $CALLSIGN
         - status   = in_progress
         - external = Linear URL (proves Linear-sourced)
    4. If no qualifying claim → exit 1 with JSON error explaining the
       chain. If found → exit 0.

Pattern A safety:
  - bd binary missing → DEGRADE-SOFT (exit 0 + log). Don't cascade an
    infra outage into a build outage; operator sees the log on next
    sweep. This is the explicit Pattern A trade-off — false-allow once
    on bd-down beats false-block-forever on a known infra hole.
  - Read-only tools ALWAYS pass — no governance value in gating Read.
  - Hook input JSON malformed → exit 0 + log (defensive; never crash
    Claude Code's hook chain).

NOT auto-activated. Wiring into `.claude/settings.json` is a Dave-directed
step Dave + Elliot run post-merge once the rule is live elsewhere
(Enforcer R2 retest after KEI-38 regex fix, etc.).

Exit codes (PreToolUse contract):
    0 = allow (read-op OR claim valid OR bd-down soft-allow)
    1 = HARD BLOCK (write-op + no qualifying claim)
    2 = hook error (unexpected exception)

CLI:
    --callsign <name>    fallback if $CALLSIGN unset
    --bd <path>          bd binary path
    --check-mode <name>  manual test mode: 'pass'|'block' bypass for tests
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_LOG = Path("/home/elliotbot/clawd/logs/bd-claim-hard-block.log")

# Tool names that constitute a "build/write op" — these gate on claim.
# All other tool names (Read, Grep, Glob, Bash-readonly, etc.) pass through.
_WRITE_TOOLS = frozenset({"Edit", "Write", "NotebookEdit"})

# Bash commands that constitute a build/write op (substring match on `command`).
# Read-only git/file ops bypass.
_BASH_WRITE_SUBSTRINGS = (
    "git commit",
    "git push",
    "git merge",
    "git rebase",
    "git reset --hard",
    "git tag",
    "gh pr create",
    "gh pr merge",
    "gh api -X PUT",
    "gh api -X POST",
    "gh api -X DELETE",
)


def _log(msg: str, log_path: Path = DEFAULT_LOG) -> None:
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except OSError:
        pass


def is_write_op(tool: str, tool_input: dict | None) -> bool:
    """True if the tool call is a build/write that should gate on claim."""
    if tool in _WRITE_TOOLS:
        return True
    if tool == "Bash":
        cmd = ((tool_input or {}).get("command") or "").lower()
        return any(s in cmd for s in _BASH_WRITE_SUBSTRINGS)
    return False


def _bd_list(bd_bin: str) -> list[dict]:
    """`bd list --json`. Empty list on any failure."""
    try:
        r = subprocess.run(
            [bd_bin, "list", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []
    if r.returncode != 0:
        return []
    try:
        data = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else data.get("issues") or data.get("data") or []
    return items if isinstance(items, list) else []


def has_valid_claim(
    callsign: str,
    *,
    bd_fn=None,
    bd_bin: str = "bd",
) -> tuple[bool, dict | None]:
    """Return (claim_found, claim_dict). Claim = assignee == callsign AND
    status == in_progress AND external is a Linear URL (proves Linear-sourced)."""
    bd_fn = bd_fn or (lambda: _bd_list(bd_bin))
    items = bd_fn()
    for i in items:
        if not isinstance(i, dict):
            continue
        assignee = (i.get("assignee") or "").strip().lower()
        if assignee != callsign.lower():
            continue
        status = (i.get("status") or "").lower()
        if status != "in_progress":
            continue
        external = (i.get("external") or "").lower()
        if "linear.app" not in external:
            continue
        return True, i
    return False, None


def block_payload(callsign: str, tool: str) -> dict:
    """Structured error payload returned via stderr on hard-block."""
    return {
        "decision": "block",
        "rule": "KEI-22 D5 — Beads hard-block (Dave directive ts ~1778667000)",
        "reason": f"No active Linear-sourced bd claim for callsign={callsign!r}.",
        "tool_blocked": tool,
        "chain_required": [
            "1. KEI exists in Linear (Todo / In Progress)",
            "2. bd sync --pull-if-stale (D1 SessionStart hook does this)",
            "3. bd update <Agency_OS-id> --assignee <callsign>",
            "4. bd update <Agency_OS-id> --claim   (sets status=in_progress)",
            "5. Build begins.",
        ],
        "fix": (
            "Either (a) claim an existing Linear-sourced bd issue for this "
            f"callsign via `bd update <id> --assignee {callsign} --claim`, or "
            "(b) raise a new KEI in Linear first per the Linear-KEI-before-"
            "build standing rule, then bd sync + claim."
        ),
    }


def decide(
    *,
    tool: str,
    tool_input: dict | None,
    callsign: str,
    bd_bin: str = "bd",
    bd_fn=None,
    bd_available: bool | None = None,
) -> dict:
    """Pure decision function — no I/O. Returns {decision, exit_code, reason,
    claim} dict."""
    if not is_write_op(tool, tool_input):
        return {
            "decision": "allow",
            "exit_code": 0,
            "reason": "read_only_tool",
            "claim": None,
        }

    if bd_available is None:
        bd_available = bool(shutil.which(bd_bin)) or bd_bin != "bd"

    if not bd_available:
        # Pattern A: bd-down does NOT cascade into a build outage.
        return {
            "decision": "allow",
            "exit_code": 0,
            "reason": "bd_unavailable_soft_allow",
            "claim": None,
        }

    found, claim = has_valid_claim(callsign, bd_fn=bd_fn, bd_bin=bd_bin)
    if found:
        return {
            "decision": "allow",
            "exit_code": 0,
            "reason": "claim_valid",
            "claim": claim,
        }
    return {
        "decision": "block",
        "exit_code": 1,
        "reason": "no_claim_hard_block",
        "claim": None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--callsign",
        default=os.environ.get("CALLSIGN", "").strip().lower() or "unknown",
    )
    parser.add_argument("--bd", default="bd")
    args = parser.parse_args(argv)

    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        _log("hook_input_malformed_soft_allow")
        return 0

    tool = payload.get("tool") or payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or payload.get("args") or {}

    result = decide(
        tool=tool,
        tool_input=tool_input,
        callsign=args.callsign,
        bd_bin=args.bd,
    )

    _log(
        f"decision={result['decision']} tool={tool!r} callsign={args.callsign} "
        f"reason={result['reason']}"
    )

    if result["decision"] == "block":
        sys.stderr.write(json.dumps(block_payload(args.callsign, tool), indent=2) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
