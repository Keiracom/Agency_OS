#!/usr/bin/env python3
"""next_work_prompter.py — wake an idle agent with their next concrete task.

Closes the gap diagnosed 2026-05-20 (Dave): self-claim loop updates bd
state on successful claim but never injects the claimed work into the
agent's tmux pane, leaving them idle at the prompt while bd shows
in_progress. Same problem for deliberators (elliot/aiden/max) — they
don't claim engineer KEIs at all, and nothing checks the PR-review queue
or pending dispatches for them.

Called by the stop hook AFTER it has classified+published the agent's
last response. If the agent has no follow-up work indicated by their own
text (e.g. tool calls still in flight), this prompter selects the next
concrete action and injects it into their tmux pane with Enter so the
session immediately picks up.

Role behaviour:
  * Worker (atlas/orion/scout/nova):
      - If bd has in_progress for me: inject "Continue KEI-XYZ".
      - Else: claim next P0/P1 from bd ready + inject brief with the title.
  * Reviewer / deliberator (aiden/max):
      - Scan open PRs for ones where my latest verdict is missing
        OR my prior HOLD was on a state that has since updated (rebase, CI
        flip, new commits). Inject "Review PR #N + #M + #O".
  * Orchestrator (elliot):
      - Scan open PRs for any awaiting my merge (dual-concur reached) +
        any in HOLD that need re-dispatch. Inject digest.

Idempotency: per-callsign per-60s throttle so re-firing the stop hook
within a turn doesn't double-inject.

Fail-open: any error logged + return 0; stop hook never blocks on this.

Usage:
    python3 next_work_prompter.py --callsign aiden
    python3 next_work_prompter.py --callsign elliot --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

WORKER_CALLSIGNS = frozenset({"atlas", "orion", "scout", "nova"})
REVIEWER_CALLSIGNS = frozenset({"aiden", "max"})
ORCHESTRATOR_CALLSIGNS = frozenset({"elliot"})

STATE_DIR = Path("/tmp/next_work_prompter")
THROTTLE_SECONDS = 60
TMUX_TARGETS = {
    "atlas": "atlas:0.0",
    "orion": "orion:0.0",
    "scout": "scout:0.0",
    "nova": "nova:0.0",
    "aiden": "aiden:0.0",
    "max": "maxbot:0.0",
    "elliot": "elliottbot:0.0",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("next_work_prompter")


def _throttled(callsign: str) -> bool:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    f = STATE_DIR / f"{callsign}.ts"
    now = time.time()
    if f.exists():
        try:
            last = float(f.read_text().strip())
            if now - last < THROTTLE_SECONDS:
                return True
        except (OSError, ValueError):
            pass
    f.write_text(str(now))
    return False


def _pane_idle(callsign: str) -> bool:
    """True if the agent's tmux pane is at an idle prompt (safe to inject).

    An agent mid-turn shows 'esc to interrupt' in the status line. Injecting
    then would queue input on top of active work. We only inject when the
    pane shows the empty prompt and no in-progress indicator.
    """
    target = TMUX_TARGETS.get(callsign)
    if not target:
        return False
    try:
        cp = subprocess.run(
            ["tmux", "capture-pane", "-t", target, "-p"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    if cp.returncode != 0:
        return False
    tail = "\n".join(cp.stdout.splitlines()[-12:]).lower()
    # Mid-turn markers — Claude Code shows these only while processing.
    return not ("esc to interrupt" in tail or "tokens ·" in tail)


def _inject(callsign: str, text: str) -> bool:
    target = TMUX_TARGETS.get(callsign)
    if not target:
        log.warning("no tmux target for %s", callsign)
        return False
    try:
        subprocess.run(
            ["tmux", "send-keys", "-t", target, text],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        time.sleep(0.4)
        subprocess.run(
            ["tmux", "send-keys", "-t", target, "C-m"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        log.info("injected -> %s: %s", target, text[:120])
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        log.warning("tmux inject err: %s", e)
        return False


def _bd_in_progress(callsign: str) -> dict | None:
    try:
        cp = subprocess.run(
            ["bd", "list", "--status=in_progress", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd="/home/elliotbot/clawd/Agency_OS",
        )
        if cp.returncode != 0:
            return None
        data = json.loads(cp.stdout) if cp.stdout.strip() else []
        items = data if isinstance(data, list) else data.get("issues", [])
        for it in items:
            if (it.get("assignee") or it.get("claimed_by") or "").lower() == callsign:
                return it
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def _bd_next_ready_for(callsign: str) -> dict | None:
    """First eligible bd ready item for this callsign (P0 then P1, unassigned)."""
    try:
        cp = subprocess.run(
            ["bd", "ready", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            cwd="/home/elliotbot/clawd/Agency_OS",
        )
        if cp.returncode != 0:
            return None
        data = json.loads(cp.stdout) if cp.stdout.strip() else []
        items = data if isinstance(data, list) else data.get("issues", [])

        # Priority sort + assignee filter
        def pri(it):
            p = it.get("priority")
            if isinstance(p, int):
                return p
            m = re.match(r"P?(\d+)", str(p or ""))
            return int(m.group(1)) if m else 9

        items.sort(key=pri)
        for it in items:
            assignee = (it.get("assignee") or "").lower()
            if assignee and assignee != callsign:
                continue
            return it
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


REVIEW_VERDICT_RE = re.compile(
    r"\[REVIEW:(approve|HOLD)[:\s]+([a-z]+)\]|\[CONCUR:([a-z]+)\]",
    re.IGNORECASE,
)


def _open_prs() -> list[dict]:
    try:
        cp = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state=open",
                "--limit=50",
                "--json",
                "number,title,updatedAt,comments,author,statusCheckRollup,commits",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if cp.returncode != 0:
            return []
        return json.loads(cp.stdout) if cp.stdout.strip() else []
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


_MAIN_HEAD_FAILURES: set[str] | None = None


def _reset_main_head_cache() -> None:
    """Test hook — clears the per-process main-HEAD failures cache."""
    global _MAIN_HEAD_FAILURES
    _MAIN_HEAD_FAILURES = None


def _fetch_main_failures_for(
    endpoint: str, list_key: str, name_key: str, state_key: str
) -> set[str]:
    """Pull FAILURE context names from one GitHub API endpoint.

    Structural extraction from _main_head_failures (Aiden HOLD-FINAL on PR #1113,
    Sonar S3776 cognitive-complexity refactor). One endpoint, one try block, one
    pass through results — keeps each function simple enough to read top-to-bottom.
    """
    failures: set[str] = set()
    try:
        cp = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if cp.returncode != 0 or not cp.stdout.strip():
            return failures
        data = json.loads(cp.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return failures
    for item in data.get(list_key, []):
        if (item.get(state_key) or "").lower() == "failure":
            n = item.get(name_key)
            if n:
                failures.add(n)
    return failures


def _main_head_failures() -> set[str]:
    """Context names of currently-failing checks on origin/main HEAD.

    Combines legacy commit statuses (StatusContext — Vercel, third-party CI)
    and modern check-runs (GH Actions). Cached for the process lifetime so
    classification of multiple PRs in one prompter cycle reuses one snapshot.

    Used by _classify_pr_block to detect INFRA-blocked PRs per Agency_OS-sg29:
    a check that's red on the PR AND red on main HEAD is repo-wide infra, not
    author-caused — author has nothing to do, no nudge.
    """
    global _MAIN_HEAD_FAILURES
    if _MAIN_HEAD_FAILURES is not None:
        return _MAIN_HEAD_FAILURES
    failures: set[str] = set()
    for args in (
        ("repos/keiracom/Agency_OS/commits/main/status", "statuses", "context", "state"),
        ("repos/keiracom/Agency_OS/commits/main/check-runs", "check_runs", "name", "conclusion"),
    ):
        failures |= _fetch_main_failures_for(*args)
    _MAIN_HEAD_FAILURES = failures
    return _MAIN_HEAD_FAILURES


def _pr_check_failures(pr: dict) -> set[str]:
    """Context names of FAILURE checks on this PR's head."""
    names: set[str] = set()
    for chk in pr.get("statusCheckRollup", []) or []:
        verdict = (chk.get("conclusion") or chk.get("state") or "").upper()
        if verdict == "FAILURE":
            n = chk.get("name") or chk.get("context")
            if n:
                names.add(n)
    return names


