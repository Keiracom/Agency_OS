# HEARTBEAT.md

Agent-maintained continuation anchor. Updated before context fills up so the
post-compaction session can resume without re-deriving state. Read at session
start, snapshotted by the PreCompact hook (scripts/pre_compact_alert.py).

## Active Task

- Directive: KEI-90 (Gate 3 — peer-verify on deployment-class KEIs)
- Goal: rebuild PR #928 on post-#925 main; ship Gate 3 with Dave-solo-ops 2-of-3 path
- Phase: verify → report (tests 11/11, ruff clean, KEI-108 gate clean; commit + push pending)
- Files touched (current PR): scripts/tasks_cli.py, supabase/migrations/20260517_kei90_gate3_deployment_peer_verify.sql, tests/scripts/test_tasks_cli_gate3.py

## Last Good Commit

- SHA: 66696057
- Branch: origin/main
- Subject: refactor(kei107): deduplicate mock helpers in test_cognee_session_start (#926)

## Model

- Configured: claude-opus-4-7
- Running: unknown — check tmux session launch command

## Blockers

- none

## Next Action

- Commit + push max/kei90-gate3-rebased; update PR #928 (or open replacement). After dual-concur, merge per Dave PR-duty directive.

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
