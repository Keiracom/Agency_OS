#!/usr/bin/env python3
"""betterstack_slack_routing.py — Better Stack Slack-routing readiness check.

Operator diagnostic for the Better Stack severity-routing pipeline (KEI-20).
Lists the BS Slack integrations on the team and reports which channels are
already wired for the alert-routing policies built by
`scripts/orchestrator/betterstack_routing_policy.py`.

Per Dave directive ts ~1778618200 (re-stated by Elliot ts ~1778741000):
critical incidents → #ceo, routine + resolved → #execution.

Target channels for the two policies:
  - #ceo       (C0B2PM3TV0B)  — must exist for critical wiring
  - #execution (C0B3QB0K1GQ)  — must exist for routine wiring (gated on OAuth)

The Better Stack v2 API does NOT expose Slack integration creation — that
requires OAuth via the BS dashboard. This script just verifies which side of
the gate we're on and prints operator instructions when one or both are
missing.

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_slack_routing.py

Env overrides (tests):
    AGENCY_OS_BETTERSTACK_API_BASE — override API root (default uptime.betterstack.com/api/v2)
    AGENCY_OS_BETTERSTACK_CEO_CHANNEL_ID         — default C0B2PM3TV0B
    AGENCY_OS_BETTERSTACK_EXECUTION_CHANNEL_ID   — default C0B3QB0K1GQ

Always exits 0 — operator-diagnostic, never blocks anything.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

CEO_CHANNEL_ID_DEFAULT = "C0B2PM3TV0B"
EXECUTION_CHANNEL_ID_DEFAULT = "C0B3QB0K1GQ"

API_BASE_DEFAULT = "https://uptime.betterstack.com/api/v2"


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _api_base() -> str:
    return os.environ.get("AGENCY_OS_BETTERSTACK_API_BASE", API_BASE_DEFAULT)


def _ceo_channel_id() -> str:
    return os.environ.get("AGENCY_OS_BETTERSTACK_CEO_CHANNEL_ID", CEO_CHANNEL_ID_DEFAULT)


def _execution_channel_id() -> str:
    return os.environ.get(
        "AGENCY_OS_BETTERSTACK_EXECUTION_CHANNEL_ID", EXECUTION_CHANNEL_ID_DEFAULT
    )


def list_slack_integrations(api_key: str) -> list[dict]:
    """Return all BS Slack integrations for this team. Empty on error."""
    url = f"{_api_base()}/slack-integrations?per_page=50"
    req = urllib.request.Request(url, headers=_auth_headers(api_key), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read() or "null")
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        print(f"[bs-slack] integrations list failed: {exc}", file=sys.stderr)
        return []
    return body.get("data", []) or []


def find_integration_by_channel_id(integrations: list[dict], channel_id: str) -> dict | None:
    """Return the integration record pointing at the given Slack channel id, else None."""
    for it in integrations:
        if it.get("attributes", {}).get("slack_channel_id") == channel_id:
            return it
    return None


def print_oauth_runbook(channel_name: str, channel_id: str) -> None:
    """Operator-facing instructions when a required integration is missing."""
    print(
        f"# Better Stack Slack-routing — OAuth required for {channel_name}\n"
        "#\n"
        "# No existing BS Slack integration points at "
        f"{channel_name} (channel {channel_id}).\n"
        "# Operator must complete BS's Slack OAuth flow via the dashboard:\n"
        "#\n"
        "#   1. Open https://uptime.betterstack.com/team/integrations/slack\n"
        "#   2. Click 'Add Slack workspace' (OAuth flow opens Slack auth page)\n"
        "#   3. Authorise the Keiracom workspace for the Better Stack app\n"
        f"#   4. When prompted for default channel, select {channel_name} (id {channel_id})\n"
        "#   5. Save\n"
        "#   6. Re-run scripts/orchestrator/betterstack_routing_policy.py — it's\n"
        "#      idempotent and will pick up the new integration_id.\n"
        "#\n"
        "# See docs/runbooks/betterstack-slack-routing.md for the full procedure.\n",
        file=sys.stderr,
    )


def report(integrations: list[dict]) -> int:
    """Print findings to stderr; return 0 (operator-diagnostic, never blocks)."""
    ceo_id = _ceo_channel_id()
    exec_id = _execution_channel_id()

    print("# Better Stack Slack-routing — readiness check", file=sys.stderr)
    print(
        f"# Looking for integrations on #ceo ({ceo_id}) and #execution ({exec_id})",
        file=sys.stderr,
    )
    print(f"# Existing slack integrations: {len(integrations)}", file=sys.stderr)
    for it in integrations:
        attrs = it.get("attributes", {})
        print(
            f"#   id={it.get('id')} channel={attrs.get('slack_channel_name')} "
            f"({attrs.get('slack_channel_id')}) status={attrs.get('slack_status')}",
            file=sys.stderr,
        )

    ceo_match = find_integration_by_channel_id(integrations, ceo_id)
    exec_match = find_integration_by_channel_id(integrations, exec_id)

    if ceo_match:
        print(f"# READY — #ceo integration found (id={ceo_match.get('id')})", file=sys.stderr)
    else:
        print("# NOT READY — no #ceo integration found", file=sys.stderr)
        print_oauth_runbook("#ceo", ceo_id)

    if exec_match:
        print(
            f"# READY — #execution integration found (id={exec_match.get('id')}).\n"
            "# Severity-routing fully wireable: betterstack_routing_policy.py will\n"
            "# create the routine policy and attach it to monitors.expiration_policy_id.",
            file=sys.stderr,
        )
    else:
        print(
            "# DEFERRED — no #execution integration found. Routine + resolved\n"
            "# routing is gated until OAuth completes.",
            file=sys.stderr,
        )
        print_oauth_runbook("#execution", exec_id)

    return 0


def main() -> int:
    api_key = os.environ.get("BETTERSTACK_API_KEY", "").strip()
    if not api_key:
        print("ERROR: BETTERSTACK_API_KEY env not set", file=sys.stderr)
        return 0  # operator-diagnostic, never blocks
    integrations = list_slack_integrations(api_key)
    return report(integrations)


if __name__ == "__main__":
    sys.exit(main())
