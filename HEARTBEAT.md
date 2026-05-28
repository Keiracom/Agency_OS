# HEARTBEAT.md

Agent-maintained continuation anchor. Updated before context fills up so the
post-compaction session can resume without re-deriving state. Read at session
start, snapshotted by the PreCompact hook (scripts/pre_compact_alert.py).

## Active Task

- Directive: PR review pass — 9 open PRs reviewed (1223–1234) + HEARTBEAT refresh
- Phase: complete
- Reviewed: 1223 (ORION budget gate), 1225 (ORION spawn attribution), 1228 (SCOUT Hindsight primitives), 1229 (NOVA go_sidecar Wave 1), 1230 (SCOUT invalidation), 1231 (ATLAS tenant scoping), 1232 (NOVA reranker Wave 2), 1233 (ORION bounded-spawn kill), 1234 (SCOUT recency decay)
- Merge-eligible now (both MAX+AIDEN): 1223, 1225, 1233

## Last Good Commit

- SHA: 5f0c03c89
- Branch: origin/main
- Subject: Merge remote-tracking branch 'origin/main'
- Note: PR #1123 (MAX migration manifest seed + enforcer) MERGED. All 9 open PRs now have MAX review. PRs 1223/1225/1233 have dual deliberator concur — Elliot to admin-merge.

## Model

- Configured: claude-opus-4-7
- Running: unknown — check tmux session launch command

## Blockers

- none

## Next Action

- Await Aiden review on PRs 1228–1232, 1234 (MAX already posted; need Elliot+Aiden for merge eligibility)
- bd ready for next claim once review queue clears
- PR #1234 (recency decay): medium finding on non-numeric score guard — author (Scout) should address before merge per GOV-10

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
