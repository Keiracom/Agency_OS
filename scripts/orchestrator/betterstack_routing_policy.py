#!/usr/bin/env python3
"""betterstack_routing_policy.py — Better Stack notification policy wire-in.

PR-C-v2 of the Better Stack bundle. Creates a Better Stack notification
policy that routes incidents to all configured Slack integrations + applies
the policy to all 5 heartbeats (PR-A) and 3 uptime monitors (PR-B).

Per Dave directive ts ~1778618200: critical incidents → #ceo. Routine
+ resolved → #execution (phase 2, gated on a SECOND Slack integration
that does not yet exist).

Phase 1 (THIS script):
  - Creates / reuses one urgency profile (name="Agency OS — Critical").
  - Creates / reuses one policy (name="Agency OS — Critical incidents")
    with a single escalation step: wait_before=0, urgency_id=<above>,
    step_members=[{type: all_slack_integrations}].
  - PATCHes policy_id onto all 3 uptime monitors + 5 heartbeats.
  - Result: BS routes incident-creation events on those resources through
    every Slack integration the team has — currently only the #ceo one
    (id 102756) per BS dashboard state.

Phase 2 (separate fast-follow, gated on Dave OAuth):
  - When operator runs BS Slack OAuth pointing at #execution, this script
    re-runs and (when phase-2 enabled) creates a SECOND policy +
    second urgency for "Routine + Resolved" with step_members targeting
    the #execution integration specifically.
  - Until that integration exists, phase-2 logic is dormant — script logs
    the gate and skips.

Idempotency contract:
  - Urgency matched by `name`. Reused if present, created otherwise.
  - Policy matched by `name`. Reused if present; PATCHed if step drift
    detected. Steps drift = step type or urgency_id or member type
    differs.
  - Resource policy_id matched by `policy_id` on each monitor/heartbeat
    attribute. PATCH-set only if missing or different.

Schema source (BS docs probed 2026-05-12 via 14-curl probe):
    https://betterstack.com/docs/uptime/api/escalation-policies/

Working policy create body:
    {"name":"X","steps":[{"type":"escalation","wait_before":0,
                          "urgency_id":<id>,
                          "step_members":[{"type":"all_slack_integrations"}]}]}

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_routing_policy.py

Env overrides (tests + alt names):
    AGENCY_OS_BETTERSTACK_API_BASE — API root
    AGENCY_OS_BETTERSTACK_POLICY_NAME — policy name (default "Agency OS — Critical incidents")
    AGENCY_OS_BETTERSTACK_URGENCY_NAME — urgency name (default "Agency OS — Critical")
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE_DEFAULT = "https://uptime.betterstack.com/api/v2"

DEFAULT_POLICY_NAME = "Agency OS — Critical incidents"
DEFAULT_URGENCY_NAME = "Agency OS — Critical"

# Resource names to apply the policy to (must match PR-A heartbeats + PR-B monitors).
MONITOR_NAMES: tuple[str, ...] = ("agencyxos.ai", "supabase-rest", "railway-prefect")
HEARTBEAT_NAMES: tuple[str, ...] = (
    "elliot-polling-loop",
    "cognee-phase1-ingest",
    "prefect-pipeline",
    "central-listener",
    "agency-os-discovery",
)


def _api_base() -> str:
    return os.environ.get("AGENCY_OS_BETTERSTACK_API_BASE", API_BASE_DEFAULT)


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _request(method: str, path: str, api_key: str, body: dict | None = None) -> dict | None:
    url = f"{_api_base()}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_auth_headers(api_key), method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read() or "null")
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace") if exc.fp else ""
        print(f"[bs-routing] HTTP {exc.code} on {method} {url}: {body_text[:200]}", file=sys.stderr)
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"[bs-routing] network/parse error on {method} {url}: {exc}", file=sys.stderr)
        return None


def ensure_urgency(api_key: str, name: str) -> dict | None:
    """Find by name or POST. Email-on, push/sms/call off (Slack covers the rest)."""
    resp = _request("GET", "/urgencies?per_page=100", api_key)
    for u in (resp or {}).get("data", []) or []:
        if u.get("attributes", {}).get("name") == name:
            return u
    body = {"name": name, "email": True, "push": False, "sms": False, "call": False}
    return (_request("POST", "/urgencies", api_key, body) or {}).get("data")


def _step_drift(existing_steps: list[dict], desired_urgency_id: int) -> bool:
    """True iff the policy's steps don't match our desired single-escalation step."""
    if len(existing_steps) != 1:
        return True
    s = existing_steps[0]
    if s.get("type") != "escalation":
        return True
    if s.get("urgency_id") != desired_urgency_id:
        return True
    members = s.get("step_members") or []
    return not (len(members) == 1 and members[0].get("type") == "all_slack_integrations")


def ensure_policy(api_key: str, name: str, urgency_id: int) -> dict | None:
    """Match by name. Create if missing; PATCH if step drift."""
    resp = _request("GET", "/policies?per_page=100", api_key)
    existing = (resp or {}).get("data", []) or []
    step = {
        "type": "escalation",
        "wait_before": 0,
        "urgency_id": urgency_id,
        "step_members": [{"type": "all_slack_integrations"}],
    }
    for p in existing:
        if p.get("attributes", {}).get("name") == name:
            if not _step_drift(p.get("attributes", {}).get("steps") or [], urgency_id):
                return p
            return (_request("PATCH", f"/policies/{p.get('id')}", api_key, {"steps": [step]}) or {}).get("data") or p
    return (_request("POST", "/policies", api_key, {"name": name, "steps": [step]}) or {}).get("data")


def apply_policy_to_monitor(api_key: str, monitor_id: str, policy_id: int) -> bool:
    """PATCH monitor.policy_id if missing/different. Returns True if changed."""
    cur = _request("GET", f"/monitors/{monitor_id}", api_key)
    if (cur or {}).get("data", {}).get("attributes", {}).get("policy_id") == policy_id:
        return False
    return _request("PATCH", f"/monitors/{monitor_id}", api_key, {"policy_id": policy_id}) is not None


def apply_policy_to_heartbeat(api_key: str, hb_id: str, policy_id: int) -> bool:
    cur = _request("GET", f"/heartbeats/{hb_id}", api_key)
    if (cur or {}).get("data", {}).get("attributes", {}).get("policy_id") == policy_id:
        return False
    return _request("PATCH", f"/heartbeats/{hb_id}", api_key, {"policy_id": policy_id}) is not None


def list_monitors(api_key: str) -> list[dict]:
    return (_request("GET", "/monitors?per_page=100", api_key) or {}).get("data", []) or []


def list_heartbeats(api_key: str) -> list[dict]:
    return (_request("GET", "/heartbeats?per_page=100", api_key) or {}).get("data", []) or []


def _find(records: list[dict], name: str, attr: str) -> dict | None:
    return next((r for r in records if r.get("attributes", {}).get(attr) == name), None)


def main() -> int:
    api_key = os.environ.get("BETTERSTACK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BETTERSTACK_API_KEY env not set", file=sys.stderr)
        return 2

    policy_name = os.environ.get("AGENCY_OS_BETTERSTACK_POLICY_NAME", DEFAULT_POLICY_NAME)
    urgency_name = os.environ.get("AGENCY_OS_BETTERSTACK_URGENCY_NAME", DEFAULT_URGENCY_NAME)

    print("# Better Stack routing policy — operator review", file=sys.stderr)
    urgency = ensure_urgency(api_key, urgency_name)
    if not urgency:
        print("# ERROR: urgency create/fetch failed", file=sys.stderr)
        return 1
    urgency_id = int(urgency["id"])
    print(f"#   urgency '{urgency_name}' id={urgency_id}", file=sys.stderr)

    policy = ensure_policy(api_key, policy_name, urgency_id)
    if not policy:
        print("# ERROR: policy create/fetch failed", file=sys.stderr)
        return 1
    policy_id = int(policy["id"])
    print(f"#   policy  '{policy_name}' id={policy_id}", file=sys.stderr)

    monitors = list_monitors(api_key)
    heartbeats = list_heartbeats(api_key)

    applied = 0
    for mon in MONITOR_NAMES:
        m = _find(monitors, mon, "pronounceable_name")
        if not m:
            print(f"#   SKIP monitor '{mon}' — not found in BS", file=sys.stderr)
            continue
        if apply_policy_to_monitor(api_key, m["id"], policy_id):
            applied += 1
            print(f"#   applied policy to monitor '{mon}' (id={m['id']})", file=sys.stderr)
    for hb in HEARTBEAT_NAMES:
        h = _find(heartbeats, hb, "name")
        if not h:
            print(f"#   SKIP heartbeat '{hb}' — not found in BS", file=sys.stderr)
            continue
        if apply_policy_to_heartbeat(api_key, h["id"], policy_id):
            applied += 1
            print(f"#   applied policy to heartbeat '{hb}' (id={h['id']})", file=sys.stderr)

    print(f"# done — {applied} resource(s) PATCHed; existing routed unchanged.", file=sys.stderr)
    print(
        "# Phase 2 gate: routine + resolved → #execution requires a SECOND Slack\n"
        "# integration via BS Slack OAuth (Dave action). See\n"
        "# docs/runbooks/betterstack-slack-routing.md.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
