#!/usr/bin/env python3
"""betterstack_slack_routing.py — Better Stack Slack-routing readiness check.

PR-C (verify-only iteration) of the Better Stack bundle. Original scope was
"create notification policy + wire all monitors/heartbeats to Slack #alerts",
but the BS v2 API has two blockers preventing full automation:

  1. Slack integrations are OAuth-scoped: a NEW BS Slack integration pointing
     at #alerts must be operator-created via the BS dashboard's OAuth flow.
     The v2 API doesn't expose integration creation.
  2. Policy step JSON schema (for type="slack" / "team_email" / "webhook")
     returns vague "allowed_values: {type: X}" errors on every field combo
     probed empirically 2026-05-12. Cannot ratify schema without working
     example, which depends on (1).

So this PR ships a READ-ONLY verification script that:
  - Lists existing BS Slack integrations + their channel routing.
  - Detects whether an #alerts integration exists (channel C0B2EJU53EK).
  - Prints either "READY for policy build" with the integration_id, OR
    "OAuth required" with explicit operator steps.

Once an operator completes the OAuth dance and re-runs this script with a
positive verdict, PR-C-v2 wires the actual notification policy referencing
the now-known integration_id.

Usage:
    BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_slack_routing.py

Env overrides (tests):
    AGENCY_OS_BETTERSTACK_API_BASE — override API root (default uptime.betterstack.com/api/v2)

Always exits 0 — operator-diagnostic, never blocks anything.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Target Slack channel for alerts (verified against scripts/slack_relay.py CHANNELS map).
ALERTS_CHANNEL_ID = "C0B2EJU53EK"
ALERTS_CHANNEL_NAME = "#alerts"

API_BASE_DEFAULT = "https://uptime.betterstack.com/api/v2"


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _api_base() -> str:
    return os.environ.get("AGENCY_OS_BETTERSTACK_API_BASE", API_BASE_DEFAULT)


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


def find_alerts_integration(integrations: list[dict]) -> dict | None:
    """Return the integration record pointing at #alerts, else None."""
    for it in integrations:
        attrs = it.get("attributes", {})
        if attrs.get("slack_channel_id") == ALERTS_CHANNEL_ID:
            return it
        if attrs.get("slack_channel_name") in {ALERTS_CHANNEL_NAME, "alerts"}:
            return it
    return None


def print_oauth_runbook() -> None:
    """Operator-facing instructions when no #alerts integration exists."""
    print(
        "# Better Stack Slack-routing — operator OAuth required\n"
        "#\n"
        "# No existing BS Slack integration points at #alerts (channel\n"
        f"# {ALERTS_CHANNEL_ID}). To enable PR-C-v2 (policy wire-in), an operator\n"
        "# must complete BS's Slack OAuth flow via the dashboard. Steps:\n"
        "#\n"
        "#   1. Open https://uptime.betterstack.com/team/integrations/slack\n"
        "#   2. Click 'Add Slack workspace' (OAuth flow opens Slack auth page)\n"
        "#   3. Authorise the Keiracom workspace for the Better Stack app\n"
        f"#   4. When prompted for default channel, select #alerts (id {ALERTS_CHANNEL_ID})\n"
        "#   5. Save\n"
        "#   6. Re-run this script — it should now report READY with the new\n"
        "#      integration_id for PR-C-v2 to consume\n"
        "#\n"
        "# See docs/runbooks/betterstack-slack-routing.md for the full procedure.\n",
        file=sys.stderr,
    )


def report(integrations: list[dict]) -> int:
    """Print findings to stderr; return advisory exit-code value (always-0 in main)."""
    print("# Better Stack Slack-routing — readiness check", file=sys.stderr)
    print(f"# Looking for an integration pointing at {ALERTS_CHANNEL_NAME} ({ALERTS_CHANNEL_ID})", file=sys.stderr)
    print(f"# Existing slack integrations: {len(integrations)}", file=sys.stderr)
    for it in integrations:
        attrs = it.get("attributes", {})
        print(
            f"#   id={it.get('id')} channel={attrs.get('slack_channel_name')} "
            f"({attrs.get('slack_channel_id')}) status={attrs.get('slack_status')}",
            file=sys.stderr,
        )

    match = find_alerts_integration(integrations)
    if match:
        print(
            f"# READY — #alerts integration found (id={match.get('id')}). "
            f"PR-C-v2 can wire the notification policy referencing this id.",
            file=sys.stderr,
        )
        return 0
    print("# NOT READY — no #alerts integration found.", file=sys.stderr)
    print_oauth_runbook()
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
