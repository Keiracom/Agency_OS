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
      "claimed":            bool,
      "issue_id":           str | null,
      "title":              str | null,
      "priority":           str | null,   ('P0'|'P1'|'P2'|'P3'|'P4')
      "callsign":           str,
      "reason":             str,          ('claimed'|'no_eligible_work'|
                                           'race_lost_all'|'all_pr_merged'|
                                           'bd_unavailable'|
                                           'invalid_callsign'|'dry_run')
      "attempted":          [str, ...]    issue ids we tried before settling
      "skipped_pr_merged":  [str, ...]    issue ids closed because their
                                          linked GH PR was already merged
                                          on origin/main (Agency_OS-y2al)
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
  - Agency_OS-y2al pre-check: for each candidate in priority order, scan its
    metadata for a GitHub PR ref (full URL or `gh-NNNN`); if `gh pr view`
    reports the PR is MERGED on origin/main, CLOSE the issue and skip — no
    brief, no claim, no agent context spent. Merged-skips do NOT consume the
    max_attempts (claim-race) budget.
  - We attempt 'bd update <id> --claim' on the next remaining candidate; on
    failure (another agent grabbed it microseconds before), try the next.
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

# Agency_OS-y2al — skip dispatch + close any KEI whose linked GitHub PR is
# already merged on origin/main. Five+ stale dispatches in one V1 session
# (each consuming an agent context to pre-flight and report no-op) make this
# a real bug. The regex matches either a full PR URL or the `gh-NNNN` shortform
# used in bd --external-ref.
_GH_PR_RE = re.compile(
    r"github\.com/[\w.-]+/[\w.-]+/pull/(\d+)|\bgh-(\d+)\b",
    re.IGNORECASE,
)
# Fields on a bd ready item where a PR reference may surface.
_PR_REF_FIELDS = ("external_ref", "title", "description", "notes")


def _priority_key(item: dict) -> tuple:
    """Sort key: lower-number priority first; fall back to created_at asc.

    bd ready --json now returns priority as int (1/2/3/4) post-KEI-22 SSOT
    migration. Coerce to str before .upper() so the old 'P\\d+' regex still
    matches both int + 'P1' string shapes — int '1' becomes '1', regex misses,
    fall-through to pri_n=9 (lowest precedence). Then re-handle int directly.
    """
    raw = item.get("priority")
    if isinstance(raw, int):
        return (raw, item.get("created", "") or item.get("created_at", ""))
    pri_raw = str(raw or "").upper()
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


def _extract_pr_number(item: dict) -> int | None:
    """Find a GitHub PR number referenced in an issue's metadata, or None.

    Scans external_ref + title + description + notes for either a full PR URL
    (github.com/<owner>/<repo>/pull/<N>) or the `gh-<N>` shortform commonly
    used in bd --external-ref. Returns the FIRST match found. Linear-only
    external_refs (no embedded GH URL) return None — those skip the merged
    check and proceed to claim normally.
    """
    for field in _PR_REF_FIELDS:
        text = str(item.get(field) or "")
        if not text:
            continue
        m = _GH_PR_RE.search(text)
        if m:
            return int(m.group(1) or m.group(2))
    return None


def _gh_pr_merged_on_main(pr_number: int) -> bool:
    """`gh pr view <N> --json state,baseRefName` → MERGED on `main`. Fail-closed.

    Fail-closed (False on any error or missing `gh`) — better to keep a dispatch
    open than to close-out an issue we can't verify is actually merged.
    """
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(pr_number), "--json", "state,baseRefName"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    if result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return False
    return data.get("state") == "MERGED" and data.get("baseRefName") == "main"


def _bd_close(bd_bin: str, issue_id: str, reason: str) -> bool:
    """`bd close <id> --reason "..."`. Returns True on success."""
    try:
        result = subprocess.run(
            [bd_bin, "close", issue_id, "--reason", reason],
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
    skipped_pr_merged: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "claimed": claimed,
        "issue_id": (issue or {}).get("id"),
        "title": (issue or {}).get("title"),
        "priority": (issue or {}).get("priority"),
        "callsign": callsign,
        "reason": reason,
        "attempted": attempted or [],
        "skipped_pr_merged": skipped_pr_merged or [],
    }


def run(
    *,
    callsign: str,
    bd_bin: str = "bd",
    max_attempts: int = 3,
    dry_run: bool = False,
    ready_fn=None,
    claim_fn=None,
    pr_merged_fn=None,
    close_fn=None,
) -> dict[str, Any]:
    """Pure-Python entry point. Side effects injectable for tests.

    `pr_merged_fn(pr_number) -> bool` and `close_fn(issue_id, reason) -> bool`
    are the Agency_OS-y2al seams — when a candidate's linked PR is already
    merged on origin/main, the issue is closed and skipped (no brief, no claim).
    """
    if not _CALLSIGN_RE.fullmatch(callsign):
        return _result(claimed=False, callsign=callsign, reason="invalid_callsign")

    # Capture injection state BEFORE wrapping defaults — bd availability
    # only matters when we'd actually shell out to it (no test injection).
    ready_fn_injected = ready_fn is not None
    ready_fn = ready_fn or (lambda: _bd_ready(bd_bin))
    claim_fn = claim_fn or (lambda iid: _bd_claim(bd_bin, iid))
    pr_merged_fn = pr_merged_fn or _gh_pr_merged_on_main
    close_fn = close_fn or (lambda iid, reason: _bd_close(bd_bin, iid, reason))

    items = ready_fn()
    if not items:
        # Could be "bd binary missing" or genuine empty queue — caller
        # discriminates via bd_available check below.
        if not ready_fn_injected and not shutil.which(bd_bin) and bd_bin == "bd":
            return _result(claimed=False, callsign=callsign, reason="bd_unavailable")
        return _result(claimed=False, callsign=callsign, reason="no_eligible_work")

    eligible = [i for i in items if _eligible(i, callsign)]
    if not eligible:
        return _result(claimed=False, callsign=callsign, reason="no_eligible_work")

    eligible.sort(key=_priority_key)
    attempted: list[str] = []
    skipped_pr_merged: list[str] = []

    if dry_run:
        target = eligible[0]
        return _result(
            claimed=False,
            callsign=callsign,
            reason="dry_run",
            issue=target,
            attempted=[target["id"]],
        )

    # Walk every eligible candidate; merged-PR skips do NOT count against the
    # max_attempts (race-loss) budget — only actual claim attempts do.
    for candidate in eligible:
        if len(attempted) >= max_attempts:
            break
        iid = candidate.get("id")
        if not iid:
            continue
        pr_n = _extract_pr_number(candidate)
        if pr_n is not None and pr_merged_fn(pr_n):
            close_fn(iid, f"auto-claim: linked PR #{pr_n} already merged on main (y2al)")
            skipped_pr_merged.append(iid)
            continue
        attempted.append(iid)
        if claim_fn(iid):
            return _result(
                claimed=True,
                callsign=callsign,
                reason="claimed",
                issue=candidate,
                attempted=attempted,
                skipped_pr_merged=skipped_pr_merged,
            )
    if not attempted and skipped_pr_merged:
        return _result(
            claimed=False,
            callsign=callsign,
            reason="all_pr_merged",
            skipped_pr_merged=skipped_pr_merged,
        )
    return _result(
        claimed=False,
        callsign=callsign,
        reason="race_lost_all" if attempted else "no_eligible_work",
        attempted=attempted,
        skipped_pr_merged=skipped_pr_merged,
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
