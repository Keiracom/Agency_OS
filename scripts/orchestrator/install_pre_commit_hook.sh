#!/usr/bin/env bash
# install_pre_commit_hook.sh — KEI-22 D6 installer (operator-run, per-worktree).
#
# Per Dave directive ts ~1778667100: pre-commit hook installs in all 6
# worktrees (elliot/aiden/max/atlas/orion/scout).
#
# This script sets `core.hooksPath` on the current worktree to point at
# the repo-shipped `.githooks/` directory, so the pre-commit hook lives
# under version control + is automatically picked up.
#
# Idempotent: re-running on a worktree already pointing at .githooks/ is
# a no-op with a notice. Doesn't touch other worktrees on the same repo
# (git config --local is per-worktree by default with worktreeConfig
# enabled; we set it that way explicitly).
#
# Usage:
#     bash scripts/orchestrator/install_pre_commit_hook.sh
#     bash scripts/orchestrator/install_pre_commit_hook.sh --uninstall
#
# Dave-directed activation step — NOT run automatically by CI.

set -euo pipefail

UNINSTALL=0
for arg in "$@"; do
    case "$arg" in
        --uninstall) UNINSTALL=1 ;;
        -h | --help)
            sed -n '2,25p' "$0"
            exit 0
            ;;
        *)
            echo "error: unknown arg: $arg" >&2
            exit 2
            ;;
    esac
done

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.githooks"
WORKTREE="$(pwd)"

if [[ ! -d "$HOOKS_DIR" ]]; then
    echo "error: $HOOKS_DIR missing — run from a worktree that has KEI-22 D6 shipped." >&2
    exit 1
fi

if [[ ! -x "$HOOKS_DIR/pre-commit" ]]; then
    chmod +x "$HOOKS_DIR/pre-commit"
fi

if [[ $UNINSTALL -eq 1 ]]; then
    git config --unset core.hooksPath 2>/dev/null || true
    echo "Layer 3 pre-commit gate uninstalled on $WORKTREE."
    exit 0
fi

current="$(git config --get core.hooksPath || echo "")"
if [[ "$current" == "$HOOKS_DIR" || "$current" == ".githooks" ]]; then
    echo "Already installed — core.hooksPath=$current. No-op."
    exit 0
fi

git config core.hooksPath "$HOOKS_DIR"
echo "Layer 3 pre-commit gate installed on $WORKTREE."
echo "  core.hooksPath -> $HOOKS_DIR"
echo "  hook script    -> $HOOKS_DIR/pre-commit"
echo ""
echo "To verify: try 'git commit --allow-empty -m test' on a branch without a"
echo "valid bd claim. The hook should HARD-BLOCK with the KEI-22 D6 message."
echo ""
echo "Escape hatch for operator-authorised override: 'git commit --no-verify ...'."
echo "Strict mode (refuse even on bd-down): export AGENCY_OS_BD_HARDFAIL=1."
