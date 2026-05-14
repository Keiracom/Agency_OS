#!/usr/bin/env python3
"""betterstack_routing_policy.py — Better Stack severity-based alert routing.

PR-C-v3 of the Better Stack bundle. Closes Linear KEI-20 / bd Agency_OS-lrcvie.

Per Dave directive ts ~1778618200 (re-stated by Elliot ts ~1778741000):
  - Critical incidents (service down, heartbeat missed) → #ceo.
  - Routine + resolved notifications → #execution.

Two policies, two integrations:

| Policy                       | Step target               | Attached to                  |
|------------------------------|---------------------------|------------------------------|
| Agency OS — Critical (PR-C)  | slack_integration  #ceo   | monitors.policy_id           |
|                              |                           | heartbeats.policy_id         |
| Agency OS — Routine (PR-C-v3)| slack_integration #execution | monitors.expiration_policy_id |

Heartbeat resolved/recovery routing — BS API limitation: heartbeats expose
only `policy_id` (no expiration_policy_id). Heartbeat-recovered events flow
through the same incident-thread as the original heartbeat-missed alert, so
the recovery notification lands in whichever channel the critical policy
targets. See runbook §"Heartbeat-recovery routing limitation".

Schema empirically re-probed 2026-05-14 against BS v2 API. The opaque-schema
note from PR-C-v2 docs is now stale — `step_members:[{"type":"slack_integration",
"id":<int>}]` returns rc=201 with that exact step shape echoed back. The
prior probe likely sent the body before a valid urgency_id existed; the
"can't be blank" error masked the schema discovery.

Phase progression:
  - Phase 1 (PR-C-v2, shipped): one policy + all_slack_integrations step.
    Worked because the team had exactly one Slack integration (#ceo).
  - Phase 2 (this PR, PR-C-v3): swap to integration-specific step types so
    adding the #execution integration doesn't broadcast to BOTH channels.
    When #execution integration is present, create the second policy.

Idempotency contract:
  - Urgency matched by `name`. Created if missing, reused otherwise.
  - Policy matched by `name`. Reused if present; PATCHed if step drift
    detected. Drift = step type / urgency_id / step_member shape differs.
  - Resource policy_id (+ expiration_policy_id for monitors) PATCHed only
    when missing or different from desired.

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_routing_policy.py

Env overrides (tests + alt names):
    AGENCY_OS_BETTERSTACK_API_BASE              — API root
    AGENCY_OS_BETTERSTACK_CRITICAL_POLICY_NAME  — default "Agency OS — Critical incidents"
    AGENCY_OS_BETTERSTACK_CRITICAL_URGENCY_NAME — default "Agency OS — Critical"
    AGENCY_OS_BETTERSTACK_ROUTINE_POLICY_NAME   — default "Agency OS — Routine + Resolved"
    AGENCY_OS_BETTERSTACK_ROUTINE_URGENCY_NAME  — default "Agency OS — Routine"
    AGENCY_OS_BETTERSTACK_CEO_CHANNEL_ID        — default C0B2PM3TV0B  (#ceo)
    AGENCY_OS_BETTERSTACK_EXECUTION_CHANNEL_ID  — default C0B3QB0K1GQ  (#execution)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

API_BASE_DEFAULT = "https://uptime.betterstack.com/api/v2"

DEFAULT_CRITICAL_POLICY_NAME = "Agency OS — Critical incidents"
DEFAULT_CRITICAL_URGENCY_NAME = "Agency OS — Critical"
DEFAULT_ROUTINE_POLICY_NAME = "Agency OS — Routine + Resolved"
DEFAULT_ROUTINE_URGENCY_NAME = "Agency OS — Routine"

CEO_CHANNEL_ID_DEFAULT = "C0B2PM3TV0B"  # #ceo
EXECUTION_CHANNEL_ID_DEFAULT = "C0B3QB0K1GQ"  # #execution

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
        print(
            f"[bs-routing] HTTP {exc.code} on {method} {url}: {body_text[:200]}",
            file=sys.stderr,
        )
        return None
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"[bs-routing] network/parse error on {method} {url}: {exc}", file=sys.stderr)
        return None


def list_slack_integrations(api_key: str) -> list[dict]:
    resp = _request("GET", "/slack-integrations?per_page=100", api_key)
    return (resp or {}).get("data", []) or []


def find_integration_by_channel(integrations: list[dict], channel_id: str) -> dict | None:
    for it in integrations:
        if it.get("attributes", {}).get("slack_channel_id") == channel_id:
            return it
    return None


def ensure_urgency(api_key: str, name: str) -> dict | None:
    """Find by name or POST. Email-on, push/sms/call off (Slack covers the rest)."""
    resp = _request("GET", "/urgencies?per_page=100", api_key)
    for u in (resp or {}).get("data", []) or []:
        if u.get("attributes", {}).get("name") == name:
            return u
    body = {"name": name, "email": True, "push": False, "sms": False, "call": False}
    return (_request("POST", "/urgencies", api_key, body) or {}).get("data")


def _desired_step(urgency_id: int, integration_id: int) -> dict:
    return {
        "type": "escalation",
        "wait_before": 0,
        "urgency_id": urgency_id,
        "step_members": [{"type": "slack_integration", "id": integration_id}],
    }


def _step_drift(existing_steps: list[dict], desired_urgency_id: int, integration_id: int) -> bool:
    """True iff steps don't match our desired single escalation step."""
    if len(existing_steps) != 1:
        return True
    s = existing_steps[0]
    if s.get("type") != "escalation":
        return True
    if s.get("urgency_id") != desired_urgency_id:
        return True
    members = s.get("step_members") or []
    if len(members) != 1:
        return True
    m = members[0]
    return not (m.get("type") == "slack_integration" and int(m.get("id", 0)) == integration_id)


