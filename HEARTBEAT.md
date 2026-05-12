# HEARTBEAT.md

Agent-maintained continuation anchor. Updated before context fills up so the
post-compaction session can resume without re-deriving state. Read at session
start, snapshotted by the PreCompact hook (scripts/pre_compact_alert.py).

## Active Task

- Directive: <directive number or label>
- Goal: <one-line>
- Phase: <scope/decompose/execute/verify/report>
- Files touched (current PR): <list>

## Last Good Commit

- SHA: <git short-sha>
- Branch: <branch-name>
- Subject: <commit subject line>

## Model

- Configured: <callsign-from-IDENTITY.md → lookup in ceo_memory key `orchestration:model_assignment` (SQL-anchored Elliot UPSERT 2026-05-12 22:45:30 UTC)>
- Running: <actual `--model` flag at startup, if known; otherwise "unknown — check tmux session launch command">

## Blockers

- <bulleted list, or "none">

## Next Action

- <single concrete next step the next session should execute>

## Heartbeat Cadence (CLAUDE.md context thresholds)

- 40% — self-alert; consider HEARTBEAT update
- 50% — alert Dave via Slack
- 60% — execute session-end protocol
- 70% — pre-compaction warning fires (this template snapshotted)

On heartbeat check:
1. Context health — if >60%, alert Dave and prepare for restart.
2. Anything urgent? — blockers, failures, opportunities.
3. Active work? — something in progress that needs follow-up?

If nothing needs attention: `HEARTBEAT_OK`
If something does: brief summary, no fluff.
