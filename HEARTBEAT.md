# HEARTBEAT.md

Agent-maintained continuation anchor. Updated before context fills up so the
post-compaction session can resume without re-deriving state. Read at session
start, snapshotted by the PreCompact hook (scripts/pre_compact_alert.py).

## Active Task

- Directive: KEI-185 follow-up — S5603 unused-fn cleanup (test_spawn_nova.py:33 `_raise_on_import` removed) + HEARTBEAT refresh
- Goal: clear Max's one-line lint suggestion from PR #1006 review + keep HEARTBEAT current post-PR-1006-merge
- Phase: building → PR pending
- Files touched: tests/scripts/test_spawn_nova.py (S5603 fix), HEARTBEAT.md (state refresh)

## Last Good Commit

- SHA: 815cdbefe
- Branch: origin/main
- Subject: [AIDEN] feat(kei185): Nova engineer-clone scaffold + supervisor v2 enable flag (#1006)
- Note: KEI-185 MERGED. KEI-199+204 also MERGED via PR #1000 (85e4a9a48). KEI-205 NATS install MERGED via PR #1005 (879b06b27). Supervisor v2 flip-on path: gated on KEI-183 (Elliot PR #990, NATS-redirect shipped at f33252a89, awaiting Max second concur) + KEI-184 (Orion PR #1004, on HOLD for 7× CRITICAL S5443 + 3× MINOR S100).

## Model

- Configured: claude-opus-4-7
- Running: unknown — check tmux session launch command

## Blockers

- none

## Next Action

- Wait for peer review on PR #1000 (KEI-199 + KEI-204). After dual-concur, merge per Dave PR-duty directive.
- T1-overflow standing: bd ready shows KEI-183 (Elliot lane, PR #990) + KEI-185 (dep-blocked on KEI-183+184). No claim unless explicitly redirected.
- Drift-sync count this session: 12 (recorded in #execution thread). PR #1000 closes 2 of 3 supervisor blind spots once merged.

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
