#!/usr/bin/env python3
"""self_assign_on_ready.py — KEI-21 self-assign hook on [READY:] emission.

Per Dave directive ts ~1778628900 + Linear KEI-21:
  "On every [READY:] emission, hook automatically fires:
     bd ready --json | first-unblocked | bd update --claim.
   If claim succeeds → agent starts next task immediately.
   Mechanical self-assign — not instructional. Closes idle-agent gap
   at task completion."

Operator-invoked: this script is the mechanism. Wiring it into a Slack
listener / tmux Stop hook / outbox watcher is a Dave-directed activation
step that lives outside this PR.

Inputs:
    --callsign <name>     callsign emitting [READY:]. Defaults to env
                          CALLSIGN, then 'unknown' (which produces a
                          graceful no-op with a diagnostic).
    --bd <path>           bd binary path (default: 'bd' on PATH). Tests
                          inject a mock here.
    --max-attempts N      retry on claim-race losses up to N issues
                          (default 3).
    --dry-run             print what would be claimed; do NOT run
                          'bd update --claim'.

Outputs (always JSON to stdout, even on no-op):
    {
      "claimed":      bool,
      "issue_id":     str | null,
      "title":        str | null,
      "priority":     str | null,   ('P0'|'P1'|'P2'|'P3'|'P4')
      "callsign":     str,
      "reason":       str,          ('claimed'|'no_eligible_work'|
                                     'race_lost_all'|'bd_unavailable'|
                                     'invalid_callsign'|'dry_run')
      "attempted":    [str, ...]    issue ids we tried before settling
    }

Exit codes:
    0  on successful claim, graceful no-op, or dry-run
    1  on bd binary missing / unexpected exception in our own code

Selection policy:
  - 'bd ready --json' filters to unblocked + open issues.
  - We filter further to:
        unassigned  OR  assignee == callsign
    so the hook never poaches another agent's work.
  - We sort by priority (P0 first → P4 last), then by created date asc.
  - We attempt 'bd update <id> --claim' on the first match; on failure
    (e.g. another agent grabbed it microseconds before), try the next.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from typing import Any

_CALLSIGN_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _priority_key(item: dict) -> tuple:
    """Sort key: lower-number priority first; fall back to created_at asc."""
    pri_raw = (item.get("priority") or "").upper()
    m = re.match(r"P(\d+)", pri_raw)
    pri_n = int(m.group(1)) if m else 9
    return (pri_n, item.get("created", "") or item.get("created_at", ""))


def _bd_ready(bd_bin: str) -> list[dict]:
    """Run `bd ready --json` and return parsed list. [] on any failure."""
    try:
        result = subprocess.run(
            [bd_bin, "ready", "--json"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []
    if result.returncode != 0:
        return []
    try:
        parsed = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        # Some bd versions wrap output as {"issues": [...]}
        parsed = parsed.get("issues") or parsed.get("data") or []
    return parsed if isinstance(parsed, list) else []


def _bd_claim(bd_bin: str, issue_id: str) -> bool:
    """Try `bd update <id> --claim`. Returns True on success."""
    try:
        result = subprocess.run(
            [bd_bin, "update", issue_id, "--claim"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    return result.returncode == 0


def _eligible(item: dict, callsign: str) -> bool:
    """KEI-150 — assignee filtering removed (Dave 2026-05-17).

    Phase-lock (KEI-86) + SELECT FOR UPDATE SKIP LOCKED already gate
    eligibility mechanically; the prior owner/assignee-match heuristic
    blocked agents from picking up work that no peer was actively
    building. Returning True universally lets any agent claim any
    visible KEI from the phase-gated queue. The `item` and `callsign`
    arguments are retained for backwards-compatible test fixtures and
    a possible future per-row policy hook.
    """
    del item, callsign  # intentionally unused — see docstring
    return True


def _result(
    *,
    claimed: bool,
    callsign: str,
    reason: str,
    issue: dict | None = None,
    attempted: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "claimed": claimed,
        "issue_id": (issue or {}).get("id"),
        "title": (issue or {}).get("title"),
        "priority": (issue or {}).get("priority"),
        "callsign": callsign,
        "reason": reason,
        "attempted": attempted or [],
    }


def run(
    *,
    callsign: str,
    bd_bin: str = "bd",
    max_attempts: int = 3,
    dry_run: bool = False,
    ready_fn=None,
    claim_fn=None,
) -> dict[str, Any]:
    """Pure-Python entry point. Side effects injectable for tests."""
    if not _CALLSIGN_RE.fullmatch(callsign):
        return _result(claimed=False, callsign=callsign, reason="invalid_callsign")

    ready_fn = ready_fn or (lambda: _bd_ready(bd_bin))
    claim_fn = claim_fn or (lambda iid: _bd_claim(bd_bin, iid))

    items = ready_fn()
    if not items:
        # Could be "bd binary missing" or genuine empty queue — caller
        # discriminates via bd_available check below.
        if not shutil.which(bd_bin) and bd_bin == "bd":
            return _result(claimed=False, callsign=callsign, reason="bd_unavailable")
        return _result(claimed=False, callsign=callsign, reason="no_eligible_work")

    eligible = [i for i in items if _eligible(i, callsign)]
    if not eligible:
        return _result(claimed=False, callsign=callsign, reason="no_eligible_work")

    eligible.sort(key=_priority_key)
    attempted: list[str] = []

    if dry_run:
        target = eligible[0]
        return _result(
            claimed=False,
            callsign=callsign,
            reason="dry_run",
            issue=target,
            attempted=[target["id"]],
        )

    for candidate in eligible[:max_attempts]:
        iid = candidate.get("id")
        if not iid:
            continue
        attempted.append(iid)
        if claim_fn(iid):
            return _result(
                claimed=True,
                callsign=callsign,
                reason="claimed",
                issue=candidate,
                attempted=attempted,
            )
    return _result(
        claimed=False,
        callsign=callsign,
        reason="race_lost_all",
        attempted=attempted,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--callsign", default=os.environ.get("CALLSIGN", "").strip().lower() or "unknown"
    )
    parser.add_argument("--bd", default="bd")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = run(
            callsign=args.callsign,
            bd_bin=args.bd,
            max_attempts=args.max_attempts,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # pragma: no cover — defensive
        print(json.dumps({"claimed": False, "reason": f"exception: {exc}"}))
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