def ensure_policy(api_key: str, name: str, urgency_id: int, integration_id: int) -> dict | None:
    """Match by name. Create if missing; PATCH if step drift."""
    resp = _request("GET", "/policies?per_page=100", api_key)
    existing = (resp or {}).get("data", []) or []
    step = _desired_step(urgency_id, integration_id)
    for p in existing:
        if p.get("attributes", {}).get("name") == name:
            if not _step_drift(
                p.get("attributes", {}).get("steps") or [], urgency_id, integration_id
            ):
                return p
            patched = _request("PATCH", f"/policies/{p.get('id')}", api_key, {"steps": [step]})
            return (patched or {}).get("data") or p
    created = _request("POST", "/policies", api_key, {"name": name, "steps": [step]})
    return (created or {}).get("data")


def apply_policy_field(
    api_key: str, kind: str, resource_id: str, field: str, policy_id: int
) -> bool:
    """PATCH resource[field] = policy_id if missing/different. Returns True if changed."""
    cur = _request("GET", f"/{kind}/{resource_id}", api_key)
    if (cur or {}).get("data", {}).get("attributes", {}).get(field) == policy_id:
        return False
    return _request("PATCH", f"/{kind}/{resource_id}", api_key, {field: policy_id}) is not None


def list_monitors(api_key: str) -> list[dict]:
    return (_request("GET", "/monitors?per_page=100", api_key) or {}).get("data", []) or []


def list_heartbeats(api_key: str) -> list[dict]:
    return (_request("GET", "/heartbeats?per_page=100", api_key) or {}).get("data", []) or []


def _find(records: list[dict], name: str, attr: str) -> dict | None:
    return next((r for r in records if r.get("attributes", {}).get(attr) == name), None)


def apply_critical(
    api_key: str, policy_id: int, monitors: list[dict], heartbeats: list[dict]
) -> int:
    """Attach critical policy to monitors.policy_id + heartbeats.policy_id. Returns # changed."""
    applied = 0
    for name in MONITOR_NAMES:
        m = _find(monitors, name, "pronounceable_name")
        if not m:
            print(f"#   SKIP monitor '{name}' — not found in BS", file=sys.stderr)
            continue
        if apply_policy_field(api_key, "monitors", m["id"], "policy_id", policy_id):
            applied += 1
            print(f"#   applied critical to monitor '{name}' (id={m['id']})", file=sys.stderr)
    for name in HEARTBEAT_NAMES:
        h = _find(heartbeats, name, "name")
        if not h:
            print(f"#   SKIP heartbeat '{name}' — not found in BS", file=sys.stderr)
            continue
        if apply_policy_field(api_key, "heartbeats", h["id"], "policy_id", policy_id):
            applied += 1
            print(f"#   applied critical to heartbeat '{name}' (id={h['id']})", file=sys.stderr)
    return applied


def apply_routine(api_key: str, policy_id: int, monitors: list[dict]) -> int:
    """Attach routine policy to monitors.expiration_policy_id. Heartbeats skipped — BS API
    limitation (heartbeats expose only policy_id). See runbook §heartbeat-recovery."""
    applied = 0
    for name in MONITOR_NAMES:
        m = _find(monitors, name, "pronounceable_name")
        if not m:
            continue
        if apply_policy_field(api_key, "monitors", m["id"], "expiration_policy_id", policy_id):
            applied += 1
            print(
                f"#   applied routine to monitor '{name}'.expiration_policy_id (id={m['id']})",
                file=sys.stderr,
            )
    return applied


