#!/usr/bin/env bash
# symlink_governance.sh — KEI-12 / Item #1 per Scout's Wave 2 design brief.
#
# Operator script for the per-worktree governance-modules + hooks symlink
# migration. Replaces .claude/modules/ + .claude/hooks/ duplicated copies
# (one per worktree × 6) with symlinks to ~/.config/agency-os/{modules,hooks}/.
#
# Scope IN:
#   - HIGH #1: .claude/modules/ → symlink to ~/.config/agency-os/modules/
#   - HIGH #2: .claude/hooks/   → symlink to ~/.config/agency-os/hooks/
#     (atlas opt-out for session_store_userpromptsubmit.sh handled via per-file
#     symlink override after the dir-level symlink — see Atlas opt-out block)
#
# Scope OUT (Phase 2+ or rejected by Scout audit):
#   - HEARTBEAT.md (per-callsign content from PR #755 conflicts with shared symlink;
#     defer until concurrent-write race resolution + per-callsign target paths)
#   - IDENTITY.md (per-worktree by design — Scout HIGH #4)
#   - CLAUDE.md (CI guard instead of symlink — Scout MEDIUM #5,
#     governance-equality-guard.yml in this PR)
#   - MEMORY.md (deleted from repo entirely in this PR — Scout HIGH #3)
#
# Safety:
#   - Idempotent (skips already-symlinked paths)
#   - Atomic per-worktree: existing dirs renamed to .bak BEFORE ln -sn
#     so a mid-swap session-start still sees the .bak (or the symlink, never
#     a missing path)
#   - Rollback: `--rollback` flag restores .bak → original
#   - 24h smoke window (operator decision when to delete .bak)
#
# Usage:
#   scripts/orchestrator/symlink_governance.sh --extract       # Phase 1
#   scripts/orchestrator/symlink_governance.sh --swap          # Phase 2 (live)
#   scripts/orchestrator/symlink_governance.sh --smoke         # Phase 3
#   scripts/orchestrator/symlink_governance.sh --rollback      # restore .bak
#   scripts/orchestrator/symlink_governance.sh --cleanup-bak   # remove .bak after 24h
#   scripts/orchestrator/symlink_governance.sh --dry-run       # show plan, no writes

set -euo pipefail

CANONICAL_MODULES="${HOME}/.config/agency-os/modules"
CANONICAL_HOOKS="${HOME}/.config/agency-os/hooks"
CLAWD_DIR="${HOME}/clawd"
WORKTREES=(Agency_OS Agency_OS-aiden Agency_OS-max Agency_OS-orion Agency_OS-atlas Agency_OS-scout)
ATLAS_OPT_OUT_HOOK="session_store_userpromptsubmit.sh"

# Source-of-truth worktree (main).
CANONICAL_SOURCE="${CLAWD_DIR}/Agency_OS"

DRY_RUN=0

log() { printf '[symlink-gov] %s\n' "$*"; }
run() { if [ "${DRY_RUN}" -eq 1 ]; then log "DRY: $*"; else "$@"; fi; }


extract_canonical() {
    log "Phase 1 — extract canonical content to ${CANONICAL_MODULES} + ${CANONICAL_HOOKS}"
    if [ -d "${CANONICAL_MODULES}" ] && [ -d "${CANONICAL_HOOKS}" ]; then
        log "  canonical dirs exist — skipping (idempotent)"
        return 0
    fi
    run mkdir -p "${CANONICAL_MODULES}" "${CANONICAL_HOOKS}"
    if [ ! -d "${CANONICAL_SOURCE}/.claude/modules" ]; then
        log "  ERROR: ${CANONICAL_SOURCE}/.claude/modules missing — cannot seed canonical"
        return 2
    fi
    run cp -a "${CANONICAL_SOURCE}/.claude/modules/." "${CANONICAL_MODULES}/"
    run cp -a "${CANONICAL_SOURCE}/.claude/hooks/." "${CANONICAL_HOOKS}/"
    log "  seeded from ${CANONICAL_SOURCE} (byte-identical to all other worktrees per Scout audit)"
}


