#!/usr/bin/env bash
# Usage: verify_pr.sh <pr_number>
# Outputs JSON: {"pr": <num>, "state": "...", "merged": bool, "merge_sha": "...",
#                "ci_passing": bool, "failed_checks": [...], "pending_checks": [...]}
# Exit 0 on successful query, 2 on PR not found, 1 on gh error.
#
# Gating checks (failures block merge): Backend Tests, MyPy, Frontend Checks, Dead Reference Guard
# Non-blocking (pre-existing): Ruff/Backend Lint, SonarCloud, Vercel deployments — these are
# allowed to fail/skip without marking ci_passing=false per repo precedent.

set -uo pipefail

PR_NUM="${1:-}"
if [[ -z "$PR_NUM" ]]; then
    echo '{"error": "usage: verify_pr.sh <pr_number>"}' >&2
    exit 1
fi

# --- Fetch PR state ---
PR_JSON=$(gh pr view "$PR_NUM" --json state,mergedAt,mergeCommit 2>&1)
GH_EXIT=$?

if [[ $GH_EXIT -ne 0 ]]; then
    if echo "$PR_JSON" | grep -qi "could not resolve\|no pull requests found\|not found"; then
        echo "{\"pr\": $PR_NUM, \"error\": \"PR not found\"}"
        exit 2
    fi
    echo "{\"pr\": $PR_NUM, \"error\": \"gh error\", \"detail\": $(echo "$PR_JSON" | jq -Rs .)}"
    exit 1
fi

STATE=$(echo "$PR_JSON" | jq -r '.state')
MERGED_AT=$(echo "$PR_JSON" | jq -r '.mergedAt // ""')
MERGE_SHA=$(echo "$PR_JSON" | jq -r '.mergeCommit.oid // ""')

if [[ "$MERGED_AT" != "" && "$MERGED_AT" != "null" ]]; then
    MERGED=true
else
    MERGED=false
fi

# --- Fetch checks (plain text, --json unsupported in this gh version) ---
# Capture both output and exit code separately. `gh pr checks` exits non-zero when
# (a) PR has no checks, (b) any check is failing (intentional gh behaviour), or
# (c) gh hits a network/auth error. (a) and (b) are recoverable — the output is
# still valid for parsing. (c) leaves output empty/error — must NOT ghost-green.
CHECKS_OUTPUT=$(gh pr checks "$PR_NUM" 2>&1)
CHECKS_EXIT=$?

# Detect a real gh failure (auth/network) vs "exit non-zero because checks failed":
# real failures emit error text and no tab-delimited rows. Anything with at least
# one tab-delimited row is parseable.
if [[ $CHECKS_EXIT -ne 0 ]] && ! echo "$CHECKS_OUTPUT" | grep -q $'\t'; then
    # gh itself failed — ci state unknown. Emit explicit unknown rather than green.
    jq -n \
        --argjson pr "$PR_NUM" \
        --arg state "$STATE" \
        --argjson merged "$MERGED" \
        --arg merge_sha "$MERGE_SHA" \
        --arg detail "$(echo "$CHECKS_OUTPUT" | head -c 200)" \
        '{pr: $pr, state: $state, merged: $merged, merge_sha: $merge_sha,
          ci_passing: null, ci_status: "unknown", failed_checks: [], pending_checks: [],
          detail: $detail}'
    exit 1
fi

# Extract failed gating checks
# Gating: "Backend Tests", "MyPy" (via "Backend Type Check"), "Frontend Checks", "Dead Reference Guard"
# Non-gating (skip): "Ruff", "Backend Lint", "SonarCloud", "Vercel"
FAILED=$(echo "$CHECKS_OUTPUT" | awk -F'\t' '
    $2 == "fail" {
        name = $1
        if (name ~ /[Rr]uff/ || name ~ /[Ss]onar/ || name ~ /[Vv]ercel/ || name ~ /[Bb]ackend [Ll]int/) next
        print name
    }
' | jq -Rsc 'split("\n") | map(select(length > 0))')

PENDING=$(echo "$CHECKS_OUTPUT" | awk -F'\t' '
    $2 == "pending" || $2 == "in_progress" || $2 == "queued" {
        name = $1
        if (name ~ /[Rr]uff/ || name ~ /[Ss]onar/ || name ~ /[Vv]ercel/ || name ~ /[Bb]ackend [Ll]int/) next
        print name
    }
' | jq -Rsc 'split("\n") | map(select(length > 0))')

FAILED_CHECKS="${FAILED:-[]}"
PENDING_CHECKS="${PENDING:-[]}"

# ci_passing = no gating failures and no gating pending
if [[ "$FAILED_CHECKS" == "[]" && "$PENDING_CHECKS" == "[]" ]]; then
    CI_PASSING=true
else
    CI_PASSING=false
fi

# --- Compose output ---
jq -n \
    --argjson pr "$PR_NUM" \
    --arg state "$STATE" \
    --argjson merged "$MERGED" \
    --arg merge_sha "$MERGE_SHA" \
    --argjson ci_passing "$CI_PASSING" \
    --argjson failed_checks "$FAILED_CHECKS" \
    --argjson pending_checks "$PENDING_CHECKS" \
    '{pr: $pr, state: $state, merged: $merged, merge_sha: $merge_sha,
      ci_passing: $ci_passing, failed_checks: $failed_checks, pending_checks: $pending_checks}'
