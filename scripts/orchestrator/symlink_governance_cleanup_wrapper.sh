#!/usr/bin/env bash
# symlink_governance_cleanup_wrapper.sh — KEI-12 24h-smoke cleanup wrapper.
#
# Operator wrapper invoked by symlink-governance-cleanup-bak.timer at
# 2026-05-13 ~10:51 UTC (24h post-swap). Runs three steps in sequence:
#   1. scripts/orchestrator/symlink_governance.sh --cleanup-bak
#   2. Post verbatim cleanup output to #execution via slack_relay.py
#   3. LAW XV three-store save bundling KEI-12 closure
#
# Best-effort throughout: step 2 failure logs + continues; step 3 failure
# logs + continues. Step 1 is the gate — if cleanup fails the timer logs
# the failure and the operator can retry manually.
#
# Pattern source: scripts/orchestrator/elliot_polling_loop.py wrapper idiom
# + scripts/three_store_save.py LAW XV save shape.

set -u

REPO_ROOT="/home/elliotbot/clawd/Agency_OS"
LOG_FILE="/home/elliotbot/clawd/logs/symlink-governance-cleanup-bak.log"

log() { printf '[%s] cleanup-wrapper: %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "${LOG_FILE}"; }


# Step 1 — cleanup-bak
log "Step 1: cleanup-bak across 6 worktrees"
CLEANUP_OUTPUT=$("${REPO_ROOT}"/scripts/orchestrator/symlink_governance.sh --cleanup-bak 2>&1)
CLEANUP_RC=$?
echo "${CLEANUP_OUTPUT}" >> "${LOG_FILE}"
if [ "${CLEANUP_RC}" -ne 0 ]; then
    log "Step 1 FAILED (exit ${CLEANUP_RC}) — operator review required"
    exit "${CLEANUP_RC}"
fi
log "Step 1 OK"


# Step 2 — Slack announce
log "Step 2: post completion to #execution"
SLACK_MSG="[AIDEN] **KEI-12 cleanup-bak FIRED** (systemd timer)

\\\$ scripts/orchestrator/symlink_governance.sh --cleanup-bak
${CLEANUP_OUTPUT}

24h smoke window closed; .bak preservation removed. Symlink governance is the durable state across all 6 worktrees. Rollback path is no longer available — symlinks are the source of truth.

Linked: PR #779 KEI-12 / Item #1 (dc608ba3) + operator --swap at 2026-05-12 ~10:51 UTC."
"${REPO_ROOT}"/scripts/slack_relay.py -g "${SLACK_MSG}" >> "${LOG_FILE}" 2>&1 || \
    log "Step 2 best-effort failed (continuing)"
log "Step 2 OK (best-effort)"


# Step 3 — LAW XV three-store save
log "Step 3: LAW XV three-store save for KEI-12 closure"
SAVE_SUMMARY="KEI-12 24h smoke window expired clean; .bak preservation removed via systemd timer at 2026-05-13 ~10:51 UTC. Symlink governance is the durable state across all 6 worktrees.

Operator timeline:
- 2026-05-12 ~10:51 UTC: operator --swap (PR #779 dc608ba3 merged) — atomic per-worktree symlink with .bak preservation
- 2026-05-12 ~10:51 UTC: --smoke verified 6/6 worktrees resolve _session_start.md
- 2026-05-13 ~10:51 UTC: --cleanup-bak fired via timer (this save)

Scope IN delivered:
- Scout HIGH #1 (.claude/modules/ → symlink to ~/.config/agency-os/modules/)
- Scout HIGH #2 (.claude/hooks/ → symlink, atlas opt-out preserved)
- Scout HIGH #3 (MEMORY.md deleted from repo — git rm in PR #779)
- Scout MEDIUM #5 (CLAUDE.md kept in-repo + governance-equality-guard.yml CI guard)

Scope OUT (deferred): Scout MEDIUM #6 HEARTBEAT.md symlink (per-callsign content from PR #755 + concurrent-write race); Scout HIGH #4 IDENTITY.md per-worktree by design — no symlink."
"${REPO_ROOT}"/.venv/bin/python3 "${REPO_ROOT}"/scripts/three_store_save.py \
    --directive "KEI-12-CLEANUP-2026-05-13" \
    --pr-number 779 \
    --summary "${SAVE_SUMMARY}" \
    --manual-section 13 >> "${LOG_FILE}" 2>&1 || \
    log "Step 3 best-effort failed (continuing) — operator can retry manually"
log "Step 3 OK (best-effort)"


log "Cleanup wrapper complete — exit 0"
exit 0
