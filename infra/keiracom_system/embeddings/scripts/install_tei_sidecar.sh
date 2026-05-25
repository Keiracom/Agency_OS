#!/usr/bin/env bash
# install_tei_sidecar.sh — bring up TEI sidecar + verify health.
#
# Phase 2 build wave 2 item 2. Per-tenant install hook (Topology B) or per-
# instance install hook (Topology A — Scale tier). Idempotent — re-running is
# a no-op if the sidecar is already up + healthy.
#
# Usage:
#   bash infra/keiracom_system/embeddings/scripts/install_tei_sidecar.sh
#   bash ... --project-name <tenant_id>     # custom docker compose project name
#   bash ... --health-timeout 180           # bump model-download grace period
#
# Exit codes:
#   0  TEI sidecar up + healthy (or already was)
#   1  docker-compose missing / install failed
#   2  TEI sidecar started but failed health check within timeout
#
# Verifies after start:
#   1. docker compose up -d (idempotent)
#   2. health check polls http://localhost:8080/health every 5s
#   3. /info endpoint returns model_id matching BAAI/bge-small-en-v1.5
#   4. /embed round-trip with a probe text returns a 384-dim vector

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../docker-compose.tei.yml"
PROJECT_NAME="${KEIRACOM_TEI_PROJECT:-keiracom-tei}"
HEALTH_URL="${KEIRACOM_TEI_HEALTH_URL:-http://localhost:8080/health}"
INFO_URL="${KEIRACOM_TEI_INFO_URL:-http://localhost:8080/info}"
EMBED_URL="${KEIRACOM_TEI_EMBED_URL:-http://localhost:8080/embed}"
HEALTH_TIMEOUT_SECONDS="${KEIRACOM_TEI_HEALTH_TIMEOUT:-180}"
EXPECTED_MODEL="${KEIRACOM_TEI_EXPECTED_MODEL:-BAAI/bge-small-en-v1.5}"
EXPECTED_DIM=384

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-name) PROJECT_NAME="$2"; shift 2 ;;
        --health-timeout) HEALTH_TIMEOUT_SECONDS="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 1 ;;
    esac
done

echo "install_tei_sidecar: project=${PROJECT_NAME} compose=${COMPOSE_FILE}"

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker not in PATH" >&2
    exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: docker compose v2 plugin missing" >&2
    exit 1
fi

# 1. Bring up sidecar (idempotent — `up -d` is no-op if already up).
docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" up -d

# 2. Poll health endpoint until 200 OK or timeout.
echo "install_tei_sidecar: polling ${HEALTH_URL} (timeout ${HEALTH_TIMEOUT_SECONDS}s)..."
deadline=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))
while [[ $(date +%s) -lt ${deadline} ]]; do
    if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
        echo "install_tei_sidecar: health OK"
        break
    fi
    sleep 5
done
if ! curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    echo "ERROR: TEI sidecar failed health check within ${HEALTH_TIMEOUT_SECONDS}s" >&2
    echo "Recent logs:" >&2
    docker compose -f "${COMPOSE_FILE}" -p "${PROJECT_NAME}" logs --tail=50 embed >&2 || true
    exit 2
fi

# 3. Verify model identity (defence against accidental model swap at upgrade).
info_json="$(curl -fsS "${INFO_URL}")"
actual_model="$(echo "${info_json}" | python3 -c "import json,sys; print(json.load(sys.stdin).get('model_id',''))")"
if [[ "${actual_model}" != "${EXPECTED_MODEL}" ]]; then
    echo "WARN: TEI loaded model_id=${actual_model!r} != expected=${EXPECTED_MODEL!r}" >&2
    echo "  Vector lineage may differ — downstream Hindsight schema dimension assumes ${EXPECTED_DIM}." >&2
    # Non-fatal — operator may intentionally have swapped the model.
else
    echo "install_tei_sidecar: model_id=${actual_model} ✓"
fi

# 4. /embed round-trip with a probe text.
probe_response="$(curl -fsS -X POST "${EMBED_URL}" \
    -H 'Content-Type: application/json' \
    -d '{"inputs": ["health probe"]}')"
probe_dim="$(echo "${probe_response}" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d[0]) if d else 0)")"
if [[ "${probe_dim}" -ne "${EXPECTED_DIM}" ]]; then
    echo "ERROR: /embed returned ${probe_dim}-dim vector; expected ${EXPECTED_DIM}" >&2
    exit 2
fi
echo "install_tei_sidecar: /embed probe returned ${probe_dim}-dim vector ✓"

echo "install_tei_sidecar: DONE — sidecar healthy at ${HEALTH_URL}"
