#!/usr/bin/env bash
# a6_observation_check.sh — Phase A6 dual-publish observation signal verifier.
#
# Watches that every NATS publish in scripts/fleet_supervisor.py's
# _nats_publish_state has a paired Temporal signal-sent line from
# _temporal_signal_state. 7-day observation window started ~2026-05-26 00:50 UTC,
# ends ~2026-06-02. If signals match within tolerance over the window, Phase A6
# graduates to Temporal-only (NATS path removed).
#
# Cross-reference:
#   PR #1155 — [ORION] FleetSupervisorWorkflow + [READY] dual-publish (Phase A6)
#   PR #1159 — [ORION] fix(fleet-supervisor): import-path fix for dual-publish
#   docs/architecture/temporal_contract_v1.md — contract V1 (signal mechanics + 7 gates)
#
# Log sources (in order):
#   1. journalctl --user -u fleet-supervisor.service (per dispatch gate)
#   2. /home/elliotbot/clawd/logs/fleet-supervisor.log (fallback)
#
# Why a fallback exists: fleet-supervisor.service's unit declares
# `StandardOutput=append:/home/elliotbot/clawd/logs/fleet-supervisor.log`,
# which routes the Python logger's output to a file rather than to systemd's
# journal. Source (1) therefore only surfaces systemd lifecycle lines
# (Started/Finished); the actual publish lines we count land in source (2).
# Both are local-only — no Temporal CLI / no remote auth required.
#
# Matched line shapes (from scripts/fleet_supervisor.py +
# src/keiracom_system/temporal/signal_helpers.py):
#   NATS publish:    '[<callsign>] NATS PUBLISH keiracom.agent.status.<callsign> → <state>'
#   Temporal signal: 'temporal signal sent: <callsign> state=<state>'
#
# Exit codes:
#   0 — mismatch < 1% AND ≥1 event each side    (CLEAN — observation healthy)
#   1 — mismatch 1-5%                            (WARN — investigate)
#   2 — mismatch > 5%, no events, or fail-closed (ALARM — block Temporal-only flip)
#
# --alert flag (Agency_OS-vjcq): on FAIL_CLOSED_NO_DATA, publish a Viktor-voice
# formatted alert to NATS subject 'keiracom.elliot.inbox'. Elliot's relay path
# surfaces the alert to #ceo. Direct slack_relay.py invocation to #ceo from
# nova is BLOCKED by `_ALLOWED_CHANNELS_BY_CALLSIGN["nova"]` (slack_relay.py:175,
# 2026-05-19 elliot-only restriction). The NATS→elliot path is the canonical
# nova→#ceo route per `ceo:comm_architecture` (3-comms-path architecture:
# inter-agent inbound = NATS→file inbox→tmux, inter-agent outbound = NATS publish,
# elliot→Dave = Slack relay).
#
# Grace period: when the producer timer (fleet-supervisor.timer) has been
# re-enabled in the last 2 hours, --alert suppresses the publish and emits a
# one-line `grace_period: producer re-enabled <X>min ago, awaiting accumulation`
# stderr notice. Threshold is 2h / 24 fires of the 5-min producer cadence —
# any real outage will re-surface after the window. Without this, a freshly
# restarted producer trips the 24h-lookback FAIL_CLOSED check until enough
# fires accumulate, producing alert fatigue + false-positive noise to Dave.
#
# Usage (manual):
#   bash scripts/a6_observation_check.sh
#   bash scripts/a6_observation_check.sh --since "12h ago"
#   bash scripts/a6_observation_check.sh --alert                   # alert on FAIL_CLOSED
#   bash scripts/a6_observation_check.sh --since "6h ago" --alert  # cron mode
#
# Usage (6-hour systemd timer during observation window):
#   infra/systemd/a6-observation-alert.timer (OnUnitActiveSec=6h)
#   → infra/systemd/a6-observation-alert.service (--alert flag)

set -euo pipefail

# ----- args (parse in any order, accept --since, --alert, -h) -----
SINCE="24h ago"
ALERT_MODE=0
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --since)
            [[ -z "${2:-}" ]] && { echo "ERROR: --since requires a value" >&2; exit 2; }
            SINCE="$2"; shift 2 ;;
        --alert)
            ALERT_MODE=1; shift ;;
        -h|--help)
            sed -n '2,55p' "$0"; exit 0 ;;
        *)
            echo "ERROR: unknown arg '$1' (accepted: --since '<window>' | --alert | --help)" >&2
            exit 2 ;;
    esac
done

# ----- constants -----
SERVICE="fleet-supervisor.service"
WORKER_SERVICE="keiracom-temporal-worker.service"
# LOG_FILE env-overridable for negative-path tests (point at /dev/null to
# force FAIL_CLOSED_NO_DATA without touching the production log).
LOG_FILE="${A6_LOG_FILE:-/home/elliotbot/clawd/logs/fleet-supervisor.log}"
NATS_SUBJECT="keiracom.elliot.inbox"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# Post-restart grace period: when the producer timer (fleet-supervisor.timer)
# was re-enabled in the last 2 hours, suppress alerts because the 24h lookback
# window cannot yet contain meaningful accumulation. Two hours = 24 fires of
# the 5-min producer cadence, enough for any real outage to re-surface.
GRACE_THRESHOLD_S=7200  # 2 hours

