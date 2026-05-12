# Better Stack — Slack Alert Routing (Operator Runbook)

## Why this is operator-action, not automatable

Better Stack's Slack integration is OAuth-scoped: a new BS-side Slack integration must be authorised through the BS dashboard's OAuth flow. The BS v2 API does not expose integration creation endpoints, so the script at `scripts/orchestrator/betterstack_slack_routing.py` is read-only — it verifies whether the integration exists, and prints these instructions when it does not.

The notification policy that references the integration (PR-C-v2, follow-up) can be API-driven once the integration_id is known. Policy step JSON schema for `type=slack` was empirically opaque on the BS v2 API as of 2026-05-12 (422 with vague "allowed_values: {type: slack}" on every field combo probed), so PR-C-v2 will need fresh probing once a real integration_id exists to reference.

## Current state (2026-05-12)

| Integration | Channel | id |
|---|---|---|
| Existing (active) | `#ceo` (C0B2PM3TV0B) | 102756 |
| **Required for PR-C-v2** | `#alerts` (C0B2EJU53EK) | _operator must create_ |

The `#ceo` integration is what routes today's incidents from BS to `#ceo` via the BS-installed Slack app. Per Dave's role-lock (2026-05-11), `#ceo` is Dave-Elliot exclusive, so flooding it with monitor/heartbeat alerts is wrong. PR-C-v2 will route alerts to `#alerts` instead.

## Operator steps

1. **Open** https://uptime.betterstack.com/team/integrations/slack
2. **Click** "Add Slack workspace" — opens Slack OAuth consent page in a new tab.
3. **Authorise** the Keiracom workspace for the Better Stack app. Requires workspace-admin rights (Dave).
4. **Select** `#alerts` (channel id `C0B2EJU53EK`) as the default channel when prompted. Leave `on_call_notifications` enabled; `integration_type=verbose` matches the existing pattern.
5. **Save** — BS dashboard now shows a second Slack integration row.
6. **Verify** by running:
   ```bash
   BETTERSTACK_API_KEY=<key> python3 scripts/orchestrator/betterstack_slack_routing.py
   ```
   The script should now print `READY — #alerts integration found (id=<new-id>)`.

## After verification

- File PR-C-v2 (Aiden) to wire a Better Stack notification policy referencing the new integration_id + apply it to all 5 heartbeats (PR-A) + 3 uptime monitors (PR-B).
- Manual smoke test: curl-fail the `agency-os-discovery` heartbeat and confirm a `#alerts` Slack post lands within 60s.

## Why we keep email AND add Slack

Defense in depth. Email is the BS default and survives Slack app outages. Slack adds real-time visibility. PR-C-v2 will not remove email — it will add Slack as a parallel step.

## Why this isn't a `/schedule` or systemd timer

The integration is a one-time setup (per-workspace), not a recurring check. The verify-only script is an operator-invoked diagnostic, not a scheduled job. Running it on a timer would just produce noise once the integration exists.

## Related

- `scripts/orchestrator/betterstack_setup.py` — heartbeats bootstrap (PR-A, merged)
- `scripts/orchestrator/betterstack_uptime_monitors.py` — uptime monitors (PR-B, merged + PR #788 fixes)
- `scripts/orchestrator/betterstack_slack_routing.py` — verify-only readiness check (PR-C, this file)
- PR-C-v2 (future) — automated policy wire-in once OAuth done
- PR-D — public status page (separate, planned)
