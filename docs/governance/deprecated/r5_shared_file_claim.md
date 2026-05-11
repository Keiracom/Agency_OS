# Deprecated Rule: R5 — SHARED-FILE-CLAIM

**Retired:** 2026-05-11 via PR #1b (TBD)
**Replaced by:** Structural prevention (per-callsign worktrees; cross-worktree edits are rare and surface via PR review) + self-enforcing CLAIM protocol convention

## Incident that created this rule

In the early Telegram-relay era, Aiden and Elliot occasionally edited the same shared files (`memory_listener.py`, `chat_bot.py`, `store.py`, `listener_discernment.py`, CLAUDE.md) without coordinating. The result was either merge conflicts (cheap) or silent overwrites where one bot's edit nullified the other's intent without anyone noticing until the behaviour regressed in production.

R5 was added to enforce `[CLAIM:<callsign>]` tagging before editing shared files, so the other bot would see "this file is mine for the next ~minutes" before starting their own edit.

## Original RULES_PROMPT text (verbatim, pre-retirement)

```
Rule 5 — SHARED-FILE-CLAIM: If the current message mentions editing memory_listener.py, chat_bot.py, store.py, listener_discernment.py, or any CLAUDE.md file, check if "[CLAIM:" was posted. Missing claim = VIOLATION.
```

## Why this is safe to retire

Multiple structural changes have made the original incident class effectively impossible or self-correcting:

1. **Per-callsign worktrees.** Each callsign now operates in their own git worktree (`Agency_OS`, `Agency_OS-aiden`, `Agency_OS-max`, `Agency_OS-atlas`, `Agency_OS-orion`). The "shared file" list R5 watched is now per-worktree by default. Cross-worktree edits require explicit ownership-crossing and are rare enough to be surfaced via PR review naturally.

2. **CLAIM protocol is self-enforcing in practice.** When peers do edit shared files (e.g., cross-worktree edits in `bot_common/` during Phase 4-5 enforcer audit), they explicitly post `[CLAIM:<callsign>]` because the pattern is now part of the team workflow vocabulary. The LLM check was redundant.

3. **Zero R5 fires in the 2026-05-11 audit window** despite multiple cross-worktree edits during the Slack migration. The check produced no signal because the convention was already followed.

4. **Bot inbox cross-post is bot-only.** Real-time visibility between bot tmux panes (the inbox-mirror layer) means a peer seeing "I'm editing X" gets immediate awareness even without a formal CLAIM tag.

## Verification

```bash
# Confirm zero R5 fires today (or recent):
grep -c 'Rule 5' /home/elliotbot/clawd/logs/aiden-slack-listener.log
# Expected: 0 in recent windows

# Confirm CLAIM protocol still in active use (regression check):
grep -c '\[CLAIM:' /tmp/telegram-relay-aiden/processed/slack_*.json | head
# Expected: nonzero — peers using the protocol voluntarily
```

## What to watch for

If two peers start editing overlapping bot_common/ files without CLAIM coordination and produce silent overwrites — investigate:
1. Did the worktree boundaries get muddied (e.g., a bot editing another bot's worktree without claiming)?
2. Did the convention stop being followed because the LLM check stopped firing?
3. Are cross-worktree edits surfacing only as merge conflicts (not silent overwrites)?

If silent-overwrite incidents recur, restore R5 as a deterministic regex check (match shared-file paths + grep for `[CLAIM:` in recent messages) — that was the proposed implementation before retirement.
