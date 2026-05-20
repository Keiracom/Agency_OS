# S4 Supervisor v2 Cutover Runbook — Sequential Migration Order

**KEI:** [KEI-193](https://linear.app/keiracom/issue/KEI-193) (sub of [KEI-185](https://linear.app/keiracom/issue/KEI-185) Nova spawn + supervisor v2 flip)
**Status:** Refinement doc — ratified, not gate (KEI-185 owns the flip itself).
**Ratification:** 3-way ratified per Max's blast-radius concern. Replaces the parallel cutover plan that concentrated failure risk on the 3 highest-state agents.
**Owner:** Elliot (orchestrator) executes; this doc anchors the sequence + rollback per agent.

---

## TL;DR

```
Nova → Scout → Orion → Atlas → Aiden → Max → Elliot
  ^                                          ^
  spawn-test                            blast-radius peak
```

Sequential, **24h validation gate between every cutover**. No parallel.

---

## Why sequential (Max's blast-radius concern)

Parallel cutover of the 3 highest-state agents (Aiden / Max / Elliot) concentrates failure mode: any latent SessionManager bug surfaces simultaneously across the bots whose KEI-state recall is the most load-bearing. Sequential with a validation window between each lets:
1. Nova/Scout/Orion (lower-state, easier rollback) prove the path.
2. Atlas (moderate-state — 10 PRs this session, dispatcher chain ownership) is the canary for medium-blast-radius.
3. Aiden / Max / Elliot (deliberators + orchestrator, highest KEI-state recall) come last so the bench is empirically validated before their state is moved.

Cost: 6 × 24h = 6 days end-to-end. Acceptable in exchange for bounded blast radius. Big-bang would have been hours but fail-modes would be hours × N agents.

---

## Cutover sequence

| # | Agent | Why this position | Pre-cutover state weight | Rollback complexity |
|---|---|---|---|---|
| 1 | **Nova** | Net-new agent — proves SessionManager from cold. No legacy state to migrate. | Zero (spawn-test) | Trivial (delete worktree, no state lost) |
| 2 | **Scout** | Lowest legacy-state of the 6 — research/docs/component-shell lane. Latest 5 PRs are Wave-3 product shells, recoverable from git. | Low | Easy (re-checkout worktree, re-fetch IDENTITY) |
| 3 | **Orion** | Next-lowest — pgcrypto + Paddle handlers + systemd. Schema-touching work is in main branch already; rollback = re-pull. | Low-medium | Easy (same as Scout) |
| 4 | **Atlas** | Canary for medium blast radius — 10 PRs this session, dispatcher product chain ownership. If Atlas survives 24h, deliberator-tier is safe to follow. | Medium | Medium (active feature branches; document open stacks before cutover) |
| 5 | **Aiden** | First deliberator. CONCUR-LOCK authority on PRs — rollback path needs explicit `[REVIEW]` history recovery via gh comments scan. | High | Medium-high |
| 6 | **Max** | Second deliberator. CONCUR-LOCK + quality gate authority. Same recovery pattern as Aiden. | High | Medium-high |
| 7 | **Elliot** | Orchestrator. KEI-state recall is load-bearing for dispatch + merge-decisions. Migrate last so the rest of the fleet is empirically stable before Elliot's queue-management moves. | Highest | High (orchestrator state — Linear API checkpoint required) |

---

## 24h validation gate (per cutover)

After each agent's restart on the v2 path, the next agent in sequence does NOT cut over until ALL of:

1. **Liveness** — `systemctl --user is-active <agent>-agent.service` returns `active` for the full 24h window (no Restart=on-failure flap).
2. **Tool-call activity** — `SELECT COUNT(*) FROM public.tool_call_log WHERE callsign='<agent>' AND created_at > NOW() - INTERVAL '24 hours'` returns > 0 (proves the agent is actually doing work, not just up).
3. **No regressions** — zero new `[REVIEW:HOLD:<agent>]` or `[CONCUR-LOCK:<agent>]` on PRs blamed on the SessionManager path (search Sonar comments + recent `gh pr list` for HOLD posts citing supervisor v2).
4. **Claim cycle** — at least one `bd claim` → `bd close` cycle completed by the cut-over agent during the window. Proves the supervisor-v2 dispatch loop reaches the agent end-to-end.

If any of 1-4 fails: HOLD the next cutover, revert the failing agent to v1 (rollback section below), document the failure mode in this runbook before retrying.

---

## Per-agent rollback procedure

**Common steps** (all 6 existing agents):

```bash
# 1. Stop the v2-routed agent
systemctl --user stop <agent>-agent.service

# 2. Flip the per-agent supervisor flag back to v1 in agent_sessions table
psql "$DATABASE_URL" -c "UPDATE public.agent_sessions SET supervisor_version = 1 WHERE callsign = '<agent>'"

# 3. Re-pull IDENTITY.md (in case v2 cutover modified it)
cd /home/elliotbot/clawd/Agency_OS-<agent>
git checkout HEAD -- IDENTITY.md

# 4. Restart on v1 path
systemctl --user start <agent>-agent.service
systemctl --user is-active <agent>-agent.service   # → active
```

**Per-agent specifics:**

- **Nova rollback** — there's nothing to roll back. `rm -rf ~/clawd/Agency_OS-nova` + `bd update KEI-185 --notes 'nova spawn failed; reverted'`. Re-spawn after fix.
- **Scout / Orion rollback** — clean. Common steps cover everything; no per-agent state files to restore.
- **Atlas rollback** — IF cutover is mid-PR, document open stack on the worktree before rollback. Common-step #3 won't lose feature branches (they live in `.git`, not `IDENTITY.md`).
- **Aiden / Max rollback** — additionally re-sync `[REVIEW]` history: `gh search prs --comments-include '[REVIEW:HOLD:<aiden|max>]' --limit 100 > /tmp/<agent>-reviews.json` so review-state is recoverable for the supervisor's re-dispatch dedup.
- **Elliot rollback** — additionally checkpoint orchestrator state: snapshot `ceo_memory` + `cis_directive_metrics` rows touched in the cutover window so Linear-mirror + directive-counter don't drift.

---

## Acceptance (KEI-193)

- [x] S4 migration plan doc reflects sequential order (this doc, Cutover sequence table)
- [x] Each cutover has 24h validation gate before next (this doc, "24h validation gate (per cutover)" section)
- [x] Rollback paths documented per agent (this doc, "Per-agent rollback procedure" section)

Refinement-only; gates remain on KEI-185 (Nova spawn + v2 flip ON). KEI-191 (existing-6 migration) consumes this doc as its execution plan.

---

## Open questions for the orchestrator (Elliot)

1. **agent_sessions schema** — this doc references `supervisor_version` column. Is that landing in KEI-183 (Supervisor v2) or a separate migration? If separate, file as KEI-193 dep before KEI-191 starts.
2. **24h window override** — for the no-blocker case (clean cutover, agent healthy), is 24h hard or can it shrink to 6h? Worth a flag in the runbook.
3. **Nova spawn rollback** — KEI-185 description doesn't specify what "spawn failed" looks like operationally. Worth a brief failure-mode catalog in KEI-185 itself.

These are doc-clarifications, not gate items. Land them as follow-up edits to this runbook when KEI-185 ships.
