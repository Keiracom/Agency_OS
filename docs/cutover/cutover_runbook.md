# Cutover Day Runbook — Ephemeral Agent Mode

**Author:** Atlas (Elliot dispatch, 2026-05-28)
**Status:** OPERATOR RUNBOOK — execute on the day Phase 1 (Dave personal cutover) fires
**Scope:** Phase 1 of `ceo:cutover_plan_v1` — flip the fleet from the persistent tmux/keepalive substrate to workflow-driven **ephemeral spawns**, retire the obsolete tmux layer, reactivate the fleet supervisor.
**Companions:** `docs/governance/cutover_requirements_v1.md` (the gate), `docs/runbooks/s4_supervisor_v2_cutover_order.md` (per-agent order + rollback), `docs/runbooks/ephemeral_agent_decommission_tracker.md` (teardown commands + per-item rollback), `docs/architecture/ephemeral_persistence_boundary.md` (what survives a spawn).

> **Golden rule:** every step has a verify command. A step is not "done" until its verify prints `OK` / `active` / the expected row count. No step proceeds on assumption. Elliot dispatches; named agents execute; Elliot runs host-side `systemctl` (host infra is orchestrator-allowed).

---

## §0 Canonical sources (queried at authoring — cross-check before executing)

This runbook is derived from canonical `ceo_memory`, not from memory or inference. Re-query before the cutover day in case state moved.

