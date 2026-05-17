# Better Stack — Severity-Based Alert Routing (Operator Runbook)

Owner: orion · Linear: [KEI-20](https://linear.app/keiracom/issue/KEI-20) · Beads: Agency_OS-lrcvie

## What this delivers

Severity-routing for Better Stack alerts per Dave directive ts ~1778618200 (re-stated by Elliot ts ~1778741000):

| Severity                                          | Channel       | BS mechanism                                  |
|---------------------------------------------------|---------------|-----------------------------------------------|
| Critical (service down, heartbeat missed)         | `#ceo`        | `policy_id` on monitors + heartbeats          |
| Routine + resolved (incident recovery)            | `#execution`  | `expiration_policy_id` on monitors            |

Two notification policies, each with a `slack_integration` step targeting one specific BS Slack integration by id.

## Why this is operator-gated, not fully automatable

Better Stack v2 API does NOT expose Slack integration creation. The OAuth flow runs through the BS dashboard. Once an integration exists, everything else (policy create + resource attachment) is API-driven and idempotent.

## Current state (run the readiness probe)

```bash
set -a; source /home/elliotbot/.config/agency-os/.env; set +a
python3 scripts/orchestrator/betterstack_slack_routing.py
```

The probe lists existing BS Slack integrations and reports:
- `READY — #ceo integration found` ← required for critical-policy wiring
- `READY — #execution integration found` ← required for routine-policy wiring
- `NOT READY` / `DEFERRED` lines with OAuth instructions for any missing integration

## OAuth dance (per missing channel)

1. Open https://uptime.betterstack.com/team/integrations/slack
2. Click "Add Slack workspace" — opens Slack OAuth in a new tab.
3. Authorise the Keiracom workspace for the Better Stack app (requires workspace-admin).
4. When prompted for the default channel, select the target channel:
   - `#ceo` → channel id `C0B2PM3TV0B`
   - `#execution` → channel id `C0B3QB0K1GQ`
   Leave `on_call_notifications` enabled; `integration_type=verbose` matches the existing pattern.
5. Save. BS dashboard now shows an additional Slack integration row.
6. Re-run the readiness probe to confirm.

## Wire the policies (after OAuth)

```bash
python3 scripts/orchestrator/betterstack_routing_policy.py
```

This script is idempotent:

1. Looks up the `#ceo` integration (channel `C0B2PM3TV0B`) by id.
2. Creates / reuses urgency `Agency OS — Critical`.
3. Creates / reuses policy `Agency OS — Critical incidents` with `step_members:[{type:slack_integration, id:<#ceo_id>}]`. PATCHes if step drift detected (e.g. legacy `all_slack_integrations` from PR-C-v2 phase-1).
4. Attaches the critical policy to all monitors' `policy_id` + all heartbeats' `policy_id`.
5. If `#execution` integration exists: creates / reuses urgency `Agency OS — Routine` + policy `Agency OS — Routine + Resolved` targeting that integration by id. Attaches it to monitors' `expiration_policy_id`. **Heartbeat-recovery routing limitation below.**
6. If `#execution` integration is missing: logs `GATE: routine-policy wiring DEFERRED`, exits 0. Re-run after OAuth.

## Heartbeat-recovery routing limitation

The BS API exposes `expiration_policy_id` only on monitors, not on heartbeats. When a heartbeat starts firing again after a missed-period incident, the recovery notification rides through the same incident thread → the `policy_id` channel (`#ceo`), not `#execution`.

If/when BS exposes a recovery-policy field on heartbeats, the routine policy will attach there too. For now, monitor recoveries land in `#execution` (matching Dave's spec); heartbeat recoveries continue to land in `#ceo`.

## Manual smoke test

1. **Critical → #ceo**: curl-fail the `agency-os-discovery` heartbeat (let one period elapse without a heartbeat call). Within `period + grace` seconds an incident opens and a `#ceo` Slack post lands.
2. **Routine → #execution**: trigger an `agencyxos.ai` monitor failure (e.g., temporary firewall rule). When the monitor recovers, the resolved notification posts to `#execution`.

## Why we keep email AND add Slack

Defense in depth. Email is the BS default and survives Slack app outages. The Slack policies do not remove email — they add Slack as a parallel step.

## Why this isn't a `/schedule` or systemd timer

Notification policies are configuration, not workload. Once wired they don't drift on their own. The wiring script is operator-invoked after each OAuth event (one-time per channel). Running it on a timer would just produce noise.

## Empirical schema (probed 2026-05-14 against BS v2 API)

```json
{
  "name": "Agency OS — Critical incidents",
  "steps": [{
    "type": "escalation",
    "wait_before": 0,
    "urgency_id": <id from POST /urgencies>,
    "step_members": [{"type": "slack_integration", "id": <integration_id>}]
  }]
}
```

The 2026-05-12 probe note ("Slack integration step JSON schema opaque, 422 on every combo") is now stale — the rejection was caused by sending the body before a valid urgency_id existed. With a real urgency_id, `step_members:[{type:slack_integration, id:<int>}]` returns rc=201 with the exact shape echoed back.

## Related

- `scripts/orchestrator/betterstack_setup.py` — heartbeats bootstrap (PR-A, merged)
- `scripts/orchestrator/betterstack_uptime_monitors.py` — uptime monitors (PR-B, merged + PR #788 fixes)
- `scripts/orchestrator/betterstack_slack_routing.py` — readiness probe (KEI-20)
- `scripts/orchestrator/betterstack_routing_policy.py` — severity-routing wire-in (KEI-20)
- `scripts/orchestrator/betterstack_status_page.py` — public status page (PR-D, merged)

## Migration notes (from PR-C-v2 phase-1)

The phase-1 policy used `step_members:[{type:all_slack_integrations}]`. When you re-run `betterstack_routing_policy.py` from this PR, the step-drift check fires and PATCHes the existing policy to `slack_integration`-targeted form. The policy id is preserved (resource attachments survive); only the step body changes.