def _pr_latest_commit_ts(pr: dict) -> str:
    """ISO timestamp of the PR's most recent commit (empty if unknown)."""
    latest = ""
    for c in pr.get("commits", []) or []:
        commit = c.get("commit") or {}
        committer = commit.get("committer") or {}
        ts = committer.get("date") or c.get("committedDate") or ""
        if ts > latest:
            latest = ts
    return latest


_HOLD_BODY_RE = re.compile(r"\[review:hold|\[hold-final|changes_requested", re.IGNORECASE)


def _latest_hold_ts(pr: dict) -> str:
    """ISO timestamp of the most recent HOLD/CHANGES_REQUESTED comment."""
    latest = ""
    for c in pr.get("comments", []) or []:
        if _HOLD_BODY_RE.search(c.get("body") or ""):
            at = c.get("createdAt") or ""
            if at > latest:
                latest = at
    return latest


def classify_pr_block(pr: dict) -> str | None:
    """Three-state classifier per Agency_OS-sg29.

    Returns one of: 'author', 'reviewer', 'infra', or None.

      - 'author':   real CI red NOT mirrored on main, OR a HOLD/CHANGES_REQUESTED
                    comment newer than the author's latest commit. Author must act.
      - 'infra':    every failing PR check is ALSO failing on origin/main HEAD —
                    repo-wide infra regression, not author-caused. Author has
                    nothing to do; orchestrator should investigate main red
                    separately (e.g. via a [PROPOSE:investigate-main-red]).
      - 'reviewer': CI green AND author's latest commit newer than every HOLD
                    AND not yet dual-approved. Waiting on reviewer verdict.
      - None:       not blocked (green + dual-approved, or no signal).

    INFRA detection uses main-HEAD parity (per Aiden's note) — not check-name
    pattern matching, which would drift as context names change.
    """
    pr_failures = _pr_check_failures(pr)
    if pr_failures:
        main_failures = _main_head_failures()
        author_caused = pr_failures - main_failures
        if author_caused:
            return "author"
        if pr_failures.issubset(main_failures):
            return "infra"
    latest_commit = _pr_latest_commit_ts(pr)
    latest_hold = _latest_hold_ts(pr)
    if latest_hold and latest_hold > latest_commit:
        return "author"
    state = _verdicts_on(pr)
    author = _author_callsign(pr)
    non_auth = [d for d in ("elliot", "aiden", "max") if d != author]
    approves = sum(1 for d in non_auth if state.get(d) == "approve")
    if approves >= 2:
        return None
    has_hold = any(v == "hold" for v in state.values())
    if has_hold or not pr_failures:
        return "reviewer"
    return None


