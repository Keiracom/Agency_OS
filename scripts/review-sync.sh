#!/usr/bin/env bash
set -eu

BRANCH="${1:?Usage: review-sync.sh <branch-name>}"
REVIEW_WT="/home/elliotbot/clawd/Agency_OS-aiden-review"

if [ ! -d "$REVIEW_WT" ]; then
    echo "ERROR: Review worktree '$REVIEW_WT' does not exist."
    echo "Create it first with:"
    echo "  git worktree add /home/elliotbot/clawd/Agency_OS-aiden-review main"
    exit 2
fi

git -C "$REVIEW_WT" fetch origin
git -C "$REVIEW_WT" checkout "$BRANCH"

echo ""
echo "=== git status: $REVIEW_WT ==="
git -C "$REVIEW_WT" status
