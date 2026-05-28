# KEI-213 Dispatcher Wiring Inventory (Cutover Step 4.5)

**Owner:** Orion (build); Aiden + Viktor (architecture concur); Elliot (orchestrator hand-off); Dave (ratified 2026-05-27).
**Anchor:** Dave directive 2026-05-27 ratifying Aiden + Viktor dual-concur — **KEI-213 is the canonical dispatcher**.
**Purpose:** topology map for where each of the **9 launch-blockers** is wired into the canonical KEI-213 dispatcher (`src/dispatcher/main.py` running at port 4001).

## Ratified canonical-dispatcher decision (2026-05-27)

**Canonical:** KEI-213 — `src/dispatcher/main.py` + `src/dispatcher/interceptor_proxy.py` (FastAPI service at port 4001).
**Deprecated:** PR #1188 — `scripts/dispatcher/dispatcher_main.py` (claim-loop binary). Code stays on main for traceability but **not wired into production**.

PRs #1217 / #1218 / #1219 / #1220 / #1221 wired the deprecated binary. KEI-213 mirror PRs (A/B/C/D/E) reproduce the same wiring topology against the canonical dispatcher per Dave + Aiden + Viktor ratify.

## 9 Launch-Blocker Wiring Map (KEI-213)

| # | Lever | Cutover-Blocker | Lib PR | Wiring slot | Wiring PR |
|---|---|---|---|---|---|
| 15 | `eff.cache_hit_rate_observability` | 9 | PR #1208 | systemd timer + Supabase view (NOT dispatcher) | (already wired in #1208) |
| 16 | `eff.cost_telemetry_to_ceo` | 1 | PR #1202 | systemd timer 23:55 AEST (NOT dispatcher) | (already wired in #1202) |
| 22 | `eff.ephemeral_persistence_boundary` | 8 | PR #1206 | docs spec + design discipline (NOT runtime code) | (no wiring; docs spec only) |
| 23 | `eff.per_task_type_cost_telemetry` | 7 | PR #1209 | KEI-213 `/dispatcher/spawn` at-spawn (task_type taxonomy) | PR D (#1225) |
| 25 | `eff.context_window_budget_per_role` | 3 | PR #1210 | KEI-213 `interceptor_proxy.intercept_request` pre-LLM-call | PR C (#1224) |
| 26 | `eff.idempotency_keys_task_queue` | 5 | PR #1204 | KEI-213 `/dispatcher/spawn` pre-spawn | PR A (#1222) |
| 27 | `eff.spawn_attribution_telemetry` | 6 | PR #1207 | KEI-213 `/dispatcher/spawn` post-register | PR D (#1225) |
| 28 | `eff.budget_ceiling_policy` | 2 | PR #1203 | KEI-213 `/dispatcher/spawn` pre-spawn | PR B (#1223) |
| 29 | `eff.cache_write_ttl_5min_default` | 4 | PR #1205 | CI guard `scripts/ci/check_no_1h_cache_ttl.sh` (NOT dispatcher) | (already wired in #1205) |

**5 of 9 wire into the canonical KEI-213 dispatcher.**
**4 of 9 wire at other architectural boundaries** (systemd timers / CI guard / docs spec).

## KEI-213 dispatcher hook topology

