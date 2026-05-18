#!/usr/bin/env bash
# check_callsign_match.sh — KEI-143 pre-commit hook.
#
# Enforces LAW XVII (Callsign Discipline): when CALLSIGN env is set, it MUST
# match the IDENTITY.md in the current worktree. Blocks commits with mismatched
# callsign so an agent operating in the wrong clone worktree can't accidentally
# tag commits with another callsign's identity.
#
# Behavior:
#   - CALLSIGN env unset                   → pass (warn-only). Humans running
#                                            `git commit` without the env var
#                                            shouldn't be blocked.
#   - CALLSIGN env set + IDENTITY.md missing → FAIL. Governance violation per
#                                            CLAUDE.md ("STOP if IDENTITY.md missing").
#   - CALLSIGN env set + value matches     → pass.
#   - CALLSIGN env set + value mismatches  → FAIL with clear error showing both
#                                            expected and actual callsigns.
#
# Usage (manual):
#   CALLSIGN=atlas bash scripts/git/check_callsign_match.sh
#
# Usage (pre-commit — wired via .pre-commit-config.yaml):
#   pre-commit runs this on every staged commit; non-zero exit blocks the commit.

set -eu

REPO_ROOT="$(git rev-parse --show-toplevel)"
IDENTITY_FILE="${REPO_ROOT}/IDENTITY.md"

# Unset CALLSIGN env → pass (humans + initial worktree setup before env is wired).
if [[ -z "${CALLSIGN:-}" ]]; then
    exit 0
fi

# CALLSIGN env set but IDENTITY.md missing → governance violation, block.
if [[ ! -f "${IDENTITY_FILE}" ]]; then
    echo "check_callsign_match: ERROR — CALLSIGN env is '${CALLSIGN}' but IDENTITY.md is missing from ${REPO_ROOT}." >&2
    echo "  Governance: per CLAUDE.md + LAW XVII, every worktree must carry an IDENTITY.md anchoring the callsign." >&2
    exit 1
fi

# Parse `**CALLSIGN:** <name>` from IDENTITY.md. Tolerant of leading/trailing
# whitespace + extra blank lines. Case-insensitive match on the key, lowercase
# the captured value for comparison.
identity_callsign="$(awk -F'\\*\\*CALLSIGN:\\*\\*[[:space:]]+' '/CALLSIGN/ {print $2; exit}' "${IDENTITY_FILE}" | tr '[:upper:]' '[:lower:]' | xargs)"
env_callsign="$(echo "${CALLSIGN}" | tr '[:upper:]' '[:lower:]' | xargs)"

if [[ -z "${identity_callsign}" ]]; then
    echo "check_callsign_match: ERROR — IDENTITY.md present but no '**CALLSIGN:** <name>' line found." >&2
    echo "  Expected format: '**CALLSIGN:** atlas' (or elliot / aiden / max / orion / scout / nova)." >&2
    exit 1
fi

if [[ "${env_callsign}" != "${identity_callsign}" ]]; then
    echo "check_callsign_match: ERROR — callsign mismatch." >&2
    echo "  CALLSIGN env: ${CALLSIGN}" >&2
    echo "  IDENTITY.md:  ${identity_callsign}" >&2
    echo "  You are running in the wrong worktree. Switch to the correct" >&2
    echo "  clone OR set CALLSIGN to match IDENTITY.md before committing." >&2
    exit 1
fi

exit 0
