#!/usr/bin/env bash
# agent_failover_notify.sh — KEI-125 #ceo escalation on agent service restart.
#
# Called from ExecStartPost in *-agent.service units. Reads NRestarts from the
# unit state. If NRestarts > 0 the unit was restarted (failover, not first
# boot), and we post to #ceo so Dave sees the failover in real time. On first
# boot (NRestarts == 0) this is a silent no-op — agent_online_notify.sh handles
# the #execution start announcement.
#
# Fail-open: any error here is logged + ignored. Failover should NOT block
# the agent from continuing to run.
#
# Usage:
#     scripts/agent_failover_notify.sh <CALLSIGN> [delay_seconds]
#
# Args:
#     CALLSIGN        — uppercase callsign label (ELLIOT, ATLAS, ...)
#     delay_seconds   — seconds to wait before posting (default: 5)
#
# Env:
#     SLACK_BOT_TOKEN — Slack bot token (injected via EnvironmentFile in unit)
#     CEO_CHANNEL_ID  — Slack channel ID for #ceo (default: env or hardcoded fallback)

set -uo pipefail   # NOT -e — fail-open per acceptance "#ceo post within 5s"

CALLSIGN="${1:?usage: agent_failover_notify.sh <CALLSIGN> [delay_seconds]}"
DELAY="${2:-5}"
CEO_CHANNEL="${CEO_CHANNEL_ID:-C09M2HE8XXX}"   # caller can override via env

# Lowercase callsign for systemctl unit name.
unit_name="$(echo "${CALLSIGN}" | tr '[:upper:]' '[:lower:]')-agent.service"

# Read NRestarts from the unit. If the binary or unit is missing,
# n_restarts defaults to 0 → no post → silent no-op (fail-open).
n_restarts="$(systemctl --user show "${unit_name}" --property=NRestarts --value 2>/dev/null || echo 0)"
n_restarts="${n_restarts:-0}"

if [[ "${n_restarts}" == "0" ]]; then
    # First boot — agent_online_notify.sh handles the #execution announcement.
    # Silent here so we don't double-post.
    exit 0
fi

if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
    echo "agent_failover_notify: WARNING — SLACK_BOT_TOKEN unset; #ceo post skipped" >&2
    exit 0
fi

# Acceptance: #ceo post within 5s of restart. Sleep up to DELAY seconds so
# the agent has time to actually re-establish before announcing.
sleep "${DELAY}"

# Compose the message — plain English per feedback_ceo_plain_english_summaries.
msg="[SYSTEM] ${CALLSIGN} agent restarted after failover (restart #${n_restarts}). Service is recovering; tool-call activity expected within 30s."

# Post to #ceo. Fail-open: any curl error is logged + ignored.
response="$(curl -sS -X POST 'https://slack.com/api/chat.postMessage' \
    -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H 'Content-Type: application/json; charset=utf-8' \
    -d "{\"channel\":\"${CEO_CHANNEL}\",\"text\":$(printf '%s' "${msg}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')}" \
    2>&1)" || true

if echo "${response}" | grep -q '"ok":true'; then
    echo "agent_failover_notify: posted #ceo failover notice for ${CALLSIGN} (restart #${n_restarts})"
else
    echo "agent_failover_notify: WARNING — Slack post failed: ${response:0:200}" >&2
fi

# Always exit 0 — failover notify must not block the service.
exit 0
