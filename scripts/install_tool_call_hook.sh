#!/usr/bin/env bash
# install_tool_call_hook.sh — KEI-116 Build 1: install Claude Code PostToolUse hook.
#
# Wires scripts/hooks/tool_call_log_writer.py into ~/.claude/settings.json as a
# PostToolUse hook so every agent tool call is persisted to public.tool_call_log.
# The tool-call-log-indexer (KEI-107, already running) then indexes rows → Weaviate.
#
# Idempotent — safe to re-run. Will not add a duplicate hook entry.
#
# Usage:
#   bash scripts/install_tool_call_hook.sh
#
# Requirements:
#   - python3 with psycopg installed in /home/elliotbot/clawd/venv/bin/python3
#   - jq (used for settings.json manipulation)
#   - ~/.claude/settings.json writable

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WRITER_SCRIPT="$REPO_ROOT/scripts/hooks/tool_call_log_writer.py"
# Single-host design: venv path is fixed to the one machine this system runs on.
VENV_PYTHON="/home/elliotbot/clawd/venv/bin/python3"
SETTINGS_FILE="${HOME}/.claude/settings.json"

# ── Guard: writer script must exist and be non-empty ──────────────────────────
if [[ ! -f "$WRITER_SCRIPT" ]]; then
    echo "ERROR: writer script not found at $WRITER_SCRIPT" >&2
    exit 1
fi
echo "writer script: $WRITER_SCRIPT — OK"

# ── Guard: python + psycopg available ─────────────────────────────────────────
if ! "$VENV_PYTHON" -c "import psycopg" 2>/dev/null; then
    echo "ERROR: psycopg not importable from $VENV_PYTHON" >&2
    echo "       Run: $VENV_PYTHON -m pip install psycopg" >&2
    exit 1
fi
echo "psycopg: importable from $VENV_PYTHON — OK"

# ── Guard: jq available ───────────────────────────────────────────────────────
if ! command -v jq >/dev/null 2>&1; then
    echo "ERROR: jq not found — required for settings.json manipulation" >&2
    exit 1
fi

# ── Ensure ~/.claude/settings.json exists with minimal shape ──────────────────
mkdir -p "$(dirname "$SETTINGS_FILE")"
if [[ ! -f "$SETTINGS_FILE" ]]; then
    echo '{"permissions": {"defaultMode": "bypassPermissions"}}' > "$SETTINGS_FILE"
    echo "created: $SETTINGS_FILE"
fi

# ── Build the hook command string ─────────────────────────────────────────────
HOOK_CMD="$VENV_PYTHON $WRITER_SCRIPT"

# ── Idempotency check: is this hook already registered? ───────────────────────
ALREADY=$(jq --arg cmd "$HOOK_CMD" \
    '[.hooks.PostToolUse[]?.hooks[]? | select(.command == $cmd)] | length' \
    "$SETTINGS_FILE" 2>/dev/null || echo 0)

if [[ "$ALREADY" -gt 0 ]]; then
    echo "hook already registered in $SETTINGS_FILE — nothing to do"
    exit 0
fi

# ── Register the hook via jq in-place ─────────────────────────────────────────
# Appends a new PostToolUse matcher entry. Preserves all existing hooks.
TMP="$(mktemp)"
jq --arg cmd "$HOOK_CMD" '
    .hooks.PostToolUse = (
        (.hooks.PostToolUse // []) + [
            {
                "matcher": "*",
                "hooks": [
                    {
                        "type": "command",
                        "command": $cmd,
                        "timeout": 10
                    }
                ]
            }
        ]
    )
' "$SETTINGS_FILE" > "$TMP" && mv "$TMP" "$SETTINGS_FILE"

echo "registered PostToolUse hook in $SETTINGS_FILE:"
echo "  command: $HOOK_CMD"
echo ""
echo "Smoke test:"
echo "  echo '{\"tool_name\":\"Read\",\"tool_input\":{\"file_path\":\"/tmp/test\"},\"tool_response\":\"hi\"}' \\"
echo "    | $VENV_PYTHON $WRITER_SCRIPT"
echo ""
echo "Done. Restart Claude Code for the hook to take effect."
