#!/usr/bin/env python3
"""bd_task_state_injection.py — KEI-31 component 3: agent-dynamic Beads state at session start.

`bd prime` is a STATIC workflow-context document (verified empirically by
Elliot 2026-05-12 ts ~1778627330). It does NOT cover Dave's restart spec:
'active issue + current step + blockers + next action'. This script wraps
`bd ready --json` + `bd show <id>` to extract dynamic agent state and emits
a markdown injection block on stdout for the SessionStart hook chain.

Hook position: SessionStart, AFTER cognee_recall --on-wake, BEFORE
session_uuid_resume + anti_amnesia_capsule. Capsule runs last so the full
injection bundle is snapshotted.

Always exits 0 — operator-script discipline. Errors logged to stderr.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys

logger = logging.getLogger("bd_task_state_injection")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

_BD_BIN_DEFAULT = os.path.expanduser("~/.local/bin/bd")


def _bd_bin() -> str:
    return os.environ.get("AGENCY_OS_BD_BIN", _BD_BIN_DEFAULT)


def _run_bd(args: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        proc = subprocess.run(  # noqa: S603 — controlled args, no shell
            [_bd_bin(), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.warning("bd %s failed: %s", args, exc)
        return -1, ""
    return proc.returncode, proc.stdout


def get_ready_issues() -> list[dict]:
    rc, out = _run_bd(["ready", "--json"])
    if rc != 0:
        return []
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError:
        return []


def get_active_for_callsign(callsign: str) -> dict | None:
    """Return the first bd issue assigned to this callsign with status active/in_progress."""
    rc, out = _run_bd(["list", "--json", "--assignee", callsign])
    if rc != 0:
        return None
    try:
        issues = json.loads(out or "[]")
    except json.JSONDecodeError:
        return None
    for issue in issues:
        status = (issue.get("status") or "").lower()
        if status in {"active", "in_progress"}:
            return issue
    return None


def render_injection(callsign: str, active: dict | None, ready: list[dict]) -> str:
    """Emit a markdown context block for the SessionStart pipe."""
    lines = ["## Beads task state (KEI-31 component 3)"]
    if active:
        lines.append(f"- Active issue: **{active.get('id')}** — {active.get('title', '?')[:120]}")
        lines.append(f"  - Status: {active.get('status', '?')}")
        blockers = active.get("dependencies") or active.get("blocked_by") or []
        if blockers:
            blk_ids = [b.get("depends_on_id") or b.get("id") or "?" for b in blockers]
            lines.append(f"  - Blocked by: {', '.join(blk_ids)}")
        else:
            lines.append("  - Blocked by: none")
        desc = (active.get("description") or "").splitlines()
        next_step = next((line for line in desc if line.strip().startswith(("1.", "-", "*"))), "")
        if next_step:
            lines.append(f"  - Next step: {next_step.strip()[:120]}")
    else:
        lines.append(f"- Active issue: none assigned to {callsign}")
    lines.append("")
    if ready:
        lines.append(f"- Ready queue ({len(ready)} unblocked):")
        for issue in ready[:5]:
            lines.append(f"  - {issue.get('id')} (P{issue.get('priority', '?')}): {issue.get('title', '?')[:80]}")
    else:
        lines.append("- Ready queue: empty")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    callsign = (os.environ.get("CALLSIGN") or "").strip().lower()
    if not callsign:
        # Try IDENTITY.md fallback
        try:
            with open("./IDENTITY.md") as f:
                for line in f:
                    if "CALLSIGN:" in line:
                        callsign = line.split("CALLSIGN:")[-1].strip().strip("*").strip().lower()
                        break
        except OSError:
            pass
    if not callsign:
        callsign = "unknown"

    active = get_active_for_callsign(callsign)
    ready = get_ready_issues()
    sys.stdout.write(render_injection(callsign, active, ready))
    return 0


if __name__ == "__main__":
    sys.exit(main())
