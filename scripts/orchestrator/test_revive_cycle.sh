#!/usr/bin/env bash
# test_revive_cycle.sh — End-to-end proof for Defects 1 + 2 (Dave 2026-05-31).
#
# Runs both recovery scripts against tmpdir-redirected outputs so the test is
# safe in CI + on the host. Prints PASS / FAIL with evidence for each check.
#
# Pass criteria:
#   1. write_heartbeat.py exits 0 and writes a HEARTBEAT.md whose `Last update`
#      line carries TODAY's UTC date.
#   2. write_compact_state.py exits 0 and the produced state file does NOT
#      contain the old "Phase 0" hardcoded literal. If ceo_memory is reachable
#      and returns the expected JSONB, the file additionally contains
#      "Phase 1" — the live-query proof. In CI (no Supabase reachable),
#      the fallback "phase unknown" path is also accepted as PASS provided
#      "Phase 0" stays absent (the structural fix is what matters).
#
# Exit 0 only when every check passes.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

HEARTBEAT_PATH="$TMP/HEARTBEAT.md"
COMPACT_STATE_PATH="$TMP/elliot-compact-state.md"
export HEARTBEAT_PATH
export ELLIOT_COMPACT_STATE_PATH="$COMPACT_STATE_PATH"

PYTHON="${PYTHON:-python3}"
PASS=0
FAIL=0

# ─── Check 1: write_heartbeat.py ─────────────────────────────────────────────
HB_LOG="$TMP/hb.log"
if "$PYTHON" scripts/orchestrator/write_heartbeat.py >"$HB_LOG" 2>&1; then
  if [[ -f "$HEARTBEAT_PATH" ]]; then
    TODAY="$(date -u +%Y-%m-%d)"
    if grep -q "^## Last update: ${TODAY}" "$HEARTBEAT_PATH"; then
      echo "PASS — write_heartbeat.py wrote HEARTBEAT.md with today's UTC date ($TODAY)"
      PASS=$((PASS + 1))
    else
      echo "FAIL — HEARTBEAT.md present but missing today's date ($TODAY)"
      head -5 "$HEARTBEAT_PATH" | sed 's/^/    /'
      FAIL=$((FAIL + 1))
    fi
  else
    echo "FAIL — HEARTBEAT.md not written at $HEARTBEAT_PATH"
    sed 's/^/    /' "$HB_LOG"
    FAIL=$((FAIL + 1))
  fi
else
  echo "FAIL — write_heartbeat.py exited non-zero:"
  sed 's/^/    /' "$HB_LOG"
  FAIL=$((FAIL + 1))
fi

# ─── Check 2: write_compact_state.py ─────────────────────────────────────────
# Only the `**Phase:**` HEADER line matters — the embedded HEARTBEAT excerpt
# can legitimately mention historic "Phase 0" milestones without the script
# being broken. The defect was the hardcoded literal in the header.
CS_LOG="$TMP/cs.log"
if "$PYTHON" scripts/orchestrator/write_compact_state.py >"$CS_LOG" 2>&1; then
  if [[ ! -f "$COMPACT_STATE_PATH" ]]; then
    echo "FAIL — compact state file not written at $COMPACT_STATE_PATH"
    sed 's/^/    /' "$CS_LOG"
    FAIL=$((FAIL + 1))
  else
    PHASE_LINE="$(grep -m1 '\*\*Phase:\*\*' "$COMPACT_STATE_PATH" || true)"
    if [[ -z "$PHASE_LINE" ]]; then
      echo "FAIL — compact state missing **Phase:** header line"
      head -5 "$COMPACT_STATE_PATH" | sed 's/^/    /'
      FAIL=$((FAIL + 1))
    elif [[ "$PHASE_LINE" == *"Phase 0"* ]]; then
      echo "FAIL — header line still contains hardcoded 'Phase 0' literal:"
      echo "    $PHASE_LINE"
      FAIL=$((FAIL + 1))
    elif [[ "$PHASE_LINE" == *"Phase 1"* ]]; then
      echo "PASS — header contains live 'Phase 1' from ceo_memory"
      echo "    $PHASE_LINE"
      PASS=$((PASS + 1))
    elif [[ "$PHASE_LINE" == *"phase unknown"* ]]; then
      echo "PASS — header shows 'phase unknown' fallback (ceo_memory unreachable)"
      echo "    structural fix verified; live-query proof requires Supabase reach"
      PASS=$((PASS + 1))
    else
      echo "FAIL — header has unexpected phase value:"
      echo "    $PHASE_LINE"
      FAIL=$((FAIL + 1))
    fi
  fi
else
  echo "FAIL — write_compact_state.py exited non-zero:"
  sed 's/^/    /' "$CS_LOG"
  FAIL=$((FAIL + 1))
fi

echo
echo "Result: $PASS pass, $FAIL fail"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