def main() -> int:
    api_key = os.environ.get("BETTERSTACK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BETTERSTACK_API_KEY env not set", file=sys.stderr)
        return 2

    crit_policy_name = os.environ.get(
        "AGENCY_OS_BETTERSTACK_CRITICAL_POLICY_NAME", DEFAULT_CRITICAL_POLICY_NAME
    )
    crit_urgency_name = os.environ.get(
        "AGENCY_OS_BETTERSTACK_CRITICAL_URGENCY_NAME", DEFAULT_CRITICAL_URGENCY_NAME
    )
    routine_policy_name = os.environ.get(
        "AGENCY_OS_BETTERSTACK_ROUTINE_POLICY_NAME", DEFAULT_ROUTINE_POLICY_NAME
    )
    routine_urgency_name = os.environ.get(
        "AGENCY_OS_BETTERSTACK_ROUTINE_URGENCY_NAME", DEFAULT_ROUTINE_URGENCY_NAME
    )
    ceo_channel = os.environ.get("AGENCY_OS_BETTERSTACK_CEO_CHANNEL_ID", CEO_CHANNEL_ID_DEFAULT)
    exec_channel = os.environ.get(
        "AGENCY_OS_BETTERSTACK_EXECUTION_CHANNEL_ID", EXECUTION_CHANNEL_ID_DEFAULT
    )

    print("# Better Stack severity-routing — wire-in", file=sys.stderr)

    integrations = list_slack_integrations(api_key)
    ceo_integration = find_integration_by_channel(integrations, ceo_channel)
    exec_integration = find_integration_by_channel(integrations, exec_channel)

    if not ceo_integration:
        print(
            f"# ERROR: no BS Slack integration found pointing at #ceo ({ceo_channel}).\n"
            "# Critical-policy wiring cannot proceed without it. See runbook for OAuth steps.",
            file=sys.stderr,
        )
        return 1
    ceo_id = int(ceo_integration["id"])
    print(f"#   #ceo integration found id={ceo_id}", file=sys.stderr)

    # Critical policy — always wired.
    crit_urgency = ensure_urgency(api_key, crit_urgency_name)
    if not crit_urgency:
        print("# ERROR: critical urgency create/fetch failed", file=sys.stderr)
        return 1
    crit_urgency_id = int(crit_urgency["id"])
    crit_policy = ensure_policy(api_key, crit_policy_name, crit_urgency_id, ceo_id)
    if not crit_policy:
        print("# ERROR: critical policy create/fetch failed", file=sys.stderr)
        return 1
    crit_policy_id = int(crit_policy["id"])
    print(f"#   critical policy '{crit_policy_name}' id={crit_policy_id} → #ceo", file=sys.stderr)

    monitors = list_monitors(api_key)
    heartbeats = list_heartbeats(api_key)
    crit_applied = apply_critical(api_key, crit_policy_id, monitors, heartbeats)
    print(f"#   critical: {crit_applied} resource(s) PATCHed", file=sys.stderr)

    # Routine policy — gated on #execution integration existing.
    if not exec_integration:
        print(
            f"# GATE: no BS Slack integration found pointing at #execution ({exec_channel}).\n"
            "# Routine-policy wiring DEFERRED. Operator must complete BS Slack OAuth for\n"
            "# the #execution channel. See docs/runbooks/betterstack-slack-routing.md.\n"
            "# Re-run this script after OAuth completes — it's idempotent.",
            file=sys.stderr,
        )
        return 0

    exec_id = int(exec_integration["id"])
    print(f"#   #execution integration found id={exec_id}", file=sys.stderr)

    routine_urgency = ensure_urgency(api_key, routine_urgency_name)
    if not routine_urgency:
        print("# ERROR: routine urgency create/fetch failed", file=sys.stderr)
        return 1
    routine_urgency_id = int(routine_urgency["id"])
    routine_policy = ensure_policy(api_key, routine_policy_name, routine_urgency_id, exec_id)
    if not routine_policy:
        print("# ERROR: routine policy create/fetch failed", file=sys.stderr)
        return 1
    routine_policy_id = int(routine_policy["id"])
    print(
        f"#   routine policy '{routine_policy_name}' id={routine_policy_id} → #execution",
        file=sys.stderr,
    )
    routine_applied = apply_routine(api_key, routine_policy_id, monitors)
    print(
        f"#   routine: {routine_applied} monitor(s) PATCHed (.expiration_policy_id)",
        file=sys.stderr,
    )
    print(
        "#   note: heartbeats keep critical-only routing (BS API exposes no\n"
        "#         expiration_policy_id on heartbeats). Heartbeat-recovery alerts\n"
        "#         flow through the same incident thread → #ceo.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