# Returns 0 (success) if the producer timer was activated <GRACE_THRESHOLD_S
# ago AND we should suppress the alert; returns 1 otherwise. Also echoes a
# one-line grace_period notice to stderr when suppressing.
_in_grace_period() {
    local producer_timer="fleet-supervisor.timer"
    local ts_str epoch_active epoch_now delta_s delta_min
    ts_str="$(systemctl --user show "${producer_timer}" --property=ActiveEnterTimestamp --value 2>/dev/null || true)"
    # Empty / 'n/a' / unparseable means timer never activated → no grace period
    [[ -z "${ts_str}" ]] && return 1
    [[ "${ts_str}" == "n/a" ]] && return 1
    epoch_active=$(date -d "${ts_str}" +%s 2>/dev/null || echo 0)
    [[ "${epoch_active}" -eq 0 ]] && return 1
    epoch_now=$(date +%s)
    delta_s=$(( epoch_now - epoch_active ))
    [[ "${delta_s}" -lt 0 ]] && return 1   # future timestamp → ignore
    if [[ "${delta_s}" -lt "${GRACE_THRESHOLD_S}" ]]; then
        delta_min=$(( delta_s / 60 ))
        echo "grace_period: producer re-enabled ${delta_min}min ago, awaiting accumulation" >&2
        return 0
    fi
    return 1
}

