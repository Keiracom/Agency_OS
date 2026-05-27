# Dispatcher Wiring Inventory (Cutover Step 4.5)

**Owner:** Orion (dispatch); Aiden (architecture concur); Elliot (orchestrator hand-off).
**Anchor:** Dave directive 2026-05-27 cutover step 4.5 + bd Agency_OS-r9p3.
**Purpose:** topology map for where each of the **9 launch-blockers** is wired into the running system. Companion CI guard verifies the named modules / files / systemd units exist.

## Background

The 9 launch-blockers (Cat 21 levers 15+16+22+23+25+26+27+28+29) shipped as modules / migrations / docs on `main` 2026-05-27, but were code-on-main **without wiring**. End-to-end empirical validation of cutover stability (step 4) cannot run until every blocker fires in its production slot.

This inventory documents the wiring topology that PRs #1217 / #1218 / #1219 / #1220 / this PR collectively land.

## 9 Launch-Blocker Wiring Map

| # | Lever | Cutover-Blocker | Lib PR | Wiring slot | Wiring PR |
|---|---|---|---|---|---|
| 15 | `eff.cache_hit_rate_observability` | 9 | PR #1208 | systemd timer + Supabase view (NOT dispatcher) | (already wired in #1208) |
| 16 | `eff.cost_telemetry_to_ceo` | 1 | PR #1202 | systemd timer 23:55 AEST + ceo post (NOT dispatcher) | (already wired in #1202) |
| 22 | `eff.ephemeral_persistence_boundary` | 8 | PR #1206 | docs spec + design discipline (NOT runtime code) | (no wiring; docs spec only) |
| 23 | `eff.per_task_type_cost_telemetry` | 7 | PR #1209 | dispatcher pre-spawn hook (at-spawn) | PR #1220 (this batch) |
| 25 | `eff.context_window_budget_per_role` | 3 | PR #1210 | dispatcher pre-spawn hook | PR #1219 (this batch) |
| 26 | `eff.idempotency_keys_task_queue` | 5 | PR #1204 | dispatcher pre-spawn hook (BEFORE route or after route, BEFORE spawn) | PR #1217 (this batch) |
| 27 | `eff.spawn_attribution_telemetry` | 6 | PR #1207 | dispatcher at-spawn hook | PR #1220 (this batch) |
| 28 | `eff.budget_ceiling_policy` | 2 | PR #1203 | dispatcher pre-spawn hook | PR #1218 (this batch) |
| 29 | `eff.cache_write_ttl_5min_default` | 4 | PR #1205 | CI guard `scripts/ci/check_no_1h_cache_ttl.sh` (NOT dispatcher) | (already wired in #1205) |

## Dispatcher Hook Lifecycle (PRs #1217-#1220)

```
┌────────────────────────────────────────────────────────────────────────┐
│ dispatcher_main loop (one envelope per iteration)                       │
│                                                                          │
│   1. inbox claim (atomic move to processing/)                           │
│                       ↓                                                  │
│   2. _envelope_route.route_envelope()                                   │
│                       ↓ (SPAWN | RESUME)                                │
│   3. [PR #1217]  _pre_spawn_gates.evaluate()                            │
│                  └─ IdempotencyGate.check_and_claim()                   │
│                       ↓ (PROCEED)                                        │
│   4. [PR #1218]  _budget_gate.evaluate()                                │
│                  └─ BudgetCeilingGate.check_budget()                    │
│                       ↓ (PROCEED)                                        │
│   5. [PR #1219]  _context_window_gate.evaluate()                        │
│                  └─ check_context_budget()                              │
│                       ↓ (PROCEED)                                        │
│   6. [PR #1220]  _spawn_attribution.emit()                              │
│                  └─ log_spawn_attribution() → JSONL                     │
│                       ↓                                                  │
│   7. _spawn.handle_envelope()                                           │
│                  └─ compose_initial_prompt + subprocess.Popen(claude)   │
└────────────────────────────────────────────────────────────────────────┘
```

## Non-Dispatcher Wiring Slots (4 / 9)

