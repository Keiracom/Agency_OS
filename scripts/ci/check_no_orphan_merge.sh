#!/usr/bin/env bash
# check_no_orphan_merge.sh — merge_to_proven_pipeline bind-gate, part (d).
#
# Blocks an ORPHAN MERGE: a migration that binds a gate_roadmap component to the
# proof path (sets proof_gate_contract, or INSERTs a component) WITHOUT also
# wiring a deploy_trigger for it. That is exactly the #1427 gap one rung up —
# a component provable + mergeable but with no deploy wiring (proven-but-never-
# deployed). GOV-12 (gates-as-code) applied to the pipeline rule itself.
#
# Repo-only + diff-based (CI has no DB), mirroring check_operational_deployment.sh:
# scans migrations ADDED/MODIFIED in this PR vs the merge-base. Fails CLOSED on
# any git error (never a vacuous pass).
#
# Override for the bind-proof harness: set ORPHAN_CHECK_FILES="f1 f2 ..." to
# check an explicit file list (used to feed a planted orphan fixture).
#
# Exit 0 = no orphan. Exit 1 = orphan merge detected (or git error).

set -uo pipefail

fail() { echo "::error::$*" >&2; FAILED=1; }
FAILED=0

# A migration BINDS a component to the proof path if it sets a proof contract
# or inserts a gate_roadmap component.
BIND_RE='proof_gate_contract|INSERT INTO public\.gate_roadmap'

check_file() {
    local f="$1"
    [[ -f "$f" ]] || return 0
    # Strip full-line SQL comments so a comment mentioning "deploy_trigger"
    # (or a contract keyword) can neither mask an orphan nor trip a false bind.
    local body
    body="$(grep -vE '^[[:space:]]*--' "$f")"
    if grep -qE "$BIND_RE" <<<"$body"; then
        if ! grep -qE 'deploy_trigger' <<<"$body"; then
            fail "ORPHAN MERGE: $f binds a component to the proof path (proof_gate_contract / gate_roadmap INSERT) but wires no deploy_trigger. A proof-path component MUST declare how it deploys (running_sha stampable) — else it is provable but never deployed (#1427 one rung up). Add a deploy_trigger for the component in this migration."
        else
            echo "ok: $f binds proof path AND wires a deploy_trigger"
        fi
    fi
}

if [[ -n "${ORPHAN_CHECK_FILES:-}" ]]; then
    # Explicit file list (bind-proof harness path).
    for f in $ORPHAN_CHECK_FILES; do check_file "$f"; done
else
    BASE_REF="${BASE_REF:-main}"
    git fetch --no-tags origin "$BASE_REF" >/dev/null 2>&1 || true
    if ! MERGE_BASE="$(git merge-base "origin/${BASE_REF}" HEAD 2>/dev/null)"; then
        echo "::error::check_no_orphan_merge cannot compute a merge-base for origin/${BASE_REF}...HEAD — failing CLOSED." >&2
        exit 1
    fi
    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        check_file "$f"
    done < <(git diff --name-only --diff-filter=AM "${MERGE_BASE}" HEAD -- 'supabase/migrations/*.sql')
fi

if [[ "$FAILED" -ne 0 ]]; then
    echo "::error::orphan-merge gate FAILED — see above." >&2
    exit 1
fi
echo "check_no_orphan_merge: no orphan merges."
exit 0
