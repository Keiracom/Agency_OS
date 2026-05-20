#!/usr/bin/env python3
"""restore_linear_state.py — KEI-234 — restore Linear issues downgraded by the
K3 orchestrator overwrite bug between 2026-05-19 11:05-12:23 UTC.

The buggy `_event_to_linear_state` mapped Postgres `available` to Linear `todo`,
silently flipping issues from `Done`/`Canceled`/`In Progress` to `Todo` whenever
the orchestrator dispatched an `update` event with the default Postgres status.
KEI-233 / PR #1080 fixed the orchestrator. This script repairs the historical
damage by querying each issue's `history` and reverting to the pre-damage state.

Algorithm:
  1. Pull every Linear issue currently in `unstarted` state.
  2. For each, query `history` and find any state-change event whose
     `createdAt` falls inside the damage window AND whose `actor.id` matches
     our API-key actor (David's user id; the orchestrator uses David's key).
  3. The `fromState` of that event = the canonical pre-damage state.
  4. Restore via `issueUpdate(input: { stateId: <pre_damage_state_id> })`.

Idempotency: re-runs are no-ops — an issue already at its pre-damage state has
no in-window flip to revert.

Usage:
  python3 scripts/restore_linear_state.py            # dry-run
  python3 scripts/restore_linear_state.py --apply    # restore
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("restore_linear_state")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

_LINEAR_GRAPHQL_URL = "https://api.linear.app/graphql"
_DEFAULT_TEAM_ID = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"  # Keiracom

# Damage window — orchestrator bug active 2026-05-19 11:05-12:23 UTC.
# Atlas stopped the service at 12:22:50. Buffer the window by 1 min each side
# to absorb any boundary-clock skew between systemd journal and Linear server.
DAMAGE_WINDOW_START = datetime(2026, 5, 19, 11, 4, 0, tzinfo=UTC)
DAMAGE_WINDOW_END = datetime(2026, 5, 19, 12, 24, 0, tzinfo=UTC)


def _api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY", "")
    if not key:
        raise SystemExit("LINEAR_API_KEY must be set")
    return key


def _graphql(api_key: str, query: str, variables: dict[str, Any] | None = None) -> dict | None:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        _LINEAR_GRAPHQL_URL,
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read() or "null")
    except (json.JSONDecodeError, urllib.error.URLError, OSError) as exc:
        logger.warning("GraphQL failed: %s", exc)
        return None


def fetch_viewer_id(api_key: str) -> str | None:
    """The user id that the API key authenticates as.
    Used as the actor filter — only events caused by this user during the
    damage window are eligible for revert (they're the orchestrator's writes)."""
    resp = _graphql(api_key, "{ viewer { id name email } }")
    return ((resp or {}).get("data") or {}).get("viewer", {}).get("id")


def fetch_candidates(api_key: str, team_id: str) -> list[dict[str, Any]]:
    """Linear issues currently in `unstarted` state for the team.

    The bug always flipped to `unstarted` (Todo), so that's our candidate
    universe. Issues legitimately in Todo (never touched by the orchestrator)
    are filtered out in the next step via history actor+timestamp check.
    """
    query = """
    query($teamId: ID!, $after: String) {
      issues(
        filter: {
          team: { id: { eq: $teamId } }
          state: { type: { eq: "unstarted" } }
        }
        first: 100
        after: $after
      ) {
        pageInfo { hasNextPage endCursor }
        nodes { id identifier title state { id type name } }
      }
    }
    """
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        resp = _graphql(api_key, query, {"teamId": team_id, "after": cursor})
        page = ((resp or {}).get("data") or {}).get("issues") or {}
        out.extend(page.get("nodes") or [])
        info = page.get("pageInfo") or {}
        if not info.get("hasNextPage"):
            break
        cursor = info.get("endCursor")
    return out


def fetch_history(api_key: str, issue_uuid: str) -> list[dict[str, Any]]:
    """Pull the state-change history for one issue (chronological)."""
    query = """
    query($id: String!) {
      issue(id: $id) {
        history(first: 50) {
          nodes {
            createdAt
            actor { id }
            fromState { id type name }
            toState { id type name }
          }
        }
      }
    }
    """
    resp = _graphql(api_key, query, {"id": issue_uuid})
    nodes = ((((resp or {}).get("data") or {}).get("issue") or {}).get("history") or {}).get(
        "nodes"
    ) or []
    return nodes


def find_pre_damage_state(
    history: list[dict[str, Any]],
    actor_id: str,
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any] | None:
    """Return the `fromState` of the FIRST in-window event by the buggy actor.

    Earliest in-window event by the orchestrator's actor = the state the
    issue was in BEFORE the bug touched it. That's our restore target.
    Returns None if no such event — issue wasn't damaged.
    """
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for event in history:
        from_state = event.get("fromState") or {}
        actor = (event.get("actor") or {}).get("id")
        if actor != actor_id:
            continue
        if not from_state:
            continue
        ts_raw = event.get("createdAt", "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        if window_start <= ts <= window_end:
            candidates.append((ts, from_state))
    if not candidates:
        return None
    # Earliest = first damage event = the state the issue was in pre-bug.
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]


def apply_restore(api_key: str, issue_uuid: str, state_id: str) -> bool:
    """Set the issue's state via Linear's issueUpdate mutation. True on success."""
    mutation = """
    mutation($id: String!, $state: String!) {
      issueUpdate(id: $id, input: { stateId: $state }) {
        success
        issue { state { type name } }
      }
    }
    """
    resp = _graphql(api_key, mutation, {"id": issue_uuid, "state": state_id})
    success = (((resp or {}).get("data") or {}).get("issueUpdate") or {}).get("success", False)
    return bool(success)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Mutate Linear (default dry-run)")
    parser.add_argument("--team-id", default=os.environ.get("LINEAR_TEAM_ID", _DEFAULT_TEAM_ID))
    parser.add_argument("--window-start", default=DAMAGE_WINDOW_START.isoformat())
    parser.add_argument("--window-end", default=DAMAGE_WINDOW_END.isoformat())
    args = parser.parse_args(argv)

    api_key = _api_key()
    actor_id = fetch_viewer_id(api_key)
    if not actor_id:
        logger.error("could not resolve viewer id from LINEAR_API_KEY")
        return 2
    logger.info("actor (orchestrator's actor) = %s", actor_id)

    window_start = datetime.fromisoformat(args.window_start)
    window_end = datetime.fromisoformat(args.window_end)
    logger.info("damage window: %s → %s", window_start, window_end)

    candidates = fetch_candidates(api_key, args.team_id)
    logger.info("candidates (Linear state=unstarted): %d", len(candidates))

    plan: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for cand in candidates:
        history = fetch_history(api_key, cand["id"])
        pre = find_pre_damage_state(history, actor_id, window_start, window_end)
        if pre is None:
            continue
        plan.append((cand, pre))

    print(f"\n{'=' * 80}")
    print(f"RESTORATION PLAN — {len(plan)} issues")
    print("=" * 80)
    for cand, pre in plan:
        print(
            f"  {cand['identifier']:<10} {pre['type']:<10} ({pre['name']:<15}) "
            f"← was wrongly flipped to {cand['state']['type']}  {cand['title'][:50]}"
        )

    applied = 0
    if args.apply and plan:
        print("\nApplying...")
        for cand, pre in plan:
            ok = apply_restore(api_key, cand["id"], pre["id"])
            status = "OK" if ok else "FAIL"
            print(f"  {status:<4} {cand['identifier']:<10} → {pre['name']}")
            if ok:
                applied += 1
        print(f"\nApplied: {applied}/{len(plan)}")
    elif plan:
        print("\nDry-run. Pass --apply to mutate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