**`ceo:cutover_plan_v1`** (ratified 2026-05-27T11:25Z — Dave verbatim sign-off; concur Elliot + Viktor + Aiden):
- `phase_1_dave_cutover.steps`: `empirical_end_to_end_test` → `memory_layer_cutover_finish` → `retire_persistent_tmux_and_watchers_plus_fleet_supervisor_reactivation`
- `dual_concur_ratified_2026_05_27_14Z`: `tmux_kill_for_model_flip: now_per_viktor_lean`; `fleet_supervisor: reactivate_step_5_after_empirical_GREEN`; `dispatcher_canonical: KEI-213_running_service_port_4001`; `tei_sidecar: defer_diagnose_post_empirical_test`; `three_repo_separation: post_phase_1_cutover_validation`
- `empirical_test_additions_2026_05_27`: pre-test migrations applied (spawn_attribution + completion_status + cache_hit_rates + paused_tasks = DONE); success criteria = recall query `"What did I just build and why?"` returns without context-injection **AND** per-spawn cost-attribution JSONL shows **three distinct spawn entries** (chat agent + worker + two deliberators)
- `full_retrieval_tier_ratify_2026_05_27_22Z`: **all 6 retrieval waves (15 KEIs) gate cutover** (Dave overrode Aiden's tier-1-only rec to all-tiers); timeline 3–5 weeks; existing 5-step Phase 1 sequenced WITH the waves

**`ceo:comm_architecture`** (CANONICAL): Slack relay is ALIVE, restricted to elliot-only outbound (2026-05-19); inter-agent path is NATS (2026-05-18). Restriction ≠ decommission — the relay stays up through cutover; only the **inbox-watcher + send-keys relay** (the tmux fan-out) is retired here.

> **Open flag (GOV-9):** the dispatch asked for a "9-item" pre-cutover checklist. No standalone 9-item artefact exists in `ceo_memory` or `docs/`. §1 below synthesises 9 concrete, verifiable GREEN gates from `ceo:cutover_plan_v1` + `cutover_requirements_v1.md`. **Elliot to confirm this mapping matches his intent before go.**

---

## §1 Pre-cutover checklist — all 9 must be GREEN before T+0

Run the morning of. If any item is not GREEN, **do not start the sequence** — the cutover is NO-GO.

| # | Gate item | Source | Verify command | GREEN = |
|---|-----------|--------|----------------|---------|
| 1 | All 6 retrieval waves merged | `cutover_plan_v1.full_retrieval_tier_ratify` | `bd list --status closed --json \| jq '[.[] \| select(.labels[]? == "cutover-gating")] \| length'` | 15 |
| 2 | Pre-cutover migrations applied | `cutover_plan_v1.empirical_test_additions` | `psql "$DATABASE_URL" -c "SELECT to_regclass('public.keiracom_spawn_attribution'), to_regclass('public.keiracom_cache_hit_rates'), to_regclass('public.keiracom_paused_tasks')"` | 3 non-NULL |
| 3 | Ephemeral dispatcher live | `dispatcher_canonical: KEI-213 port 4001` | `curl -fsS http://127.0.0.1:4001/health && systemctl --user is-active keiracom-dispatcher@elliot.service` | `active` |
| 4 | Bounded-spawn kill firing | `cutover_requirements_v1` AGENT-SIDE | `pytest tests/dispatcher/test_bounded_spawn_enforcer.py -q` | all pass |
| 5 | Per-spawn cost telemetry + attribution | `cutover_requirements_v1` COST TELEMETRY | `psql "$DATABASE_URL" -c "SELECT count(*) FROM public.keiracom_spawn_attribution WHERE created_at > NOW() - INTERVAL '24 hours'"` | > 0 |
| 6 | Budget ceiling enforcement firing | `cutover_requirements_v1` COST TELEMETRY | `pytest tests/relay/test_budget_ceiling.py -q` | all pass |
| 7 | Go sidecar denying cross-domain calls | `cutover_requirements_v1` GOVERNANCE | `curl -s -o /dev/null -w "%{http_code}" -X POST $SIDECAR_URL/authorize -d '{"role":"scout","tool":"telnyx.send_sms"}'` | `403` |
| 8 | Memory-layer cutover complete | `cutover_plan_v1.phase_1 step 2` | `python scripts/retrieval_smoke.py --cold-start` → recall returns atoms with citations | non-empty + cited |
| 9 | Empirical end-to-end test GREEN | `cutover_plan_v1.phase_1 step 1` | one real PR through ephemeral dispatcher; then `"What did I just build and why?"` recall + `jq 'length' <cost-attribution.jsonl>` for that workflow | recall answers; **3** spawn entries |

**Item 9 is the keystone.** It is itself Phase-1 step 1 and unlocks the teardown sequence (§2). If item 9 is not GREEN, every later step is NO-GO regardless of items 1–8.

**Pre-flight smoke set** (run immediately before declaring go — `cutover_requirements_v1` PRE-FLIGHT): bounded ephemeral spawn end-to-end, migration spike (5 real production tasks), task-decomposition quality, adversarial-input against fresh context, keepalive respawn. All clean = go.

---

## §2 Cutover sequence — order, timestamps, pauses

Two phases on the timeline:

**Phase A — per-agent supervisor-v2 flip** (the multi-day fleet migration). Order is fixed by `s4_supervisor_v2_cutover_order.md` — lowest blast radius first, orchestrator last:

```
Nova → Scout → Orion → Atlas → Aiden → Max → Elliot
 (spawn-test)            (canary)        (deliberators)  (orchestrator, last)
```

**The pause between each agent is the 24h validation gate** (§3). No parallel. Cost: 6 × 24h ≈ 6 days; blast radius stays bounded to one agent.

**Per-agent cutover-day micro-sequence** (timestamps relative to that agent's T+0):

| T | Step | System acted on | Owner |
|---|------|-----------------|-------|
| T+0 | Confirm prior agent's 24h gate passed (or §1 GREEN for the first agent, Nova) | — | Elliot |
| T+5 | Announce cutover window for `<agent>` in #ceo | — | Elliot |
| T+10 | Stop v1 substrate units for `<agent>` | `<agent>-agent.service`, `<agent>-inbox-watcher.service`, `<agent>-nats-*-bridge.service` | Elliot (host) |
| T+15 | Flip supervisor flag | `UPDATE public.agent_sessions SET supervisor_version = 2 WHERE callsign = '<agent>'` | Elliot (host) |
| T+18 | Start `<agent>` on the v2 ephemeral path (dispatcher spawns on demand) | `keiracom-dispatcher@<agent>.service` | Elliot (host) |
| T+22 | First-spawn validation (liveness + one cost-attribution row) | — | devops-6 |
| T+25 | Disable the now-obsolete tmux units for `<agent>` (decommission tracker §3.1) | same 3 units, `disable --now` | Elliot (host) |
| T+30 | **Begin 24h soak** (the pause) → §3 gate → next agent | — | all |

**Phase B — shared teardown + fleet supervisor reactivation** (once all 7 agents are flipped + validated; runs ONCE):

| T | Step | System acted on | Owner |
|---|------|-----------------|-------|
| B+0 | Disable Elliot's tmux-pane liveness checker (tracker §3.2) | `elliot-check-agents.timer` + `.service` | Elliot (host) |
| B+10 | Archive obsolete tmux scripts (tracker §3.3) | `scripts/agent_keepalive.sh`, `fleet_supervisor.py`, `relay_watcher.sh`, … → `scripts/archive/` | Atlas (PR) |
| B+30 | Reactivate fleet supervisor on the v2 path (`cutover_plan_v1`: `reactivate_step_5_after_empirical_GREEN`) | fleet supervisor (v2) | Elliot (host) + devops-6 |
| B+45 | Write `ceo:tmux_layer_retired_<date>` with verbatim verification output (tracker §7.8) | `ceo_memory` | Elliot |

> The 15-min spacing in Phase B is the **pause between each** — each step's verify (§3) must print OK before the next starts. Do not batch.

---

## §3 Validation at each step — exact verify commands

**Per-agent (Phase A) 24h validation gate** — ALL four must hold for the full window before the next agent cuts over (`s4_supervisor_v2_cutover_order.md`):

```bash
A="<agent>"
# 1. Liveness — active for the full 24h, no Restart=on-failure flap
systemctl --user is-active keiracom-dispatcher@$A.service        # → active

# 2. Tool-call activity — the agent is doing work, not just up
psql "$DATABASE_URL" -c \
  "SELECT count(*) FROM public.tool_call_log WHERE callsign='$A' AND created_at > NOW() - INTERVAL '24 hours'"  # → > 0

# 3. No regressions — zero HOLD/CONCUR-LOCK blamed on the v2 path
gh pr list --search "[REVIEW:HOLD:$A] supervisor v2" --state all | head   # → empty

# 4. Claim cycle — one bd claim→close completed by the agent in-window
bd list --assignee="$A" --status closed --since 24h | head        # → ≥ 1 row
```

**Per-step verify (Phase A micro-sequence):**

| Step | Verify command | Pass |
|------|----------------|------|
| T+10 stop units | `systemctl --user is-active $A-agent.service $A-inbox-watcher.service 2>&1 \| grep -qv active && echo OK` | `OK` |
| T+15 flip flag | `psql "$DATABASE_URL" -tAc "SELECT supervisor_version FROM public.agent_sessions WHERE callsign='$A'"` | `2` |
| T+18 start v2 | `systemctl --user is-active keiracom-dispatcher@$A.service` | `active` |
| T+22 first spawn | `psql "$DATABASE_URL" -tAc "SELECT count(*) FROM public.keiracom_spawn_attribution WHERE callsign='$A' AND created_at > NOW()-INTERVAL '10 min'"` | `> 0` |
| T+25 disable tmux units | `systemctl --user is-enabled $A-agent.service 2>&1 \| grep -q "disabled\|not-found" && echo OK` | `OK` |

**Phase B verify:**

```bash
# B+0  elliot-check-agents gone
systemctl --user is-enabled elliot-check-agents.timer 2>&1 | grep -q "disabled\|not-found" && echo OK || echo FAIL
# B+10 no tmux-coupled scripts on the runtime path
git grep -l "tmux send-keys\|tmux capture-pane\|tmux new-session" scripts/ | grep -v "scripts/archive/" && echo FAIL || echo OK
# B+30 fleet supervisor up on v2
systemctl --user is-active keiracom-fleet-supervisor.service   # → active
# B+45 canonical key written
psql "$DATABASE_URL" -tAc "SELECT 1 FROM public.ceo_memory WHERE key LIKE 'ceo:tmux_layer_retired_%'"  # → 1
```

---

## §4 Failed-step definition + response

A step has **FAILED** when its §3 verify does not print the pass value within the step's window (or prints `FAIL`). Response is tiered by where the failure lands:

| Failure | What it looks like | Response |
|---------|--------------------|----------|
| **§1 gate item RED** (pre-cutover) | Any of the 9 items not GREEN | **NO-GO.** Do not start. Elliot files a blocker KEI for the red item, dispatches the fix, reschedules. No partial cutover. |
| **Empirical test (item 9) fails** | Recall returns empty / un-cited, OR cost-attribution JSONL shows 1–2 spawn entries (attribution chain collapsing spawns) | **HARD STOP.** Per `cutover_plan_v1`: defer + diagnose. Do not retire tmux. Escalate to Elliot → #ceo. |
| **Phase A step fails mid-agent** (T+10…T+25) | Unit won't stop, flag won't flip, dispatcher won't start, no first-spawn row | **PAUSE that agent. ROLLBACK that agent only** (§ rollback below). Document the failure mode in `s4_supervisor_v2_cutover_order.md` before retry. Other agents already flipped are unaffected (sequential = bounded blast radius). |
| **24h soak gate fails** | Any of liveness / tool-activity / regressions / claim-cycle fails in-window | **HOLD the next cutover. ROLLBACK the failing agent to v1.** Do not advance the sequence until the failure mode is understood + documented. |
| **Phase B step fails** | Script grep shows runtime tmux refs, fleet supervisor won't start | **PAUSE Phase B.** `git revert` the offending change (scripts/docs) or `systemctl enable --now` the unit just disabled. Re-attempt after fix. Phase B is reversible per-item. |

**Per-agent rollback** (`s4_supervisor_v2_cutover_order.md` common steps):

```bash
A="<agent>"
systemctl --user stop keiracom-dispatcher@$A.service
psql "$DATABASE_URL" -c "UPDATE public.agent_sessions SET supervisor_version = 1 WHERE callsign = '$A'"
cd /home/elliotbot/clawd/Agency_OS-$A && git checkout HEAD -- IDENTITY.md
# Re-enable the v1 units disabled at T+25 (decommission tracker §6 rollback)
systemctl --user enable --now $A-agent.service $A-inbox-watcher.service $A-nats-dispatch-bridge.service
systemctl --user is-active $A-agent.service   # → active
```

Per-agent specifics: **Nova** — nothing to roll back (`rm -rf ~/clawd/Agency_OS-nova`, re-spawn after fix). **Atlas** — if mid-PR, document open feature-branch stack before rollback (branches live in `.git`, survive the IDENTITY checkout). **Aiden/Max** — additionally re-sync `[REVIEW]` history via `gh search prs --comments-include '[REVIEW:HOLD:<agent>]'` so dedup state is recoverable. **Elliot** — additionally checkpoint `ceo_memory` + `cis_directive_metrics` rows so directive-counter + Linear mirror don't drift.

**Escalation:** any HARD STOP or a soak-gate failure that blocks the sequence → Elliot posts to **#ceo immediately** (blocker-escalation R13: #ceo first, not after peer discussion). Elliot is the only Dave-facing channel; clones report via outbox to Elliot.

---

## §5 Who runs each step

| Role | Responsibility on cutover day |
|------|-------------------------------|
| **Dave** | Owns the go/no-go decision. Receives #ceo updates from Elliot. Authorises any deferral of a red gate item. |
| **Elliot** (orchestrator) | Dispatches every step; runs host-side `systemctl`/`psql` for the flip + teardown (host infra is orchestrator-allowed); announces each window in #ceo; writes the final `ceo:tmux_layer_retired_<date>` key. Does NOT author the empirical-test code (role-lock). |
| **Atlas / Orion** (engineer-tier) | Build the empirical-test PR (§1 item 9). Atlas authors the Phase B script-archive PR. Atlas is the Phase-A canary (position 4). |
| **Aiden / Max** (deliberators) | Review + 2-of-3 concur the empirical-test PR and the script-archive PR. Cut over last-but-one (positions 5–6) so the bench is validated before their high-state recall moves. |
| **devops-6** | Runs the §3 verify commands (liveness, first-spawn row, fleet-supervisor health). Reports pass/fail to Elliot. |
| **Each agent** | During its 24h soak, completes ≥1 real `bd claim → bd close` cycle to prove the v2 dispatch loop reaches it end-to-end. |

---

## §6 Post-cutover verification — confirm ephemeral mode is correct

"Running ephemeral mode correctly" = **durable state survives a spawn, per-spawn context dies, and the dispatcher spawns/kills cleanly.** Anchor: `docs/architecture/ephemeral_persistence_boundary.md`.

**A. Durable state SURVIVES (must all pass):**

```bash
# Temporal workflow state intact across respawn
temporal workflow list --query 'ExecutionStatus="Running"' | head           # in-flight graphs present

# Hindsight semantic memory recall works from a COLD spawn (no context injection)
python scripts/retrieval_smoke.py --cold-start --query "What did I just build and why?"   # → cited atoms

# ceo_memory canonical keys readable
psql "$DATABASE_URL" -tAc "SELECT count(*) FROM public.ceo_memory WHERE key LIKE 'ceo:%'"  # > 0

# IDENTITY template loads from file, not session
test -f docs/runbooks/elliot-identity.md && echo OK
```

**B. Ephemeral state DIES (no carryover):**

```bash
# Keepalive respawn carries NO prior-session context — fresh context every spawn
# (cutover_requirements_v1 PRE-FLIGHT "keepalive respawn test")
# Spawn twice; confirm spawn 2 does not reference spawn 1's in-session scratch.
python scripts/ephemeral_respawn_check.py --callsign elliot   # → "fresh context confirmed"
```

**C. Dispatcher lifecycle clean:**

```bash
# Bounded spawn: each spawn one task, killed at token/time ceiling
psql "$DATABASE_URL" -c \
  "SELECT decision, count(*) FROM public.keiracom_spawn_attribution WHERE created_at > NOW()-INTERVAL '24 hours' GROUP BY decision"
# Cost attribution: a multi-agent task shows DISTINCT spawn entries (not collapsed)
# cutover_plan_v1 success criterion — expect ≥3 for chat+worker+2 deliberators
```

**D. Obsolete layer gone:**

```bash
# No tmux units active for any callsign
for A in elliot aiden max atlas orion scout nova; do
  systemctl --user is-active $A-agent.service 2>&1 | grep -qv active || echo "STILL UP: $A"
done   # → no output
# No runtime-path tmux references (decommission tracker §7.7)
git grep -l "tmux send-keys\|tmux capture-pane\|tmux new-session" scripts/ docs/runbooks/ | grep -v "scripts/archive/" && echo FAIL || echo OK
```

**Cutover is COMPLETE when:** §6 A–D all pass, the decommission tracker §7 sign-off criteria are met, and `ceo:tmux_layer_retired_<date>` carries the verbatim verification output.

---

## §7 Notes + deferred items

- **Deferred (do NOT block cutover)** — per `cutover_plan_v1.deferred_decisions` + `dual_concur`: TEI sidecar (defer-diagnose post-empirical-test), tier caps + UX (Phase 2 launch, not Dave personal cutover), three-repo separation (post-Phase-1-validation).
- **Phase 2 (before customer two, NOT this runbook):** `pulumi_tenant_create_workflow_e2e`, `supabase_keys_audit_both_auth_surfaces`.
- **9-item gate (§1)** is synthesised from the canonical plan, not a pre-existing artefact — Elliot to confirm the mapping/count before go (GOV-9 flag, §0).
- Re-query `ceo:cutover_plan_v1` on the morning of: ratified state can move, and this runbook is a snapshot of 2026-05-28.
