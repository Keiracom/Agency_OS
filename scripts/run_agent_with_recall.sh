#!/usr/bin/env bash
# run_agent_with_recall.sh — launch an ephemeral Claude agent with spawn-time
# memory recall injected into its system prompt (empirical test Stage B.2,
# docs/cutover/empirical_test_spec.md §6).
#
# Flow:
#   1. Call spawn_recall.inject_prior_context(task_type, task_brief) → builds the
#      "Prior context from memory" block from a reranked Hindsight recall.
#   2. Forward that block to the Claude CLI via --append-system-prompt so it
#      lands in the ephemeral agent's system prompt.
#   3. Fail-open: empty block (recall outage / empty corpus) → launch plain.
#
# This is the launch path that bridges inject_prior_context's env output to a
# real agent, which spawn_recall.py itself left out of scope.
#
# Usage:
#   scripts/run_agent_with_recall.sh "<task prompt>" [task_type]
#
# Env:
#   DISPATCHER_RERANKER_ENABLED  default "true" — engage the cross-encoder so
#                                recall is reranked (the gate's whole point).
#   HINDSIGHT_BASE               default http://localhost:8889
#   MODEL                        optional — passed to claude --model if set.
#   AGENCY_OS_ENV                .env path for DATABASE_URL (recall needs PG).
#   PYTHON                       venv python (default /home/elliotbot/clawd/venv/bin/python3).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK_PROMPT="${1:?usage: run_agent_with_recall.sh \"<task prompt>\" [task_type]}"
TASK_TYPE="${2:-research}"
AGENCY_OS_ENV="${AGENCY_OS_ENV:-$HOME/.config/agency-os/.env}"
PYTHON="${PYTHON:-/home/elliotbot/clawd/venv/bin/python3}"

# Recall needs DATABASE_URL etc.; fail-open if the env file is absent.
if [[ -r "$AGENCY_OS_ENV" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$AGENCY_OS_ENV"
    set +a
fi
export DISPATCHER_RERANKER_ENABLED="${DISPATCHER_RERANKER_ENABLED:-true}"
export HINDSIGHT_BASE="${HINDSIGHT_BASE:-http://localhost:8889}"

# 1. Build the recall block. Task passed via env to avoid shell-quoting issues.
BLOCK="$(cd "$REPO_DIR" && TASK_TYPE="$TASK_TYPE" TASK_BRIEF="$TASK_PROMPT" \
    PYTHONPATH=. "$PYTHON" - <<'PY'
import os
from src.retrieval import spawn_recall

kwargs = spawn_recall.inject_prior_context(
    {"env": {}},
    task_type=os.environ["TASK_TYPE"],
    task_brief=os.environ["TASK_BRIEF"],
)
print(kwargs.get("env", {}).get(spawn_recall.PRIOR_CONTEXT_ENV_KEY, ""), end="")
PY
)"

# 2. Launch the ephemeral agent. Fail-open when no block was produced.
declare -a MODEL_ARGS=()
[[ -n "${MODEL:-}" ]] && MODEL_ARGS=(--model "$MODEL")

if [[ -n "${BLOCK//[$' \t\r\n']/}" ]]; then
    echo "[run_agent_with_recall] injecting $(printf '%s' "$BLOCK" | wc -c) chars of prior context" >&2
    exec claude -p "$TASK_PROMPT" --append-system-prompt "$BLOCK" "${MODEL_ARGS[@]}"
else
    echo "[run_agent_with_recall] no prior context — launching plain (fail-open)" >&2
    exec claude -p "$TASK_PROMPT" "${MODEL_ARGS[@]}"
fi