Four launch-blockers wire at architectural boundaries other than `dispatcher_main`:

### Lever 16 — Daily cost rollup (PR #1202)
**Slot:** systemd timer `keiracom-cost-rollup.timer` fires 23:55 AEST → runs `scripts/agency_cost_rollup.py` → posts `tg -c ceo` message.
**Why not dispatcher:** the rollup aggregates ALL costs (Anthropic + OpenAI + Vultr) at end of day. Dispatcher emits per-spawn attribution; rollup correlates. Different lifecycle.

### Lever 15 — Cache hit-rate observability (PR #1208)
**Slot:** systemd timer `cache_hit_rate_ingest.timer` (13:50 UTC) + `cache_hit_rate_alert.timer` (13:53 UTC) + Supabase view `keiracom_cache_hit_rates_v1`.
**Why not dispatcher:** hit-rates compute from session JSONLs after spawns complete. Dispatcher doesn't see cache headers; Anthropic adds them to responses. Read-only observability layer.

### Lever 22 — Ephemeral persistence boundary (PR #1206)
**Slot:** `docs/architecture/ephemeral_persistence_boundary.md` (180 lines: §1 SURVIVES + §2 DIES + §3 12-row decision table + §4 anti-patterns + §5 cutover-gate mapping + §6 impl footprint + §7 Phase 2 open questions).
**Why not runtime code:** the boundary is a design discipline — what data CAN survive a spawn (Postgres, Hindsight, durable state) vs what DIES (in-memory dicts, tmux buffers, local files). Future engineers wire to the SURVIVES list; the dispatcher inherently respects DIES by spawning fresh per task.

### Lever 29 — Cache write TTL 5-min default (PR #1205)
**Slot:** CI guard `scripts/ci/check_no_1h_cache_ttl.sh` rejects PRs introducing `{"type": "1h"}` cache controls; codebase canonical is `{"type": "ephemeral"}` = 5-min per Anthropic spec.
**Why not dispatcher:** the TTL is encoded at Anthropic prompt-cache configuration sites in skill / agent code. CI guard catches regressions at PR time.

## Rollout Phases

All 5 dispatcher-side gate kwargs default to disabled / None for **Phase 1** (zero behavioural change). **Phase 2** rollout PR (follow-up) sets them at the dispatcher entry-point in fleet supervisor / per-callsign systemd unit:

```python
# Phase 2 example — fleet_supervisor or per-callsign launcher
from scripts.dispatcher.dispatcher_main import main
from src.dispatcher.idempotency import IdempotencyGate
from src.dispatcher.valkey_pool import get_valkey_client
from src.relay.budget_ceiling import BudgetCeilingGate

main(
    [...],
    db_factory=lambda: psycopg.connect(DSN).cursor(),
    idempotency_gate=IdempotencyGate(valkey_client=get_valkey_client()),
    budget_gate=BudgetCeilingGate(db=cursor, daily_budget_aud=25.0),
    context_window_enabled=True,
    context_window_summariser=tiktoken_backed_summariser,
    attribution_enabled=True,
    attribution_model="claude-sonnet-4-6",
)
```

## CI Verification

`scripts/ci/check_dispatcher_wiring_inventory.sh` (this PR) fails if any documented wiring point is missing:

- Each PR #1217-#1220 module under `scripts/dispatcher/`
- Each PR #1208 systemd unit under `systemd/`
- PR #1202 `scripts/agency_cost_rollup.py`
- PR #1206 docs spec
- PR #1205 CI guard

This document is the **single source of truth** for cutover-step-4.5 wiring topology. Update when a new launch-blocker lands or a wiring slot moves.

## Anchors

- **bd:** Agency_OS-r9p3 (cutover step 4.5)
- **Cat 21 §0 BOUNDED-SPAWN HARDEST** anchors all 9 levers
- **Composes with:** PRs #1217 (idempotency) + #1218 (budget) + #1219 (context-window) + #1220 (attribution + per-task-type) + this PR #5 (inventory + CI guard)
- **Gates:** Phase 1 step 5 retire-persistent-tmux per Aiden CONCUR condition (a)
