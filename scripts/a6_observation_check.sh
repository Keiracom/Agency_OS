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
# Usage (manual):
#   bash scripts/a6_observation_check.sh
#   bash scripts/a6_observation_check.sh --since "12h ago"
#   bash scripts/a6_observation_check.sh --since "2026-05-26 00:50"
#
# Usage (daily cron during observation window):
#   0 8 * * * /home/elliotbot/clawd/Agency_OS/scripts/a6_observation_check.sh \
#       >> /home/elliotbot/clawd/logs/a6_observation_check.log 2>&1

set -euo pipefail

# ----- args -----
SINCE="24h ago"
if [ "${1:-}" = "--since" ] && [ -n "${2:-}" ]; then
    SINCE="$2"
elif [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    sed -n '2,40p' "$0"
    exit 0
fi

# ----- constants -----
SERVICE="fleet-supervisor.service"
LOG_FILE="/home/elliotbot/clawd/logs/fleet-supervisor.log"
TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# ----- 1. primary source: journalctl -----
if ! journalctl --user -u "${SERVICE}" --since "${SINCE}" --no-pager >"${TMP}" 2>/dev/null; then
    echo "FAIL-CLOSED: journalctl --user -u ${SERVICE} returned non-zero" >&2
    echo "    Diagnostic: ensure user journald is reachable and the unit exists." >&2
    exit 2
fi

# ----- 2. fallback source: log file (only if journalctl has no publish lines) -----
if ! grep -qE "NATS PUBLISH|temporal signal sent" "${TMP}"; then
    if [ -r "${LOG_FILE}" ]; then
        # fleet-supervisor.log is python-logger-formatted ('YYYY-MM-DD HH:MM:SS,sss LEVEL ...').
        # We accept all lines in the file; the observation window is bounded
        # by --since at the journalctl call above. If the log file's retention
        # exceeds the window, we will over-count slightly — flagged in the
        # output as a source-augmentation note.
        echo "[note] journalctl had no publish lines; augmenting from ${LOG_FILE}" >&2
        cat "${LOG_FILE}" >>"${TMP}"
    fi
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
if [ "${count_nats}" -eq 0 ] && [ "${count_temporal}" -eq 0 ]; then
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
    exit 2
fi

# ----- 5. mismatch + percentage (integer arithmetic) -----
if [ "${count_nats}" -gt "${count_temporal}" ]; then
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

if [ -n "${EXAMPLES}" ]; then
    echo "  mismatch_examples (first 5 by delta desc):"
    echo "${EXAMPLES}" | sed 's/^/    /'
fi

# ----- 8. exit code per spec -----
if [ "${mismatch_pct}" -lt 1 ]; then
    echo "  status=CLEAN"
    exit 0
elif [ "${mismatch_pct}" -lt 5 ]; then
    echo "  status=WARN"
    exit 1
else
    echo "  status=ALARM"
    exit 2
fi