def _verdicts_on(pr: dict) -> dict:
    """Latest-verdict-per-reviewer for a PR."""
    state: dict[str, str] = {}
    last_at: dict[str, str] = {}
    for c in pr.get("comments", []):
        body = c.get("body") or ""
        at = c.get("createdAt") or ""
        for m in REVIEW_VERDICT_RE.finditer(body):
            if m.group(3):
                who, v = m.group(3).lower(), "approve"
            else:
                v = (m.group(1) or "").lower()
                who = (m.group(2) or "").lower()
            if at >= last_at.get(who, ""):
                last_at[who] = at
                state[who] = v
    return state


def _author_callsign(pr: dict) -> str | None:
    m = re.match(r"\[(\w+)\]", pr.get("title", ""))
    return m.group(1).lower() if m else None


def _reviewer_pending(callsign: str) -> list[int]:
    """PRs where this reviewer has no verdict yet OR prior HOLD on a stale state."""
    pending = []
    for pr in _open_prs():
        author = _author_callsign(pr)
        if author == callsign:
            continue  # author-exclusion
        state = _verdicts_on(pr)
        my_verdict = state.get(callsign)
        if my_verdict is None:
            pending.append(pr["number"])
        # NOTE: HOLD-on-stale-state detection requires comparing comment ts
        # to PR last-commit ts; deferring that to v2.
    return pending


def _own_prs_needing_fix(callsign: str) -> list[int]:
    """PRs this callsign authored that are AUTHOR-blocked (author must act).

    Per Agency_OS-sg29: REVIEWER-blocked (author already responded, waiting on
    re-review) and INFRA-blocked (CI red on contexts also red on main HEAD,
    not author-caused) are EXCLUDED — author has nothing to do for those,
    so no nudge. Only AUTHOR-blocked PRs are returned for the [NEXT-WORK]
    fix-up dispatch.
    """
    out = []
    for pr in _open_prs():
        if _author_callsign(pr) != callsign:
            continue
        if classify_pr_block(pr) == "author":
            out.append(pr["number"])
    return out


