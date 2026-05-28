#!/usr/bin/env bash
# install_reranker_sidecar.sh — bring up the reranker sidecar + verify.
#
# Wave 2 dispatch Agency_OS-0thg. Idempotent — re-running while the sidecar
# is up + healthy is a no-op. Mirrors infra/keiracom_system/embeddings/
# scripts/install_tei_sidecar.sh; same TEI image, different model.
#
# Usage:
#   bash infra/keiracom_system/reranker/scripts/install_reranker_sidecar.sh
#   bash ... --project-name keiracom-reranker-<tenant_id>
#   bash ... --health-timeout 240   # bump model-download grace
#
# Verifies after start:
#   1. docker compose up -d (idempotent)
#   2. health poll on http://localhost:8090/health
#   3. /info returns model_id BAAI/bge-reranker-base
#   4. /rerank round-trip with a probe (query, [candidate]) returns a score
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../docker-compose.reranker.yml"
PROJECT_NAME="${KEIRACOM_RERANKER_PROJECT:-keiracom-reranker}"
HEALTH_URL="${KEIRACOM_RERANKER_HEALTH_URL:-http://localhost:8090/health}"
INFO_URL="${KEIRACOM_RERANKER_INFO_URL:-http://localhost:8090/info}"
RERANK_URL="${KEIRACOM_RERANKER_RERANK_URL:-http://localhost:8090/rerank}"
HEALTH_TIMEOUT_SECONDS="${KEIRACOM_RERANKER_HEALTH_TIMEOUT:-240}"
EXPECTED_MODEL="${KEIRACOM_RERANKER_EXPECTED_MODEL:-BAAI/bge-reranker-base}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --health-timeout) HEALTH_TIMEOUT_SECONDS="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

command -v docker >/dev/null || { echo "docker missing" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "docker compose plugin missing" >&2; exit 1; }

echo "==> docker compose up -d (project=${PROJECT_NAME})"
docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" up -d

echo "==> polling ${HEALTH_URL} (timeout ${HEALTH_TIMEOUT_SECONDS}s)..."
DEADLINE=$(( $(date +%s) + HEALTH_TIMEOUT_SECONDS ))
until curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; do
  if (( $(date +%s) >= DEADLINE )); then
    echo "FAIL: reranker did not pass health check within ${HEALTH_TIMEOUT_SECONDS}s" >&2
    docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" logs --tail=50 >&2
    exit 2
  fi
  sleep 5
done

echo "==> /info → expecting model_id=${EXPECTED_MODEL}"
INFO_JSON="$(curl -fsS "${INFO_URL}")"
echo "${INFO_JSON}"
if ! echo "${INFO_JSON}" | grep -q "\"model_id\":\"${EXPECTED_MODEL}\""; then
  echo "FAIL: expected model_id=${EXPECTED_MODEL} in /info" >&2
  exit 3
fi

echo "==> /rerank smoke test"
RERANK_JSON="$(curl -fsS -X POST "${RERANK_URL}" \
  -H 'content-type: application/json' \
  -d '{"query":"what is rust","texts":["rust is a programming language","cats meow"]}')"
echo "${RERANK_JSON}"
echo "${RERANK_JSON}" | grep -q '"score"' || { echo "FAIL: no score in /rerank response" >&2; exit 4; }

echo "OK: reranker sidecar up + healthy + serving BAAI/bge-reranker-base on ${RERANK_URL}"