```
HTTP POST /dispatcher/spawn (src/dispatcher/main.py)
    │
    ├── Backend validation
    │
    ├── [PR A] Idempotency gate (Cat 21 lever 26)
    │       └─ IdempotencyGate.check_and_claim()
    │          ├─ SPAWN_OK     → continue
    │          └─ DROP_DUPLICATE → HTTP 200 {spawned: false, decision: "drop_duplicate"}
    │
    ├── [PR B] Budget ceiling gate (Cat 21 lever 28)
    │       └─ BudgetCeilingGate.check_budget()
    │          ├─ SPAWN_OK / OVERAGE_LOG_AND_SPAWN / DAVE_BYPASS / FORCE_OVERRIDE → continue
    │          └─ QUEUE_NEXT_DAY / DROP_WITH_LOG → HTTP 200 {spawned: false, decision: ...}
    │
    ├── SessionManager.spawn(**spawn_kwargs)
    ├── _register_session(...)
    │
    ├── [PR D] Spawn attribution emit (Cat 21 levers 27 + 23)
    │       └─ log_spawn_attribution() → DEFAULT_ATTRIBUTION_LOG JSONL
    │
    └── HTTP 200 with handle


HTTP POST /interceptor/forward (src/dispatcher/interceptor_proxy.py)
    │
    ├── governance check
    ├── spend budget check  (per-tenant monthly Valkey)
    ├── rate limit check    (per-tenant 60s window Valkey)
    │
    ├── [PR C] Context-window budget gate (Cat 21 lever 25)
    │       └─ check_context_budget(role, context)
    │          ├─ SPAWN_OK / SUMMARISED → continue
    │          └─ REJECTED → InterceptorDecision(allowed=False, 413)
    │
    ├── forward to LiteLLM
    └── log allow event
```

## Non-dispatcher wiring slots (unchanged from PR #1221 inventory)

### Lever 16 — Daily cost rollup (PR #1202)
**Slot:** systemd timer `keiracom-cost-rollup.timer` fires 23:55 AEST → runs `scripts/agency_cost_rollup.py` → posts `tg -c ceo` message.

### Lever 15 — Cache hit-rate observability (PR #1208)
**Slot:** systemd timer `cache_hit_rate_ingest.timer` (13:50 UTC) + `cache_hit_rate_alert.timer` (13:53 UTC) + Supabase view `keiracom_cache_hit_rates_v1`.

### Lever 22 — Ephemeral persistence boundary (PR #1206)
**Slot:** `docs/architecture/ephemeral_persistence_boundary.md` (180-line design discipline spec).

### Lever 29 — Cache write TTL 5-min default (PR #1205)
**Slot:** CI guard `scripts/ci/check_no_1h_cache_ttl.sh` rejects PRs introducing `{"type": "1h"}`.

## Phase 1 vs Phase 2 rollout

**Phase 1 (PRs A/B/C/D):** All 4 dispatcher-side toggles default to disabled (zero behavioural change):
- `main._idempotency_gate = None`
- `main._budget_gate = None`
- `interceptor_proxy.context_window_enabled = False` (env-driven)
- `main.attribution_enabled = False` (env-driven)

**Phase 2 (follow-up config PR):** Production rollout at dispatcher startup site:

```python
# src/dispatcher/main.py startup OR a separate config module
from src.dispatcher.idempotency import IdempotencyGate
from src.dispatcher.valkey_pool import get_valkey_client
from src.relay.budget_ceiling import BudgetCeilingGate
import src.dispatcher.main as main_mod
import src.dispatcher.interceptor_proxy as interceptor_mod

main_mod._set_idempotency_gate(IdempotencyGate(valkey_client=get_valkey_client()))
main_mod._set_budget_gate(BudgetCeilingGate(db=cursor, daily_budget_aud=25.0))
interceptor_mod.context_window_enabled = True  # or via DISPATCHER_CONTEXT_WINDOW_ENABLED=1 env
main_mod.attribution_enabled = True            # or via DISPATCHER_ATTRIBUTION_ENABLED=1 env
```

## CI verification

`scripts/ci/check_dispatcher_wiring_inventory_kei213.sh` (this PR) verifies the lib modules + systemd units + docs spec referenced in this inventory all exist.

This document is the **single source of truth** for KEI-213 wiring topology. Update when a new launch-blocker lands or a wiring slot moves.

## Anchors

- **bd:** Agency_OS-r9p3 (cutover step 4.5)
- **Cat 21 §0 BOUNDED-SPAWN HARDEST** anchors all 9 levers
- **GOV-12** (gates as code, not comments) — CI guard runtime enforcement
- **Composes with:** PRs A-D (KEI-213 wiring batch) + all 9 lib PRs
- **Supersedes (operational scope):** `dispatcher_wiring_inventory.md` (which targets PR #1188 deprecated binary)
- **Gates:** Phase 1 step 5 retire-persistent-tmux per Aiden + Viktor CONCUR
