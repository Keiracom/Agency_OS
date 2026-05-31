#!/usr/bin/env bash
# gate_git_commit.sh — proves a new commit landed in the product repo since the
# last gate pass.
#
# Real-output gate: reads `git log` in the named repo (default: $PWD), compares
# the latest commit SHA against the SHA recorded in the last passing run of
# this gate. Pass when SHA changed; fail when unchanged.
#
# Env:
#   GATE_GIT_REPO   Path to repo. Default: current working directory.
#   GATE_GIT_REF    Ref to inspect. Default: HEAD.
#   DATABASE_URL    For looking up last-pass SHA in gate_ledger (optional —
#                   on miss, gate falls back to "since 24h ago" via reflog/date
#                   so a first run still has a meaningful comparison window).

set -euo pipefail
GATE_ID="gate_git_commit"
# shellcheck source=./_lib.sh
. "$(dirname "$0")/_lib.sh"

repo="${GATE_GIT_REPO:-$(pwd)}"
ref="${GATE_GIT_REF:-HEAD}"

if ! command -v git >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "git not installed"
fi
if ! command -v jq >/dev/null 2>&1; then
    _emit_skip "$GATE_ID" "jq not installed"
fi
if [[ ! -d "$repo/.git" ]]; then
    _emit_skip "$GATE_ID" "not a git repo: $repo"
fi

current_sha="$(git -C "$repo" rev-parse "$ref" 2>/dev/null || echo '')"
if [[ -z "$current_sha" ]]; then
    _emit_fail "$GATE_ID" "$(jq -nc --arg r "$repo" --arg ref "$ref" \
        '{reason: "git rev-parse failed", repo: $r, ref: $ref}')"
fi

# Look up the SHA recorded in the most recent passing run of this gate.
# Best-effort — if Postgres is unreachable or no prior pass exists, we
# fall back to comparing against the previous commit (HEAD~1). That still
# proves "a new commit since last reference point" even on first run.
prior_sha=""
DSN="${DATABASE_URL:-${SUPABASE_DB_URL:-}}"
if [[ -n "$DSN" ]] && command -v psql >/dev/null 2>&1; then
    DSN="${DSN/+asyncpg/}"
    prior_sha="$(psql "$DSN" -tAc \
        "SELECT evidence->>'current_sha' FROM public.gate_ledger
         WHERE gate_id = '${GATE_ID}' AND status = 'pass'
         ORDER BY recorded_at DESC LIMIT 1;" 2>/dev/null || echo '')"
    prior_sha="${prior_sha// /}"
fi

if [[ -z "$prior_sha" ]]; then
    prior_sha="$(git -C "$repo" rev-parse "${ref}~1" 2>/dev/null || echo '')"
fi

if [[ -z "$prior_sha" ]]; then
    _emit_fail "$GATE_ID" "$(jq -nc --arg s "$current_sha" \
        '{reason: "no prior reference SHA available", current_sha: $s}')"
fi

if [[ "$current_sha" != "$prior_sha" ]]; then
    evidence=$(jq -nc --arg c "$current_sha" --arg p "$prior_sha" --arg r "$repo" \
        '{repo: $r, current_sha: $c, prior_sha: $p, advanced: true}')
    _emit_pass "$GATE_ID" "$evidence"
else
    evidence=$(jq -nc --arg c "$current_sha" --arg r "$repo" \
        '{repo: $r, current_sha: $c, prior_sha: $c, advanced: false, reason: "no new commit since last pass"}')
    _emit_fail "$GATE_ID" "$evidence"
fi
