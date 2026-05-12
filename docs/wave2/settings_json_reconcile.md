# Wave 2 Research — `.claude/settings.json` Reconciliation

**Read fresh 2026-05-12.** Orion's audit (Drift 3) claimed 4 distinct shapes across 6 worktrees. Current state shows **2 shapes** — most have already converged. Updated finding:

## Current state (md5 + size)

| Worktree | md5 | LOC | Bytes |
|---|---|---|---|
| Agency_OS (main) | a2f3fee5… | 250 | 6624 |
| Agency_OS-aiden | a2f3fee5… | 250 | 6624 |
| Agency_OS-orion | a2f3fee5… | 250 | 6624 |
| Agency_OS-max | a2f3fee5… | 250 | 6624 |
| Agency_OS-scout | a2f3fee5… | 250 | 6624 |
| Agency_OS-atlas | 7b33623f… | 228 | 5999 |

**Convergence already achieved: 5/6 worktrees share an identical settings.json.** Only Atlas is forked.

The Drift 3 audit appears to have been taken before a prior reconciliation pass (or before Max/Scout were re-synced). Orion's then-claim of "max forked bigger, atlas forked smaller, scout smallest" no longer holds — only Atlas is out of band, and it is *smaller* than the canonical baseline.

## Diff: main → atlas

`diff /home/elliotbot/clawd/Agency_OS/.claude/settings.json /home/elliotbot/clawd/Agency_OS-atlas/.claude/settings.json`

Atlas is **missing** three hook entries that exist in the canonical file:

1. **SessionStart hook (extra command):** `anti_amnesia_capsule.py --read` — runs at session start, reads pinned context.
2. **UserPromptSubmit hook block (entire matcher):**
   ```json
   "UserPromptSubmit": [
     {"matcher": "*", "hooks": [
       {"type": "command", "command": "bash .claude/hooks/session_store_userpromptsubmit.sh", "timeout": 5}
     ]}
   ]
   ```
3. **Stop hook (extra command):** `anti_amnesia_capsule.py` (write side) — runs at session stop, snapshots pinned context.

Net effect on Atlas: no anti-amnesia capsule read/write, no session_store on prompt submit. Atlas sessions run "thinner" — they don't push context into the shared session store or pull the capsule back at startup.

## Local override layer

`.claude/settings.local.json` exists in only 2 worktrees:
- Agency_OS (main): 752 b
- Agency_OS-atlas: 416 b

`settings.local.json` is git-ignored by Claude Code convention. These are per-host overrides and should not be reconciled.

## Recommended canonical shape

**(a) main is canonical, force-sync atlas.** Single-file world is simpler than an overlay system, the divergence is one-way (atlas missing hooks, not adding any unique ones), and there's no clear architectural reason atlas should skip anti-amnesia or UserPromptSubmit hooks — those are runtime-safety features that benefit all callsigns equally.

Concrete Wave 2 action:
```bash
cp /home/elliotbot/clawd/Agency_OS/.claude/settings.json \
   /home/elliotbot/clawd/Agency_OS-atlas/.claude/settings.json
# verify md5 matches main, commit on atlas branch
```

**(b) per-callsign overlay** would solve a problem we don't have. With 5/6 already converged on one file, the overlay system's complexity (canonical base + merge logic + per-callsign delta files) isn't justified by 1 forked worktree.

**(c) restart atlas tmux session** after the file copy — Claude Code reads settings.json at session start, so a stale running session won't pick up the new hooks.

## One incidental finding

Scout worktree IDENTITY.md is missing (stash@{1} on scout side holds the working-copy version; HEAD doesn't have it). Not in Wave 2 scope but flagging for triage — Scout sessions currently can't run the `LAW XVII callsign verification` step described in CLAUDE.md.
