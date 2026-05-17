#!/usr/bin/env bash
# kei45_acceptance_test.sh — KEI-45 behavioral acceptance test.
#
# Satisfies Dave's verification-trigger acceptance criterion verbatim:
#   "Orion is idle. Make a task available. Orion wakes up automatically
#    within 10 seconds. No manual dispatch. No relay required."
#
# Run AFTER kei45-realtime-listener.service is started:
#   systemctl --user start kei45-realtime-listener
#   bash scripts/orchestrator/kei45_acceptance_test.sh
#
# What it does:
#   1. Captures a baseline tmux pane snapshot for all 6 callsigns.
#   2. INSERTs a test row into public.tasks with status='available'.
#   3. Sleeps 10 seconds (the acceptance window).
#   4. Captures post-INSERT tmux pane snapshot.
#   5. Compares: each pane must show a NEW 'bd ready  # KEI-45 listener wake-up'
#      line that wasn't in the baseline.
#   6. Cleans up the test row.
#   7. Prints PASS/FAIL summary + verbatim diff per agent.
#   8. On PASS: prints the SQL to INSERT task_verifications row + UPDATE done.
#
# The verbatim output is the test_output payload for the task_verifications
# INSERT — capture stdout (e.g. via tee) when running for the record.

set -euo pipefail

TEST_ID="KEI-45-ACCEPTANCE-$(date -u +%Y%m%dT%H%M%SZ)"
WINDOW_SECONDS="${KEI45_WAKE_WINDOW:-10}"
MCP_BRIDGE="/home/elliotbot/clawd/skills/mcp-bridge"
PROJECT_ID="${SUPABASE_PROJECT_ID:-jatzvazlbusedwsnqxzr}"

CALLSIGNS=(elliot aiden max atlas orion scout)
declare -A TMUX_SESSION=(
  [elliot]=elliottbot
  [aiden]=aiden
  [max]=maxbot
  [atlas]=atlas
  [orion]=orion
  [scout]=scout
)

run_sql() {
  local sql=$1
  local args
  args=$(jq -cn --arg pid "$PROJECT_ID" --arg q "$sql" '{project_id:$pid, query:$q}')
  node "$MCP_BRIDGE/scripts/mcp-bridge.js" call supabase execute_sql "$args"
}

capture_pane() {
  local session=$1
  if tmux has-session -t "$session" 2>/dev/null; then
    tmux capture-pane -t "$session" -p -S -50 2>/dev/null || echo "<capture-pane failed>"
  else
    echo "<tmux session $session not running>"
  fi
}

echo "=== KEI-45 Acceptance Test ==="
echo "test_id: $TEST_ID"
echo "window:  ${WINDOW_SECONDS}s"
echo "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

declare -A BEFORE
for cs in "${CALLSIGNS[@]}"; do
  BEFORE[$cs]=$(capture_pane "${TMUX_SESSION[$cs]}")
done
echo "baseline captured for ${#CALLSIGNS[@]} panes"

echo
echo "INSERTing test row $TEST_ID into public.tasks..."
INSERT_SQL="INSERT INTO public.tasks (id, status, title, priority) VALUES ('$TEST_ID', 'available', 'KEI-45 acceptance test row', 5);"
run_sql "$INSERT_SQL" >/dev/null
echo "INSERT done. Sleeping ${WINDOW_SECONDS}s for listener fan-out..."
sleep "$WINDOW_SECONDS"

echo
echo "=== Per-callsign wake verification ==="
PASS=0
FAIL=0
declare -A RESULT
for cs in "${CALLSIGNS[@]}"; do
  AFTER=$(capture_pane "${TMUX_SESSION[$cs]}")
  WAKE_LINE=$(diff <(echo "${BEFORE[$cs]}") <(echo "$AFTER") | grep -E '^>.*KEI-45 listener wake-up' || true)
  if [[ -n "$WAKE_LINE" ]]; then
    echo "  PASS $cs (${TMUX_SESSION[$cs]}): $WAKE_LINE"
    RESULT[$cs]=PASS
    PASS=$((PASS+1))
  else
    echo "  FAIL $cs (${TMUX_SESSION[$cs]}): no listener wake line in pane"
    RESULT[$cs]=FAIL
    FAIL=$((FAIL+1))
  fi
done

echo
echo "=== Cleanup ==="
CLEANUP_SQL="DELETE FROM public.tasks WHERE id='$TEST_ID';"
run_sql "$CLEANUP_SQL" >/dev/null
echo "test row $TEST_ID deleted"

echo
echo "=== Summary ==="
echo "PASS: $PASS / ${#CALLSIGNS[@]}"
echo "FAIL: $FAIL / ${#CALLSIGNS[@]}"

if [[ "$FAIL" -eq 0 ]]; then
  echo
  echo "=== ACCEPTANCE SATISFIED — task_verifications INSERT SQL ==="
  cat <<EOF
INSERT INTO public.task_verifications (task_id, verified_by, behavioral_test, test_output)
VALUES (
  'KEI-45',
  'max',
  'kei45_acceptance_test.sh — INSERT test row, sleep ${WINDOW_SECONDS}s, capture all 6 tmux panes, verify wake-up line present',
  \$\$$(printf '%s' "$0 verbatim stdout — capture via tee")\$\$
);

UPDATE public.tasks SET status='done' WHERE id='KEI-45' AND claimed_by='max';
EOF
  exit 0
else
  echo
  echo "ACCEPTANCE FAILED — listener did not wake all 6 panes within ${WINDOW_SECONDS}s"
  echo "Do NOT INSERT task_verifications. Investigate before re-running."
  exit 1
fi
