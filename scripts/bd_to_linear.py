#!/usr/bin/env python3
"""bd_to_linear.py — Beads→Linear outbound sync (PR-2 of Dave Urgent directive).

Watches the local Beads export at `.beads/issues.jsonl` for status + assignee
changes since the last sync, then PATCHes the matching Linear issue (joined
by external_ref URL) via Linear's GraphQL API.

Outcomes from directive (Dave ts ~1778620420):
  - Outcome 2: bd close → Linear state=Done; bd update --status active →
    Linear state="In Progress"
  - Outcome 4: bd update --claim → Linear assignee=<claiming callsign>

State tracking:
  /home/elliotbot/.local/state/agency-os/bd-to-linear.state.json
  shape: {<bd_issue_id>: {"status": "...", "assignee": "...", "linear_id": "..."}}
  Diff against current bd export → only PATCH changed issues.

GraphQL direct via urllib (LINEAR_API_KEY env) — same pattern as
elliot_polling_loop.py:170 poll_linear_stale. Local mcp-bridge does NOT have
linear-server; CLAUDE.md references the browser-side claude.ai HTTP MCP
connector. urllib direct is portable + matches the existing in-repo pattern.

Callsign → Linear user UUID:
  Primary: AGENCY_OS_LINEAR_USER_<UPPER_CALLSIGN> env var (operator-configured,
    one per agent). Looked up first.
  Fallback: Linear `users` query by name (case-insensitive). If neither hits,
  log warning + skip assignee field (status still PATCHes).

Idempotency:
  - State file persists across runs. First-run with empty state file emits
    a PATCH for every bd issue with an external-ref + non-default status
    (one-time bootstrap; operator can prime by deleting the state file).
  - Subsequent runs PATCH only the diff.
  - Failed Linear PATCHes are logged but DO NOT update state — they retry
    on next run.

Always exits 0 — operator-script discipline. Errors logged to stderr.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("bd_to_linear")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

_LINEAR_GRAPHQL = "https://api.linear.app/graphql"
_DEFAULT_STATE_PATH = os.path.expanduser("~/.local/state/agency-os/bd-to-linear.state.json")
_DEFAULT_BEADS_PATH = ".beads/issues.jsonl"

# Linear state TYPE values per StateType enum. UI names ("Done", "In Progress")
# vary by workspace; the type values are fixed. We update state via the
# stateId field, which we resolve from a workflow-states query on first use.
_BD_TO_LINEAR_STATE_TYPE: dict[str, str] = {
    "closed": "completed",
    "active": "started",
    "in_progress": "started",
    "open": "unstarted",
}


def _state_path() -> Path:
    return Path(os.environ.get("AGENCY_OS_BD_TO_LINEAR_STATE", _DEFAULT_STATE_PATH))


def _beads_path() -> Path:
    return Path(os.environ.get("AGENCY_OS_BEADS_EXPORT", _DEFAULT_BEADS_PATH))


def _load_state() -> dict[str, dict]:
    p = _state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text() or "{}")
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, dict]) -> None:
    p = _state_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2, sort_keys=True))
    except OSError as exc:
        logger.warning("save state failed: %s", exc)


def _load_beads() -> list[dict]:
    p = _beads_path()
    if not p.exists():
        return []
    out: list[dict] = []
    try:
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        logger.warning("read beads export failed: %s", exc)
    return out


def _linear_id_from_external_ref(url: str) -> str | None:
    """Extract the Linear issue identifier (KEI-NN) from an issue URL."""
    m = re.search(r"/issue/([A-Z]+-\d+)", url)
    return m.group(1) if m else None


def _linear_graphql(api_key: str, query: str, variables: dict | None = None) -> dict | None:
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        _LINEAR_GRAPHQL,
        data=body,
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or "null")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Linear GraphQL failed: %s", exc)
        return None


def _resolve_assignee_id(api_key: str, callsign: str) -> str | None:
    """Try AGENCY_OS_LINEAR_USER_<UPPER> env first; else Linear users query."""
    env_key = f"AGENCY_OS_LINEAR_USER_{callsign.upper()}"
    if (uid := os.environ.get(env_key, "").strip()):
        return uid
    query = 'query($name:String!){users(filter:{name:{containsIgnoreCase:$name}},first:5){nodes{id name}}}'
    resp = _linear_graphql(api_key, query, {"name": callsign})
    nodes = ((resp or {}).get("data") or {}).get("users", {}).get("nodes") or []
    for n in nodes:
        if (n.get("name") or "").lower() == callsign.lower():
            return n.get("id")
    return nodes[0].get("id") if nodes else None


def _resolve_state_id(api_key: str, identifier: str, target_type: str) -> str | None:
    """Resolve the workflow state id for the issue's team matching target_type."""
    query = '''query($id:String!){issue(id:$id){team{states{nodes{id name type}}}}}'''
    resp = _linear_graphql(api_key, query, {"id": identifier})
    states = (((resp or {}).get("data") or {}).get("issue") or {}).get("team", {}).get("states", {}).get("nodes") or []
    for s in states:
        if s.get("type") == target_type:
            return s.get("id")
    return None


