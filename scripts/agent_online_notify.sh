#!/usr/bin/env bash
# agent_online_notify.sh — ExecStartPost Slack relay for *-agent.service units (KEI-86).
#
# Posts a [SYSTEM] online message to a Slack channel when an agent service starts.
# Designed to be called from ExecStartPost= in systemd unit files.
# Reads SLACK_BOT_TOKEN from the unit's EnvironmentFile.
#
# Usage:
#     scripts/agent_online_notify.sh <CALLSIGN> [delay_seconds] [channel_id]
#
# Args:
#     CALLSIGN        — uppercase callsign label for the message (e.g. ELLIOT)
#     delay_seconds   — seconds to wait before posting (default: 15)
#     channel_id      — Slack channel ID to post to (default: C0B3QB0K1GQ = #execution)
#
# Env:
#     SLACK_BOT_TOKEN — Slack bot token (injected via EnvironmentFile in unit)

set -euo pipefail

# DISABLED 2026-05-27 per Dave directive: stop all automated posting to #execution.
# Session-online alerts (Orion restarts etc) named explicitly in the kill-list.
# Script kept as no-op so ExecStartPost lines in unit files remain valid; restore
# by removing this early-exit block if the directive is reversed.
exit 0

CALLSIGN="${1:?usage: agent_online_notify.sh <CALLSIGN> [delay_seconds] [channel_id]}"
DELAY="${2:-15}"
CHANNEL="${3:-C0B3QB0K1GQ}"

if [[ -z "${SLACK_BOT_TOKEN:-}" ]]; then
    echo "[agent_online_notify] ERROR: SLACK_BOT_TOKEN not set" >&2
    exit 1
fi

sleep "${DELAY}"

PAYLOAD=$(printf '{"channel":"%s","text":"[SYSTEM] [%s] session online."}' \
    "${CHANNEL}" "${CALLSIGN}")

RESPONSE=$(curl -s -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "${PAYLOAD}")

echo "[agent_online_notify] Slack response: ${RESPONSE}"

if echo "${RESPONSE}" | grep -q '"ok":true'; then
    echo "[agent_online_notify] Posted [SYSTEM] [${CALLSIGN}] to channel ${CHANNEL}"
    exit 0
else
    echo "[agent_online_notify] ERROR: Slack post failed: ${RESPONSE}" >&2
    exit 1
fi
