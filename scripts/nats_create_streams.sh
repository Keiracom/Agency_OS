#!/usr/bin/env bash
# nats_create_streams.sh — KEI-205 step 2: create the 6 JetStream streams.
#
# Runs after install_nats.sh has nats-server.service up + active. Uses the
# `nats` CLI (separate from nats-server) — installs it on first run if missing.
#
# 6 streams per Elliot's architecture spec:
#   keiracom.orchestration              main task routing
#   keiracom.deliberation.{task_id}     per-task deliberation (subject wildcard)
#   keiracom.agent.status.{callsign}    agent ready/active state — kills [READY] Slack spam
#   keiracom.elliot.atlas               Elliot → Atlas pair channel
#   keiracom.aiden.orion                Aiden → Orion pair channel
#   keiracom.max.scout                  Max → Scout pair channel
#
# Idempotent — `nats stream add` errors if stream exists; we check first.
#
# Usage:
#   bash scripts/nats_create_streams.sh

set -euo pipefail

NATS_CLI="${NATS_CLI:-/usr/local/bin/nats}"
NATS_CLI_VERSION="${NATS_CLI_VERSION:-0.1.6}"
NATS_URL="${NATS_URL:-nats://127.0.0.1:4222}"

# ----- 1. Install nats CLI if missing -----
if [[ ! -x "${NATS_CLI}" ]]; then
    echo "nats_create_streams: nats CLI missing — installing v${NATS_CLI_VERSION}"
    arch="$(uname -m)"
    case "${arch}" in
        x86_64)  cli_arch="amd64" ;;
        aarch64) cli_arch="arm64" ;;
        *) echo "unsupported arch ${arch}" >&2; exit 2 ;;
    esac
    tarball="nats-${NATS_CLI_VERSION}-linux-${cli_arch}.zip"
    url="https://github.com/nats-io/natscli/releases/download/v${NATS_CLI_VERSION}/${tarball}"
    tmp="$(mktemp -d)"
    trap 'rm -rf "${tmp}"' EXIT
    curl -sSL "${url}" -o "${tmp}/${tarball}"
    unzip -q "${tmp}/${tarball}" -d "${tmp}"
    sudo install -m 0755 "${tmp}/nats-${NATS_CLI_VERSION}-linux-${cli_arch}/nats" "${NATS_CLI}"
    echo "nats_create_streams: installed $("${NATS_CLI}" --version | head -1)"
fi

# ----- 2. Define streams. Subject patterns include wildcards where the
# architecture uses per-task / per-callsign subjects. -----
# Format: <stream_name>|<subjects>|<comment>
declare -a STREAMS=(
    "orchestration|keiracom.orchestration|main task routing"
    "deliberation|keiracom.deliberation.*|per-task deliberation (subject wildcard for task_id)"
    "agent_status|keiracom.agent.status.*|agent ready/active state — kills [READY] Slack spam"
    "pair_elliot_atlas|keiracom.elliot.atlas|Elliot → Atlas pair channel"
    "pair_aiden_orion|keiracom.aiden.orion|Aiden → Orion pair channel"
    "pair_max_scout|keiracom.max.scout|Max → Scout pair channel"
)

# ----- 3. Idempotent create -----
created=0
existed=0
failed=()
for entry in "${STREAMS[@]}"; do
    IFS='|' read -r name subjects comment <<< "${entry}"
    if "${NATS_CLI}" -s "${NATS_URL}" stream info "${name}" >/dev/null 2>&1; then
        echo "  ${name}: exists (subjects=${subjects})"
        existed=$((existed + 1))
        continue
    fi
    if "${NATS_CLI}" -s "${NATS_URL}" stream add "${name}" \
            --subjects="${subjects}" \
            --storage=file \
            --retention=limits \
            --max-msgs=-1 \
            --max-bytes=-1 \
            --max-age=24h \
            --max-msg-size=-1 \
            --discard=old \
            --dupe-window=2m \
            --replicas=1 \
            --defaults >/dev/null 2>&1; then
        echo "  ${name}: created (subjects=${subjects}) — ${comment}"
        created=$((created + 1))
    else
        echo "  ${name}: FAILED to create" >&2
        failed+=("${name}")
    fi
done

# ----- 4. Verify -----
echo
echo "----- verify -----"
"${NATS_CLI}" -s "${NATS_URL}" stream ls 2>/dev/null | grep -E '^\s+(orchestration|deliberation|agent_status|pair_)' || true

if ((${#failed[@]} > 0)); then
    echo "nats_create_streams: ${#failed[@]} failure(s):" >&2
    printf '  - %s\n' "${failed[@]}" >&2
    exit 1
fi

echo
echo "nats_create_streams: ${created} created, ${existed} already existed (of 6 total)"
