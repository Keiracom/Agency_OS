#!/usr/bin/env bash
# elliot_fleet_notify.sh — ExecStartPost Slack relay for elliot-agent.service (KEI-86).
#
# Posts a consolidated fleet status to #execution when the Elliot service
# starts. Dave directive 2026-05-20: fleet status is operational/peer info,
# NOT a CEO outcome/blocker/decision — it must NOT reach #ceo.
# Reads SLACK_BOT_TOKEN from the unit's EnvironmentFile.
#
# Usage:
#     scripts/elliot_fleet_notify.sh [delay_seconds]
#
# Args:
#     delay_seconds   — seconds to wait before posting (default: 20)
#
# Env:
#     SLACK_BOT_TOKEN — Slack bot token (injected via EnvironmentFile in unit)

set -euo pipefail

DELAY="${1:-20}"
# #execution (C0B3QB0K1GQ) — fleet status is peer/operational info, not a
# #ceo outcome/blocker/decision (Dave directive 2026-05-20).
CHANNEL="C0B3QB0K1GQ"

if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
    echo "[elliot_fleet_notify] ERROR: SLACK_BOT_TOKEN not set" >&2
    exit 1
fi

sleep "${DELAY}"

STATUS=$(systemctl --user is-active aiden-agent max-agent atlas-agent orion-agent scout-agent 2>&1 || true)

# Use Python for safe JSON serialisation (avoids quote-escaping in bash)
PAYLOAD=$(python3 -c "
import json, sys
status = sys.argv[1]
text = '[SYSTEM] [ELLIOT] Server online. Agent fleet status:\n' + status
print(json.dumps({'channel': '$CHANNEL', 'text': text}))
" "${STATUS}")

RESPONSE=$(curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "${PAYLOAD}")

echo "[elliot_fleet_notify] Slack response: ${RESPONSE}"

if echo "${RESPONSE}" | grep -q '"ok":true'; then
    echo "[elliot_fleet_notify] Posted fleet status to #execution"
    exit 0
else
    echo "[elliot_fleet_notify] ERROR: Slack post failed: ${RESPONSE}" >&2
    exit 1
fi
