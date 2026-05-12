#!/usr/bin/env bash
# install_systemd_units.sh — idempotent post-merge installer for repo systemd units.
#
# Closes Beads Agency_OS-34s. Pattern A class problem: PRs shipping new .service
# / .timer files into the repo (e.g. PR #774 polling timer, PR #784 cleanup
# timer, PR #776 + #777 alerters from this session) need a manual
#   cp + systemctl --user daemon-reload + enable --now
# on the host. Easy to forget — PR #774's timer silently didn't run for a
# stretch until Dave noticed. This installer enumerates repo unit files,
# diffs them against the host install dir, copies new/changed files,
# daemon-reloads, and enables+starts NEW .timer files. Idempotent: re-runs
# on an unchanged repo do nothing and exit 0.
#
# Scope decisions:
#   - Enable+start applies to .timer files only. Companion .service files
#     are pulled in by the timer's [Install] WantedBy=timers.target.
#   - Standalone .service files (no companion .timer, e.g. relay-watchers
#     or daemons) are INSTALLED but NOT auto-enabled — operator decides
#     when to start a long-running daemon.
#   - Units already on the host but REMOVED from the repo are LEFT ALONE.
#     Removal is an explicit operator decision, not an automated sweep.
#   - Dave-directed activation preserved: this script is invoked manually
#     by an operator (no GH Action auto-run). Running it equals operator
#     intent to activate everything in the repo.
#
# Usage:
#   scripts/orchestrator/install_systemd_units.sh            # real install
#   scripts/orchestrator/install_systemd_units.sh --dry-run  # report only
#
# Env overrides (testing + non-default hosts):
#   AGENCY_OS_SYSTEMD_SOURCE_DIRS  — colon-separated list of source dirs
#                                    (default: infra/alerts:infra/cron:infra/opa:systemd)
#   AGENCY_OS_SYSTEMD_INSTALL_DIR  — host install dir (default ~/.config/systemd/user)
#   AGENCY_OS_SYSTEMCTL            — systemctl binary path (default 'systemctl')
#   AGENCY_OS_SYSTEMCTL_SKIP       — if set, skip every systemctl invocation
#                                    (unit tests use this so they don't touch the
#                                    real user systemd instance)
#
# Exit codes: 0 on success or clean no-op; 1 on copy/systemctl failure; 2 on
# bad arguments.

set -euo pipefail

# ─── Args ──────────────────────────────────────────────────────────────
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h | --help)
            sed -n '2,40p' "$0"
            exit 0
            ;;
        *)
            echo "error: unknown arg: $arg" >&2
            exit 2
            ;;
    esac
done

# ─── Config ────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEFAULT_SOURCE_DIRS="infra/alerts:infra/cron:infra/opa:systemd"
SOURCE_DIRS="${AGENCY_OS_SYSTEMD_SOURCE_DIRS:-$DEFAULT_SOURCE_DIRS}"
INSTALL_DIR="${AGENCY_OS_SYSTEMD_INSTALL_DIR:-$HOME/.config/systemd/user}"
SYSTEMCTL_BIN="${AGENCY_OS_SYSTEMCTL:-systemctl}"

# ─── Helpers ───────────────────────────────────────────────────────────
log() { printf '%s\n' "$*"; }
note() { printf '[install_systemd_units] %s\n' "$*"; }

run_systemctl() {
    # Wraps systemctl --user so unit tests can short-circuit via env.
    if [ -n "${AGENCY_OS_SYSTEMCTL_SKIP:-}" ]; then
        note "(skipped) systemctl --user $*"
        return 0
    fi
    "$SYSTEMCTL_BIN" --user "$@"
}

file_hash() { sha256sum "$1" 2>/dev/null | awk '{print $1}'; }

# Returns "new" / "changed" / "unchanged" for a source unit file.
classify_unit() {
    local src="$1" dest="$2"
    if [ ! -f "$dest" ]; then
        echo "new"
        return
    fi
    local sh dh
    sh="$(file_hash "$src")"
    dh="$(file_hash "$dest")"
    if [ "$sh" = "$dh" ]; then
        echo "unchanged"
    else
        echo "changed"
    fi
}

# ─── Discover source units ─────────────────────────────────────────────
declare -a SOURCE_UNITS=()
IFS=':' read -r -a SRC_ARR <<<"$SOURCE_DIRS"
for sd in "${SRC_ARR[@]}"; do
    abs="$REPO_ROOT/$sd"
    [ -d "$abs" ] || continue
    while IFS= read -r -d '' f; do
        SOURCE_UNITS+=("$f")
    done < <(find "$abs" -maxdepth 1 -type f \( -name '*.service' -o -name '*.timer' \) -print0 2>/dev/null)
done

if [ "${#SOURCE_UNITS[@]}" -eq 0 ]; then
    note "no source unit files found under: $SOURCE_DIRS"
    exit 0
fi

# ─── Plan ──────────────────────────────────────────────────────────────
declare -a NEW_FILES=()
declare -a CHANGED_FILES=()
declare -a NEW_TIMERS=()
mkdir -p "$INSTALL_DIR"

for src in "${SOURCE_UNITS[@]}"; do
    name="$(basename "$src")"
    dest="$INSTALL_DIR/$name"
    cls="$(classify_unit "$src" "$dest")"
    case "$cls" in
        new)
            NEW_FILES+=("$src")
            [[ "$name" == *.timer ]] && NEW_TIMERS+=("$name")
            ;;
        changed)
            CHANGED_FILES+=("$src")
            ;;
        unchanged) : ;;
    esac
done

new_count=${#NEW_FILES[@]}
chg_count=${#CHANGED_FILES[@]}
total=$((new_count + chg_count))

if [ "$total" -eq 0 ]; then
    note "no-op — all ${#SOURCE_UNITS[@]} source unit(s) already match host. exit 0."
    exit 0
fi

note "plan: ${new_count} new, ${chg_count} changed, ${#NEW_TIMERS[@]} timer(s) to enable+start"
for f in "${NEW_FILES[@]}"; do note "  NEW     $(basename "$f")"; done
for f in "${CHANGED_FILES[@]}"; do note "  CHANGED $(basename "$f")"; done

if [ "$DRY_RUN" -eq 1 ]; then
    note "--dry-run set — no files copied, no systemctl invoked. exit 0."
    exit 0
fi

# ─── Apply ─────────────────────────────────────────────────────────────
for src in "${NEW_FILES[@]}" "${CHANGED_FILES[@]}"; do
    name="$(basename "$src")"
    cp -f "$src" "$INSTALL_DIR/$name"
    note "  copied $name"
done

note "running daemon-reload"
run_systemctl daemon-reload

for t in "${NEW_TIMERS[@]}"; do
    note "  enable --now $t"
    run_systemctl enable --now "$t"
done

note "done — installed $total file(s); enabled ${#NEW_TIMERS[@]} new timer(s). exit 0."
exit 0