def _patch_linear_issue(
    api_key: str, identifier: str, state_id: str | None, assignee_id: str | None
) -> bool:
    """PATCH a Linear issue via issueUpdate mutation. Returns True on success."""
    if not (state_id or assignee_id):
        return True
    input_fields = {}
    if state_id:
        input_fields["stateId"] = state_id
    if assignee_id:
        input_fields["assigneeId"] = assignee_id
    mutation = (
        'mutation($id:String!,$input:IssueUpdateInput!){'
        'issueUpdate(id:$id,input:$input){success}}'
    )
    resp = _linear_graphql(api_key, mutation, {"id": identifier, "input": input_fields})
    return bool((((resp or {}).get("data") or {}).get("issueUpdate") or {}).get("success"))


def compute_deltas(prior: dict[str, dict], current: list[dict]) -> list[dict]:
    """Return list of {bd_id, linear_id, status_changed, assignee_changed, ...}
    for each bd issue whose external_ref maps to a Linear identifier AND
    whose status or assignee differs from the prior snapshot.
    """
    deltas: list[dict] = []
    for issue in current:
        bd_id = issue.get("id")
        ref = issue.get("external_ref") or (issue.get("metadata") or {}).get("external_ref")
        if not (bd_id and ref):
            continue
        linear_id = _linear_id_from_external_ref(ref)
        if not linear_id:
            continue
        cur_status = (issue.get("status") or "").lower()
        cur_assignee = (issue.get("assignee") or "").lower()
        snap = prior.get(bd_id, {})
        status_changed = snap.get("status") != cur_status
        assignee_changed = (snap.get("assignee") or "") != cur_assignee
        if status_changed or assignee_changed:
            deltas.append(
                {
                    "bd_id": bd_id,
                    "linear_id": linear_id,
                    "status": cur_status,
                    "assignee": cur_assignee,
                    "status_changed": status_changed,
                    "assignee_changed": assignee_changed,
                }
            )
    return deltas


def sync_once(api_key: str | None = None) -> int:
    """Run one sync pass. Returns count of issues PATCHed successfully."""
    key = api_key or os.environ.get("LINEAR_API_KEY", "")
    if not key:
        logger.warning("LINEAR_API_KEY not set; bd→linear sync no-op")
        return 0
    prior = _load_state()
    current = _load_beads()
    deltas = compute_deltas(prior, current)
    if not deltas:
        return 0
    new_state = dict(prior)
    patched = 0
    for d in deltas:
        state_id: str | None = None
        if d["status_changed"]:
            target_type = _BD_TO_LINEAR_STATE_TYPE.get(d["status"])
            if target_type:
                state_id = _resolve_state_id(key, d["linear_id"], target_type)
        assignee_id: str | None = None
        if d["assignee_changed"] and d["assignee"]:
            assignee_id = _resolve_assignee_id(key, d["assignee"])
        if _patch_linear_issue(key, d["linear_id"], state_id, assignee_id):
            new_state[d["bd_id"]] = {
                "status": d["status"],
                "assignee": d["assignee"],
                "linear_id": d["linear_id"],
            }
            patched += 1
    _save_state(new_state)
    return patched


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Compute deltas, log, but skip PATCH")
    args = parser.parse_args(argv)
    if args.dry_run:
        deltas = compute_deltas(_load_state(), _load_beads())
        for d in deltas:
            print(f"# DELTA bd={d['bd_id']} linear={d['linear_id']} status={d['status']} assignee={d['assignee']}", file=sys.stderr)
        return 0
    n = sync_once()
    if n > 0:
        print(f"# bd→linear: PATCHed {n} issue(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
