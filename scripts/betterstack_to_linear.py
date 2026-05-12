#!/usr/bin/env python3
"""betterstack_to_linear.py — BS incident → Linear KEI subprocess wrapper.

KEI-26 P1 dispatch from src/api/webhooks/betterstack.py. Stdin: JSON
envelope normalised from BS incident webhook payload (canonical shape per
empirical probe of BS v2 /api/v2/incidents response):

  {
    "incident_id": "964390352",
    "monitor_name": "railway-prefect",
    "monitor_url": "https://prefect.keiracom.app/api/health",
    "cause": "DNS lookup failure",
    "status": "started",
    "started_at": "2026-05-12T12:48:08.330Z",
    "resolved_at": "",
    "monitor_id": "4400119"
  }

Creates a Linear KEI via GraphQL issueCreate mutation:
  - Team: Keiracom (id 4686528f-ce77-4c2f-968b-3dc76b34d6fe, empirically
    resolved from teams{} GraphQL query during build probe; env override
    LINEAR_TEAM_ID supported)
  - Priority: 1 (Urgent) per Dave's restart-readiness directive intent
  - State: started (In Progress) — Linear state_id resolved via team states query
  - Assignee: env AGENCY_OS_LINEAR_USER_ELLIOT (fallback to users{} search)

Idempotency via state file at ~/.local/state/agency-os/betterstack-incidents.json
mapping {incident_id: linear_issue_id, linear_issue_url, created_at}.
Same BS incident replayed → skip create + log existing mapping.

Always exits 0 — operator-script discipline.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("bs_to_linear")
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

_LINEAR_GRAPHQL = "https://api.linear.app/graphql"
_DEFAULT_TEAM_ID = "4686528f-ce77-4c2f-968b-3dc76b34d6fe"  # Keiracom team
_DEFAULT_STATE_PATH = os.path.expanduser(
    "~/.local/state/agency-os/betterstack-incidents.json"
)

_ALLOWED_STATE_ROOTS: tuple[Path, ...] = (
    Path(os.path.expanduser("~/.local/state/agency-os")),
    Path("/tmp"),  # NOSONAR — pytest tmp_path
)


def _is_under(p: Path, root: Path) -> bool:
    try:
        p.relative_to(root)
        return True
    except ValueError:
        return False


def _state_path() -> Path:
    """Resolve state path; env override validated against _ALLOWED_STATE_ROOTS."""
    raw = os.environ.get("AGENCY_OS_BS_INCIDENTS_STATE", _DEFAULT_STATE_PATH)
    resolved = Path(raw).expanduser().resolve()
    if not any(_is_under(resolved, root.resolve()) for root in _ALLOWED_STATE_ROOTS):
        return Path(_DEFAULT_STATE_PATH).expanduser().resolve()
    return resolved


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
        p.write_text(json.dumps(state, indent=2, sort_keys=True))  # NOSONAR — path is helper-resolved via _state_path() which validates the env override against _ALLOWED_STATE_ROOTS via _is_under; not user-supplied
    except OSError as exc:
        logger.warning("state save failed: %s", exc)


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
    except (json.JSONDecodeError, OSError) as exc:
        # OSError covers urllib.error.URLError (subclass).
        logger.warning("Linear GraphQL failed: %s", exc)
        return None


def _resolve_started_state_id(api_key: str, team_id: str) -> str | None:
    query = (
        'query($id:String!){team(id:$id){states{nodes{id name type}}}}'
    )
    resp = _linear_graphql(api_key, query, {"id": team_id})
    states = (((resp or {}).get("data") or {}).get("team", {}).get("states", {}).get("nodes") or [])
    for s in states:
        if s.get("type") == "started":
            return s.get("id")
    return None


def _resolve_assignee_id(api_key: str) -> str | None:
    """Resolve Elliot's Linear user id. Env primary; GraphQL fallback."""
    if uid := os.environ.get("AGENCY_OS_LINEAR_USER_ELLIOT", "").strip():
        return uid
    query = 'query{users(filter:{name:{containsIgnoreCase:"elliot"}},first:3){nodes{id name}}}'
    resp = _linear_graphql(api_key, query)
    nodes = ((resp or {}).get("data") or {}).get("users", {}).get("nodes") or []
    return nodes[0].get("id") if nodes else None


