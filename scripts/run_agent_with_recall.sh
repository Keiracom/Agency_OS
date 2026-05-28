#!/usr/bin/env bash
# run_agent_with_recall.sh — assemble a spawn's FULL system prompt.
#
#   full system prompt = hydrated governance template  (hydrate_spawn_template.py)
#                      +  the recall block             (AGENCY_OS_PRIOR_CONTEXT)
#
# Previously a spawn launched with the raw recall block alone as its context.
# Per the cutover plan, the governance contract (docs/cutover/spawn_governance_
# template.md) must lead the system prompt, hydrated for this specific agent;
# the recall block (positive + failure context, injected upstream by the
# dispatcher's spawn_recall hook into AGENCY_OS_PRIOR_CONTEXT) is appended below.
#
# Emits the assembled prompt on stdout — the caller forwards it to the agent CLI
# via `--append-system-prompt "$(...)"`. Stdlib Python only; no extra deps.
#
# Usage:
#   run_agent_with_recall.sh --callsign orion --orchestrator elliot \
#       --model gemini-2.5-flash [--role-lens "..."] [--specialty "build/retrieval"]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CALLSIGN="" ORCHESTRATOR="" MODEL="" ROLE_LENS="" SPECIALTY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --callsign)     CALLSIGN="$2"; shift 2 ;;
    --orchestrator) ORCHESTRATOR="$2"; shift 2 ;;
    --model)        MODEL="$2"; shift 2 ;;
    --role-lens)    ROLE_LENS="$2"; shift 2 ;;
    --specialty)    SPECIALTY="$2"; shift 2 ;;
    *) echo "run_agent_with_recall.sh: unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$CALLSIGN" ] || [ -z "$ORCHESTRATOR" ] || [ -z "$MODEL" ]; then
  echo "run_agent_with_recall.sh: --callsign, --orchestrator, and --model are required" >&2
  exit 2
fi

HYDRATE_ARGS=(--callsign "$CALLSIGN" --orchestrator "$ORCHESTRATOR" --model "$MODEL")
[ -n "$ROLE_LENS" ] && HYDRATE_ARGS+=(--role-lens "$ROLE_LENS")
[ -n "$SPECIALTY" ] && HYDRATE_ARGS+=(--specialty "$SPECIALTY")

GOVERNANCE="$(python3 "$SCRIPT_DIR/hydrate_spawn_template.py" "${HYDRATE_ARGS[@]}")"

# Recall block is injected upstream by the dispatcher (spawn_recall) into this
# env var. Absent (recall disabled / empty corpus) → governance prompt alone.
RECALL="${AGENCY_OS_PRIOR_CONTEXT:-}"

if [ -n "$RECALL" ]; then
  printf '%s\n\n%s\n' "$GOVERNANCE" "$RECALL"
else
  printf '%s\n' "$GOVERNANCE"
fi