def _orchestrator_actions(callsign: str) -> str | None:
    """For elliot: scan for merge-eligible + held PRs awaiting dispatch."""
    merge_ready, holds = [], []
    for pr in _open_prs():
        author = _author_callsign(pr)
        state = _verdicts_on(pr)
        non_auth = [d for d in ("elliot", "aiden", "max") if d != author]
        approves = [d for d in non_auth if state.get(d) == "approve"]
        explicit_holds = [d for d in non_auth if state.get(d) == "hold"]
        if explicit_holds:
            holds.append(pr["number"])
        elif len(approves) >= 2:
            merge_ready.append(pr["number"])
    parts = []
    if merge_ready:
        parts.append(
            f"{len(merge_ready)} PRs merge-eligible — poll and merge: {sorted(merge_ready)[:5]}{'...' if len(merge_ready) > 5 else ''}"
        )
    if holds:
        parts.append(
            f"{len(holds)} PRs HOLD — check author fix-ups: {sorted(holds)[:5]}{'...' if len(holds) > 5 else ''}"
        )
    return " | ".join(parts) if parts else None


def prompt_worker(callsign: str) -> str | None:
    """Return the prompt text for a worker, or None if nothing to do."""
    # Own blocked PRs take priority over claiming new work.
    own_fix = _own_prs_needing_fix(callsign)
    if own_fix:
        return (
            f"[NEXT-WORK:{callsign}] FIX your own {len(own_fix)} blocked PRs first: "
            f"{sorted(own_fix)[:6]} — fetch CI/reviewer comments, push fix-up, "
            "post [FIXED:<callsign>] before claiming anything new."
        )
    ip = _bd_in_progress(callsign)
    if ip:
        return f"[NEXT-WORK:{callsign}] Continue claimed KEI {ip.get('id') or ip.get('identifier')}: {ip.get('title', '')[:80]}. Pick up where you left off."
    nx = _bd_next_ready_for(callsign)
    if nx:
        return f"[NEXT-WORK:{callsign}] Claim {nx.get('id') or nx.get('identifier')}: {nx.get('title', '')[:80]} (priority {nx.get('priority', '?')}). Run `bd update <id> --claim` then begin."
    return None


def prompt_reviewer(callsign: str) -> str | None:
    own_fix = _own_prs_needing_fix(callsign)
    pending = _reviewer_pending(callsign)
    parts = []
    if own_fix:
        parts.append(
            f"FIX your own {len(own_fix)} blocked PRs first: {sorted(own_fix)[:6]} "
            "— fetch CI/reviewer comments, push fix-up, post [FIXED:<callsign>]"
        )
    if pending:
        head = sorted(pending)[:6]
        parts.append(
            f"then review {len(pending)} PRs awaiting your verdict: "
            f"{head}{'...' if len(pending) > len(head) else ''} "
            "(dual-Sonar verbatim + gh pr comment)"
        )
    if not parts:
        return None
    return f"[NEXT-WORK:{callsign}] " + " | ".join(parts)


def prompt_orchestrator(callsign: str) -> str | None:
    summary = _orchestrator_actions(callsign)
    if not summary:
        return None
    return (
        f"[NEXT-WORK:{callsign}] PR queue state — {summary}. Poll, dispatch, merge as appropriate."
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--callsign", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--poll-mode",
        action="store_true",
        help="Called from the 60s self-claim loop — require an idle pane "
        "before injecting (don't interrupt mid-turn work).",
    )
    args = p.parse_args(argv)
    cs = args.callsign.lower()
    if not args.dry_run and _throttled(cs):
        log.info("throttled: %s within %ds window", cs, THROTTLE_SECONDS)
        return 0
    if cs in WORKER_CALLSIGNS:
        prompt = prompt_worker(cs)
    elif cs in REVIEWER_CALLSIGNS:
        prompt = prompt_reviewer(cs)
    elif cs in ORCHESTRATOR_CALLSIGNS:
        prompt = prompt_orchestrator(cs)
    else:
        log.warning("unknown callsign role: %s", cs)
        return 0
    if not prompt:
        log.info("no next work for %s", cs)
        return 0
    if args.dry_run:
        print(prompt)
        return 0
    # Idle-pane guard: never inject on top of active work. Always enforced —
    # stop-hook path fires at turn-end (pane already idle), poll path needs it.
    if not _pane_idle(cs):
        log.info("pane busy for %s — skip inject (work in progress)", cs)
        return 0
    _inject(cs, prompt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