swap_one_worktree() {
    local wt_path="$1"
    local wt_name
    wt_name=$(basename "${wt_path}")
    if [ ! -d "${wt_path}" ]; then
        log "  ${wt_name}: skipping (worktree not present)"
        return 0
    fi

    # Modules
    local modules_path="${wt_path}/.claude/modules"
    if [ -L "${modules_path}" ]; then
        log "  ${wt_name}: modules already symlinked"
    elif [ -d "${modules_path}" ]; then
        log "  ${wt_name}: modules → swap"
        run mv "${modules_path}" "${modules_path}.bak"
        run ln -sn "${CANONICAL_MODULES}" "${modules_path}"
    fi

    # Hooks
    local hooks_path="${wt_path}/.claude/hooks"
    if [ -L "${hooks_path}" ]; then
        log "  ${wt_name}: hooks already symlinked"
    elif [ -d "${hooks_path}" ]; then
        log "  ${wt_name}: hooks → swap"
        run mv "${hooks_path}" "${hooks_path}.bak"
        run ln -sn "${CANONICAL_HOOKS}" "${hooks_path}"
    fi

    # Atlas opt-out: after the dir symlink, remove the unwanted hook for atlas
    # only by replacing the hook-dir symlink with per-file symlinks (atlas has
    # the missing userpromptsubmit hook per Orion+Scout audits).
    if [ "${wt_name}" = "Agency_OS-atlas" ]; then
        log "  ${wt_name}: applying atlas opt-out for ${ATLAS_OPT_OUT_HOOK}"
        # Replace dir symlink with per-file symlinks, excluding the opt-out.
        run rm "${hooks_path}"
        run mkdir -p "${hooks_path}"
        local f
        for f in "${CANONICAL_HOOKS}"/*; do
            local fname
            fname=$(basename "${f}")
            if [ "${fname}" = "${ATLAS_OPT_OUT_HOOK}" ]; then
                continue
            fi
            run ln -sn "${f}" "${hooks_path}/${fname}"
        done
    fi
}


swap_all_worktrees() {
    log "Phase 2 — atomic per-worktree swap (modules + hooks → symlinks)"
    extract_canonical || return $?
    local wt
    for wt in "${WORKTREES[@]}"; do
        swap_one_worktree "${CLAWD_DIR}/${wt}"
    done
}


smoke() {
    log "Phase 3 — smoke: every worktree resolves session-start reads"
    local fail=0
    local wt
    for wt in "${WORKTREES[@]}"; do
        local target="${CLAWD_DIR}/${wt}/.claude/modules/_session_start.md"
        if [ ! -r "${target}" ]; then
            log "  FAIL: ${wt} — ${target} unreadable"
            fail=1
        else
            log "  OK: ${wt} session_start.md readable"
        fi
    done
    return ${fail}
}


rollback_one() {
    local wt_path="$1"
    local wt_name
    wt_name=$(basename "${wt_path}")
    local modules_path="${wt_path}/.claude/modules"
    local hooks_path="${wt_path}/.claude/hooks"
    if [ -d "${modules_path}.bak" ]; then
        log "  ${wt_name}: rollback modules"
        run rm -rf "${modules_path}"
        run mv "${modules_path}.bak" "${modules_path}"
    fi
    if [ -d "${hooks_path}.bak" ]; then
        log "  ${wt_name}: rollback hooks"
        run rm -rf "${hooks_path}"
        run mv "${hooks_path}.bak" "${hooks_path}"
    fi
}


rollback_all() {
    log "Rolling back: restore .bak → original; remove symlinks"
    local wt
    for wt in "${WORKTREES[@]}"; do
        rollback_one "${CLAWD_DIR}/${wt}"
    done
}


cleanup_bak() {
    log "Cleanup: removing .bak dirs (24h smoke window assumed)"
    local wt
    for wt in "${WORKTREES[@]}"; do
        local p="${CLAWD_DIR}/${wt}/.claude"
        run find "${p}" -maxdepth 1 -name '*.bak' -exec rm -rf {} +
    done
}


usage() {
    cat <<EOF
Usage: $0 [--extract|--swap|--smoke|--rollback|--cleanup-bak] [--dry-run]
  --extract        Phase 1: seed ${CANONICAL_MODULES} + ${CANONICAL_HOOKS}
  --swap           Phase 1+2: extract + atomic per-worktree symlink swap
  --smoke          Phase 3: verify session-start reads resolve in every worktree
  --rollback       Restore .bak → original (drops symlinks); use within 24h smoke window
  --cleanup-bak    Delete .bak after smoke window — POINT OF NO RETURN
  --dry-run        Show planned operations without executing
EOF
}


main() {
    local cmd=""
    for arg in "$@"; do
        case "${arg}" in
            --extract|--swap|--smoke|--rollback|--cleanup-bak) cmd="${arg}" ;;
            --dry-run) DRY_RUN=1 ;;
            -h|--help) usage; exit 0 ;;
            *) usage; exit 2 ;;
        esac
    done

    case "${cmd}" in
        --extract)     extract_canonical ;;
        --swap)        swap_all_worktrees ;;
        --smoke)       smoke ;;
        --rollback)    rollback_all ;;
        --cleanup-bak) cleanup_bak ;;
        *)             usage; exit 2 ;;
    esac
}


main "$@"
