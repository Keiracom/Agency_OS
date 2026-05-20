#!/usr/bin/env bash
# install_worktree_identity.sh — bootstrap IDENTITY.md into each callsign worktree.
#
# WHY THIS EXISTS (orchestrator audit 2026-05-20, bd Agency_OS-zeig):
# IDENTITY.md is gitignored (.gitignore — per-worktree host-side content, not
# repo-trackable). `git worktree add` therefore does NOT carry IDENTITY.md into
# a new worktree — it starts with no identity file and silently falls back to
# the CALLSIGN env var. The audit found IDENTITY.md absent from the orion and
# aiden worktrees: identity "worked" only via the env fallback, not the
# documented LAW-XVII primary source.
#
# This script is the permanent fix: it writes IDENTITY.md to each worktree from
# that worktree's repo-tracked source-of-truth — docs/runbooks/<callsign>-identity.md
# (the first ```markdown fenced block). Idempotent. Run after `git worktree add`.
#
# A worktree whose callsign has no docs/runbooks/<callsign>-identity.md is
# skipped with a warning — author the runbook first (it is the canonical
# source). As of 2026-05-20 runbooks exist for: orion, scout.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# callsign → worktree path. Extend as worktrees are added.
WORKTREES=(
    "orion:/home/elliotbot/clawd/Agency_OS-orion"
    "scout:/home/elliotbot/clawd/Agency_OS-scout"
    "atlas:/home/elliotbot/clawd/Agency_OS-atlas"
    "aiden:/home/elliotbot/clawd/Agency_OS-aiden"
)

rc=0
for entry in "${WORKTREES[@]}"; do
    cs="${entry%%:*}"
    wt="${entry#*:}"
    runbook="$REPO_ROOT/docs/runbooks/${cs}-identity.md"
    dest="$wt/IDENTITY.md"

    if [[ ! -d "$wt" ]]; then
        echo "skip ${cs} — worktree absent ($wt)"
        continue
    fi
    if [[ ! -f "$runbook" ]]; then
        if [[ -f "$dest" ]]; then
            # No runbook, but the worktree already has an IDENTITY.md — healthy,
            # just not runbook-bootstrappable. Not an error.
            echo "ok ${cs} — IDENTITY.md present; no runbook to re-bootstrap from"
        else
            echo "WARN: ${cs} — IDENTITY.md MISSING and no canonical runbook" \
                 "($runbook); author the runbook first, then re-run" >&2
            rc=1
        fi
        continue
    fi

    # Two supported runbook shapes:
    #  (a) a wrapped runbook with the IDENTITY content in a ```markdown fence
    #      (e.g. orion-identity.md) — extract the first fenced block;
    #  (b) the runbook IS the raw IDENTITY content, starting with '# IDENTITY'
    #      (e.g. aiden-identity.md) — use the whole file.
    block="$(awk '/^```markdown$/{f=1;next} /^```$/{if(f)exit} f' "$runbook")"
    if [[ -z "$block" ]] && head -1 "$runbook" | grep -q '^# IDENTITY'; then
        block="$(cat "$runbook")"
    fi
    if [[ -z "$block" ]]; then
        echo "WARN: ${cs} — runbook is neither a \`\`\`markdown block nor raw" \
             "'# IDENTITY' content; cannot bootstrap" >&2
        rc=1
        continue
    fi
    printf '%s\n' "$block" > "$dest"
    echo "wrote ${dest} ($(wc -l < "$dest") lines) from $(basename "$runbook")"
done

exit "$rc"
