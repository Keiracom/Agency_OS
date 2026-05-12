#!/usr/bin/env bash
# Smoke test: session_store_{posttooluse,stop}.sh must early-exit (status 0)
# when CLAUDE_CODE_SKILL_GEN=1 is set in the environment. This is the
# recursion guard for src/skill_gen — see src/skill_gen/claude_invoke.py.
#
# Runs both hooks twice:
#   1. With CLAUDE_CODE_SKILL_GEN=1  → assert exit 0 AND no recorder log line.
#   2. Without the env var          → assert exit 0 (best-effort recording).
#
# This is a shell smoke, not pytest. Run manually:
#   bash tests/hooks/test_session_store_hook_skip.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
POSTTOOLUSE_HOOK="$REPO_ROOT/.claude/hooks/session_store_posttooluse.sh"
STOP_HOOK="$REPO_ROOT/.claude/hooks/session_store_stop.sh"
TMP_LOG_DIR="$(mktemp -d -t session-store-hook-smoke.XXXXXX)"
trap "rm -rf '$TMP_LOG_DIR'" EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

# --- Case 1a: posttooluse with marker → early-exit, no log line written ---
SESSION_STORE_LOG_DIR="$TMP_LOG_DIR" CLAUDE_CODE_SKILL_GEN=1 \
    bash "$POSTTOOLUSE_HOOK" </dev/null
[ ! -f "$TMP_LOG_DIR/posttooluse.log" ] || \
    fail "posttooluse hook wrote log despite CLAUDE_CODE_SKILL_GEN=1"
pass "posttooluse hook: early-exit when marker set; no log line"

# --- Case 1b: stop with marker → early-exit, no log line written ---
SESSION_STORE_LOG_DIR="$TMP_LOG_DIR" CLAUDE_CODE_SKILL_GEN=1 \
    bash "$STOP_HOOK" </dev/null
[ ! -f "$TMP_LOG_DIR/stop.log" ] || \
    fail "stop hook wrote log despite CLAUDE_CODE_SKILL_GEN=1"
pass "stop hook: early-exit when marker set; no log line"

# --- Case 2a: posttooluse WITHOUT marker → exit 0 + log line written ---
SESSION_STORE_LOG_DIR="$TMP_LOG_DIR" \
    bash "$POSTTOOLUSE_HOOK" <<<'{}'
[ -f "$TMP_LOG_DIR/posttooluse.log" ] || \
    fail "posttooluse hook did NOT write log when marker absent"
pass "posttooluse hook: writes log when marker absent (best-effort path intact)"

# --- Case 2b: stop WITHOUT marker → exit 0 + log line written ---
SESSION_STORE_LOG_DIR="$TMP_LOG_DIR" \
    bash "$STOP_HOOK" </dev/null
[ -f "$TMP_LOG_DIR/stop.log" ] || \
    fail "stop hook did NOT write log when marker absent"
pass "stop hook: writes log when marker absent (best-effort path intact)"

echo "ALL HOOK SMOKE CASES PASS"