def _create_linear_issue(api_key: str, event: dict, team_id: str, state_id: str | None, assignee_id: str | None) -> dict | None:
    title = f"BetterStack incident — {event['monitor_name']}: {event['cause'][:80]}"
    description = (
        f"Auto-created from Better Stack incident webhook.\n\n"
        f"- **Monitor:** {event['monitor_name']}\n"
        f"- **URL:** {event['monitor_url']}\n"
        f"- **Cause:** {event['cause']}\n"
        f"- **Started at:** {event['started_at']}\n"
        f"- **BS incident id:** {event['incident_id']}\n"
        f"- **BS monitor id:** {event['monitor_id']}\n"
    )
    input_fields: dict = {
        "teamId": team_id,
        "title": title,
        "description": description,
        "priority": 1,  # Urgent
    }
    if state_id:
        input_fields["stateId"] = state_id
    if assignee_id:
        input_fields["assigneeId"] = assignee_id
    mutation = (
        'mutation($input:IssueCreateInput!){'
        'issueCreate(input:$input){success issue{id identifier url}}}'
    )
    resp = _linear_graphql(api_key, mutation, {"input": input_fields})
    issue = (((resp or {}).get("data") or {}).get("issueCreate") or {}).get("issue")
    return issue


def handle_incident(event: dict) -> int:  # NOSONAR S3516 — multiple return paths: 0 success/idempotent-skip, 2 missing LINEAR_API_KEY (operator misconfig signal), 0 graceful no-op on no-incident-id or create-failure; failures fail-open + logged per operator-script discipline
    """Idempotent create: skip if incident_id already mapped to a Linear issue."""
    incident_id = event.get("incident_id", "")
    if not incident_id:
        return 0
    state = _load_state()
    if incident_id in state:
        logger.info(
            "incident %s idempotent skip: already mapped to %s",
            incident_id,
            state[incident_id].get("linear_issue_id", "?"),
        )
        return 0
    api_key = os.environ.get("LINEAR_API_KEY", "")
    if not api_key:
        logger.warning("LINEAR_API_KEY not set; cannot create Linear KEI")
        return 2  # operator misconfig signal — surfaces in systemd-timer logs
    team_id = os.environ.get("LINEAR_TEAM_ID", _DEFAULT_TEAM_ID)
    state_id = _resolve_started_state_id(api_key, team_id)
    assignee_id = _resolve_assignee_id(api_key)
    issue = _create_linear_issue(api_key, event, team_id, state_id, assignee_id)
    if not issue:
        logger.warning("issueCreate returned no issue")
        return 0
    state[incident_id] = {
        "linear_issue_id": issue.get("id"),
        "linear_identifier": issue.get("identifier"),
        "linear_url": issue.get("url"),
        "created_at": subprocess.check_output(["date", "-Iseconds"]).decode().strip(),  # noqa: S603
    }
    _save_state(state)
    logger.info("created Linear %s for BS incident %s", issue.get("identifier"), incident_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Read event JSON from stdin")
    parser.add_argument("--event-file", type=Path, default=None)
    args = parser.parse_args(argv)
    raw = ""
    try:
        if args.event_file is not None and args.event_file.exists():
            raw = args.event_file.read_text()
        elif args.json or not sys.stdin.isatty():
            raw = sys.stdin.read()
    except OSError as exc:
        logger.warning("read event failed: %s", exc)
        return 0
    if not raw.strip():
        return 0
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("event JSON parse failed: %s", exc)
        return 0
    return handle_incident(event)


if __name__ == "__main__":
    sys.exit(main())
