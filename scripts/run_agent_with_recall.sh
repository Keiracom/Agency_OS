#!/usr/bin/env bash
# run_agent_with_recall.sh — launch an ephemeral Gemini agent with spawn-time
# memory recall injected into its system prompt (empirical test Stage B.2,
# docs/cutover/empirical_test_spec.md §6).
#
# Flow:
#   1. Call spawn_recall.inject_prior_context(task_type, task_brief) → builds the
#      "Prior context from memory" block from a reranked Hindsight recall.
#   2. Forward that block + task prompt to Gemini API (google-generativeai).
#   3. Fail-open: empty block (recall outage / empty corpus) → launch plain.
#
# Uses Gemini for all ephemeral testing (Claude CLI uses Anthropic API credits;
# Gemini key is available in env as GEMINI_API_KEY).
#
# Usage:
#   scripts/run_agent_with_recall.sh "<task prompt>" [task_type]
#
# Env:
#   DISPATCHER_RERANKER_ENABLED  default "true" — engage the cross-encoder so
#                                recall is reranked (the gate's whole point).
#   HINDSIGHT_BASE               default http://localhost:8889
#   MODEL                        optional — Gemini model override (default gemini-2.5-flash).
#   AGENCY_OS_ENV                .env path for DATABASE_URL + GEMINI_API_KEY.
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

# 2. Launch the ephemeral agent via Gemini API. Fail-open when no block produced.
GEMINI_MODEL="${MODEL:-gemini-2.5-flash}"

if [[ -n "${BLOCK//[$' \t\r\n']/}" ]]; then
    echo "[run_agent_with_recall] injecting $(printf '%s' "$BLOCK" | wc -c) chars of prior context → $GEMINI_MODEL" >&2
else
    echo "[run_agent_with_recall] no prior context — launching plain (fail-open) → $GEMINI_MODEL" >&2
fi

exec "$PYTHON" - <<PY
import os, sys
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

task_prompt = """${TASK_PROMPT}"""
block = """${BLOCK}"""

config = types.GenerateContentConfig(
    temperature=0.2,
    system_instruction=block if block.strip() else None,
)

response = client.models.generate_content(
    model="${GEMINI_MODEL}",
    contents=task_prompt,
    config=config,
)

print(response.text)
PY