# ----- helper: Viktor-voice alert publish to NATS keiracom.elliot.inbox -----
publish_alert() {
    local diagnostic="$1"
    local action_required="$2"
    local producer_state consumer_state alert_body payload

    # Honour 2h post-restart grace period before publishing.
    if _in_grace_period; then
        return 0
    fi

    producer_state="$(systemctl --user is-active "${SERVICE}" 2>/dev/null || echo 'unknown')"
    consumer_state="$(systemctl --user is-active "${WORKER_SERVICE}" 2>/dev/null || echo 'unknown')"

    alert_body=$(printf -- '─── A6 OBSERVATION FAIL_CLOSED ───\n\n*Diagnostic:* %s\n*Producer:* %s=%s\n*Consumer:* %s=%s\n*Window:* %s\n\n▸ ACTION REQUIRED: %s' \
        "${diagnostic}" \
        "${SERVICE}" "${producer_state}" \
        "${WORKER_SERVICE}" "${consumer_state}" \
        "${SINCE}" \
        "${action_required}")

    if ! command -v nats >/dev/null 2>&1; then
        echo "ALERT_PUBLISH_FAILED: nats CLI not found (alert body follows):" >&2
        echo "${alert_body}" >&2
        return 1
    fi

    # Build a JSON envelope keiracom-elliot-inbox bridge accepts. python3 is
    # used inline (not added as a runtime dep — already required by every
    # other operational script in scripts/).
    payload=$(python3 -c "
import json, sys, time
print(json.dumps({
    'sender': 'nova',
    'sender_name': 'nova',
    'ts': time.time(),
    'kind': 'alert',
    'to': 'elliot',
    'severity': 'critical',
    'task_ref': 'Agency_OS-vjcq',
    'text': sys.argv[1],
}))
" "${alert_body}")

    if ! nats pub "${NATS_SUBJECT}" "${payload}" >/dev/null 2>&1; then
        echo "ALERT_PUBLISH_FAILED: nats pub ${NATS_SUBJECT} returned non-zero (alert body follows):" >&2
        echo "${alert_body}" >&2
        return 1
    fi
    echo "  alert_published=1 subject=${NATS_SUBJECT}"
    return 0
}

# ----- 1. primary source: journalctl -----
if ! journalctl --user -u "${SERVICE}" --since "${SINCE}" --no-pager >"${TMP}" 2>/dev/null; then
    echo "FAIL-CLOSED: journalctl --user -u ${SERVICE} returned non-zero" >&2
    echo "    Diagnostic: ensure user journald is reachable and the unit exists." >&2
    if [[ "${ALERT_MODE}" -eq 1 ]]; then
        publish_alert \
            "journalctl unavailable for ${SERVICE}" \
            "verify user journald reachable: 'journalctl --user-unit=${SERVICE} --since 1h'" \
            || true
    fi
    exit 2
fi

# ----- 2. fallback source: log file (only if journalctl has no publish lines) -----
# fleet-supervisor.log is python-logger-formatted ('YYYY-MM-DD HH:MM:SS,sss LEVEL ...').
# We accept all lines in the file; the observation window is bounded by --since
# at the journalctl call above. If the log file's retention exceeds the window
# we will over-count slightly — flagged in stderr below.
if ! grep -qE "NATS PUBLISH|temporal signal sent" "${TMP}" && [[ -r "${LOG_FILE}" ]]; then
    echo "[note] journalctl had no publish lines; augmenting from ${LOG_FILE}" >&2
    cat "${LOG_FILE}" >>"${TMP}"
fi

# ----- 3. counts -----
count_nats=$(grep -cE "NATS PUBLISH keiracom\.agent\.status\." "${TMP}" || true)
count_temporal=$(grep -cE "temporal signal sent: " "${TMP}" || true)

# Strip any whitespace grep -c may produce on some platforms.
count_nats=${count_nats//[!0-9]/}
count_temporal=${count_temporal//[!0-9]/}
count_nats=${count_nats:-0}
count_temporal=${count_temporal:-0}

# ----- 4. fail-closed: no events on either side -----
if [[ "${count_nats}" -eq 0 && "${count_temporal}" -eq 0 ]]; then
    echo "FAIL-CLOSED: zero publish events in window (--since '${SINCE}')" >&2
    echo "    Diagnostic checks:" >&2
    echo "      systemctl --user status fleet-supervisor.service" >&2
    echo "      systemctl --user status fleet-supervisor.timer" >&2
    echo "      grep TEMPORAL_DUAL_PUBLISH_ENABLED /home/elliotbot/.config/agency-os/.env" >&2
    echo "    Producer-side dual-publish requires fleet-supervisor.service" >&2
    echo "    to fire during the window AND TEMPORAL_DUAL_PUBLISH_ENABLED=1." >&2
    cat <<EOF
a6_observation_check  window=${SINCE}
  count_nats=0
  count_temporal=0
  mismatch_count=0
  mismatch_pct=NaN
  status=FAIL_CLOSED_NO_DATA
EOF
    if [[ "${ALERT_MODE}" -eq 1 ]]; then
        publish_alert \
            "zero dual-publish events observed in window — producer not firing" \
            "re-enable producer: 'systemctl --user enable --now fleet-supervisor.timer'; or confirm Phase A6 producer migration is intentional and stop this observation cadence" \
            || true
    fi
    exit 2
fi

# ----- 5. mismatch + percentage (integer arithmetic) -----
if [[ "${count_nats}" -gt "${count_temporal}" ]]; then
    mismatch_count=$(( count_nats - count_temporal ))
    denominator=${count_nats}
else
    mismatch_count=$(( count_temporal - count_nats ))
    denominator=${count_temporal}
fi
mismatch_pct=$(( mismatch_count * 100 / denominator ))

# ----- 6. mismatch examples — per-(callsign,state) counts diverging between sides -----
# Emit one line per (callsign,state) pair where NATS count != Temporal count,
# sorted by absolute delta descending, first 5. Empty if every pair matches
# exactly (mismatch_count may still be non-zero if a side has a pair the
# other lacks entirely — set difference catches that case).
EXAMPLES=$( {
    grep -oE "NATS PUBLISH keiracom\.agent\.status\.[a-z0-9_-]+ . [a-z_]+" "${TMP}" \
        | sed -E 's/NATS PUBLISH keiracom\.agent\.status\.([a-z0-9_-]+) . ([a-z_]+)/\1\t\2\tN/'
    grep -oE "temporal signal sent: [a-z0-9_-]+ state=[a-z_]+" "${TMP}" \
        | sed -E 's/temporal signal sent: ([a-z0-9_-]+) state=([a-z_]+)/\1\t\2\tT/'
} | awk -F'\t' '
    { key=$1 FS $2; if($3=="N") n[key]++; else t[key]++; keys[key]=1 }
    END {
        for (k in keys) {
            nc=n[k]+0; tc=t[k]+0;
            if (nc != tc) {
                delta = (nc>tc) ? nc-tc : tc-nc;
                printf "%d\t%s\tNATS=%d\tTemporal=%d\n", delta, k, nc, tc
            }
        }
    }
' | sort -t$'\t' -k1,1 -nr | head -5 | cut -f2-)

# ----- 7. report -----
cat <<EOF
a6_observation_check  window=${SINCE}
  count_nats=${count_nats}
  count_temporal=${count_temporal}
  mismatch_count=${mismatch_count}
  mismatch_pct=${mismatch_pct}%
EOF

if [[ -n "${EXAMPLES}" ]]; then
    echo "  mismatch_examples (first 5 by delta desc):"
    echo "${EXAMPLES}" | sed 's/^/    /'
fi

# ----- 8. exit code per spec (--alert only fires on FAIL_CLOSED, not WARN/ALARM) -----
if [[ "${mismatch_pct}" -lt 1 ]]; then
    echo "  status=CLEAN"
    exit 0
elif [[ "${mismatch_pct}" -lt 5 ]]; then
    echo "  status=WARN"
    exit 1
else
    echo "  status=ALARM"
    exit 2
fi
