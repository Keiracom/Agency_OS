# fleet_session_mgmt — Scoping Doc

**Author:** orion (clone)
**Date:** 2026-06-02
**Triggered by:** Elliot dispatch — scope the Phase-0 gate `fleet_session_mgmt`.
**Status:** SCOPING ONLY — no build, no execution. Awaiting Elliot+Dave direction on Option A / B / C below.

---

## §1 What I found vs what the dispatch said

| Dispatch claim | Empirical reality |
|---|---|
| "KEI-191, Phase-0, status=backlog" | KEI-191 status = **`dismissed`** in both `bd show` and `public.tasks` (phase 0.0). |
| "migrating 6 agents to a managed session model" | KEI-191's one-by-one migration was **superseded** by Max's session retirement plan (`docs/cutover/session_retirement_plan.md`, PR #1254, 2026-05-28). The new target is **persistent tmux → event-triggered ephemeral spawning** — not migrating onto SessionManager calls one agent at a time, but **retiring** the persistent-tmux substrate entirely. |
| "gate is in backlog" | `gate_roadmap.fleet_session_mgmt.status = 'built'`, `built_by_callsign = NULL`, `proof_run_id = NULL`. Gate notes: *"SessionManager + v2 + Nova spawn Done; full 6-agent migration not finished."* — notes refer to the dismissed KEI-191 scope. |

**Net:** the gate as currently labelled targets a dismissed KEI. Before scoping execution work, the gate definition needs to be aligned with what's actually shipped + what's actually pending.

---

## §2 Current state inventory (read-only verifications)

### 2.1 What is SHIPPED + LIVE

| Component | Evidence |
|---|---|
| `SessionManager` abstraction (KEI-184) | `src/dispatcher/session_manager.py` (157 lines) — `tmux` + `container` backends; PR #1004 merged. |
| `tmux_lifecycle` + `container_lifecycle` modules | `src/dispatcher/tmux_lifecycle.py` + `container_lifecycle.py` — present. |
| Nova spawn via SessionManager (KEI-185) | PR #1006 merged. |
| Dispatcher service (KEI-213) | `dispatcher.service` ACTIVE since 2026-06-02 08:35 UTC; `/dispatcher/health` returns `{"status":"ok"}` with all 5 components green (auth_minter / interceptor_proxy / spend_tracker / watchdog / reaper). |
| 5 dispatcher-wired cutover-blocker gates | PRs #1222 (idempotency), #1223 (budget ceiling), #1224 (context-window), #1225 (spawn attribution) — all MERGED. |
| Ephemeral spawn contract | `ceo:ephemeral_spawn_contract_ratified` (2026-05-28). 4-layer: hydrate → Hindsight recall → Valkey spend gate → dispatcher compose. |
| Listener architecture post-cutover | `ceo:listener_architecture_post_cutover_ratified` (2026-05-28). Haiku per-#ceo-message via Socket Mode. |
| Cutover docs | `docs/cutover/session_retirement_plan.md` (Max, 357 lines) + `docs/cutover/cutover_runbook.md` (Atlas, 236 lines) + `docs/runbooks/s4_supervisor_v2_cutover_order.md` + `docs/runbooks/ephemeral_agent_decommission_tracker.md` + `docs/architecture/ephemeral_persistence_boundary.md` — all present. |

### 2.2 What is CONFIGURED but NOT EXECUTING

| Item | Reality |
|---|---|
| `FLEET_SUPERVISOR_V2_ENABLED=1` in `~/.config/agency-os/.env` | Flag is set. |
| `AGENT_ROUTING_{ELLIOT,AIDEN,MAX,ORION,SCOUT,NOVA,ATLAS}=v2` | All 7 callsigns flagged for v2 routing. |
| `src/fleet/supervisor_v2.py` Python module | **DOES NOT EXIST.** `scripts/fleet_supervisor.py:1367` does `from src.fleet import supervisor_v2` inside a `try/except ImportError` that silently falls back to v1 with a WARNING log. |
| `fleet-supervisor.timer` (5-minute trigger) | **INACTIVE.** Per `systemctl --user status` — `Active: inactive (dead)`. Even the v1 path is not firing on a cadence. |
| Persistent-tmux substrate (`{callsign}-agent.service` × 7) | **STILL ACTIVE** for all 7 callsigns. The retirement plan's per-callsign Step 1–4 sequence has not been executed. |

**Implication:** the cutover is in a *configured-but-not-executing* state. Flags say v2; the module backing v2 doesn't exist; the supervisor isn't running; the substrate the cutover is meant to retire is still live. Anyone reading the env flags would assume the cutover happened. It hasn't.

### 2.3 What is OPEN per the retirement plan's §6

| # | Prerequisite | Current state |
|---|---|---|
| P1 | All 5 dispatcher-wired cutover-blocker gates passing in CI | ✅ All 4 PRs merged + dispatcher health green. |
| P2 | `dispatcher.service` running and healthy | ✅ Active since 2026-06-02 08:35 UTC, all components ok. |
| P3 | Fleet supervisor v2 flag implemented and tested | ⚠ Flag exists; **`src/fleet/supervisor_v2.py` module is missing**. Silent v1 fallback. |
| P4 | Scout empirical probe baseline against live dispatcher | ❌ Not run. |
| P5 | Aiden gate D approval on Step 6 archive execution | ❌ Not granted. |

---

## §3 Three options for proving `fleet_session_mgmt`

### Option A — Reframe the gate to match what is shipped (recommended for speed)

Scope the gate as: *"SessionManager abstraction + supervisor v2 flag mechanism + Nova spawn via SessionManager are shipped and verifiable."*

**Proof path:** static + test-suite + dispatcher health, same shape as the `fleet_autostart_recovery` proof I just landed:
1. STATIC — `SessionManager` exists with both backends; `Backend` enum present; tests exist.
2. TEST — `pytest tests/dispatcher/test_session_manager.py -q` passes.
3. LIVE — `dispatcher.service` health + Nova spawn round-trip via `POST /dispatcher/spawn`.

**Effort:** ~2 hours for the proof script + PR (same shape as PR #1407).
**Attestation:** binding_reviewer by elliot or dave (no-self-attest passes — `built_by_callsign` would be set during proof to the actual KEI-184 author = orion; check the trigger constraint before insert).
**Honest about state:** gate proven = abstraction is in place; cutover execution is **out of scope** and tracked as a separate gate.

### Option B — Expand the gate to "full cutover executed"

Scope the gate as the entire session retirement plan: Phase A (per-agent serial cutover with 24h soak between agents) + Phase B (shared teardown + supervisor reactivation + canonical key write).

**Proof path:** the canonical `ceo:tmux_layer_retired_<date>` key written with verbatim verification output per §6 D of `cutover_runbook.md`.

**Effort:**
- Pre-flight verify (1–2 hr): all 9 §1 gate items GREEN. **Currently 6/9 — P3 (supervisor_v2 module) + P4 (Scout probe) + P5 (Aiden gate D) are RED.**
- **Author `src/fleet/supervisor_v2.py`** (1–2 days): the missing module Max's plan assumes exists. Replaces `tmux capture-pane` + `tmux send-keys` calls with dispatcher REST calls.
- Phase A (6 × 24h serial soak = ~6 days wall clock): Nova → Scout → Orion → Atlas → Aiden → Max → Elliot. Each: stop v1 substrate → flip flag → start v2 dispatch → verify first-spawn + 24h soak gate (liveness + tool-call activity + no regressions + 1 bd claim cycle).
- Phase B (4–6 hr): teardown + fleet supervisor reactivation + ceo_memory canonical write.
- **Total: ~9–10 days end-to-end** (assuming no soak-gate failures + Aiden gate D approval lands in advance).

**Risk:** high. Six days serial means six 24-hour windows where any single soak-gate failure rolls that agent back and blocks the next. The supervisor_v2 module being missing today is the load-bearing blocker — without it, "supervisor v2" is a silent no-op.

### Option C — Split into two gates (recommended for accuracy)

Rename / re-scope:

- **`fleet_session_mgmt`** (proven via Option A) → covers the **abstraction layer**: SessionManager + tmux/container_lifecycle + supervisor v2 flag mechanism + Nova spawn validation. This matches what is actually shipped + makes the row's `status='built'` defensible.
- **`fleet_cutover_execution`** (NEW gate, status=`not_started`) → covers Phase A + Phase B execution. Proof = `ceo:tmux_layer_retired_<date>` key + Phase B verify suite from `cutover_runbook.md` §6. Gated on:
  - `src/fleet/supervisor_v2.py` authoring (currently missing — this is the real blocker).
  - Scout empirical probe baseline.
  - Aiden gate D approval.
  - Per-agent 24h soak completion.

This splits a 2-hour deliverable from a 9-day deliverable, and surfaces the `supervisor_v2.py` gap as its own row rather than burying it in fleet_session_mgmt's notes.

**My recommendation: Option C.** Two reasons:
1. The current gate name + notes describe two different things at once (abstraction shipped + cutover not done). Splitting is the honest mapping.
2. Surfacing `supervisor_v2.py` as a separate blocker is the right governance step — right now the env flag implies cutover state that doesn't match reality. A separate gate row makes the gap legible to anyone reading `gate_roadmap`.

---

## §4 Open questions for Elliot + Dave (before building)

1. **Pick option** A / B / C. Default recommendation: C.
2. If C: rename `fleet_session_mgmt` semantics (notes update) + open `fleet_cutover_execution` row. Per migration `20260602_gate_roadmap_proof_gate.sql` schema, `gate_roadmap` already has `UNIQUE(component)` + status transitions; new row insert is straightforward.
3. Who authors `src/fleet/supervisor_v2.py`? Max's plan names it but Max's role per `feedback_max_verify_only_role_2026-06-02` is verify-only — Max does NOT build. Candidates: Atlas (current canary position in `s4_supervisor_v2_cutover_order.md`), Nova (already cut over per KEI-185), orion (this clone).
4. **`required_attestation_kind`** for the new rows — `ci_runner` (forces CI gate authoring) or `binding_reviewer` (allows manual dave attest)? Per Dave addendum 2026-06-02 + PR #1402's allowlist tightening, `ci_runner` is the harder + more durable path.
5. The dispatch said "do NOT start building yet, scope first." Confirmed — I have NOT started authoring `supervisor_v2.py` or running any cutover step. Awaiting direction.

---

## §5 If Option A or C abstraction-half is approved

Estimated work (I can dispatch self to do this in next session):

| Task | Effort |
|---|---|
| Author `scripts/proof_fleet_session_mgmt.sh` (mirroring `proof_fleet_autostart_recovery.sh`) | 1–1.5 hr |
| Static tier: confirm `SessionManager` API surface + `Backend` enum + both backends importable | inside above |
| Test tier: run `pytest tests/dispatcher/test_session_manager.py -q` and capture verbatim | inside above |
| Live tier: hit `/dispatcher/health` + Nova spawn round-trip + verify ephemeral session exits | inside above |
| Archive run to `docs/proof_runs/` + SHA256 | 5 min |
| PR + body + ready-to-paste attestation SQL (dave or elliot binding_reviewer) | 30 min |
| **Total** | **~2 hours** |

## §6 If Option B or C cutover-half is approved

Sequence (NOT executing here — proposed work order):

1. Pre-flight: re-verify 9 gate items from `cutover_runbook.md` §1. Currently 6/9 GREEN; need P3/P4/P5.
2. **Author `src/fleet/supervisor_v2.py`** (~1–2 days, separate PR). Spec from `session_retirement_plan.md` §2.2: replace `tmux capture-pane` + `tmux send-keys` with dispatcher REST calls; v2 code path operates without tmux dependency.
3. Scout empirical probe baseline run.
4. Aiden gate D approval secured.
5. Phase A — Nova → Scout → Orion → Atlas → Aiden → Max → Elliot, 24h soak between each. Elliot drives host-side `systemctl`. Per-agent rollback path documented in `s4_supervisor_v2_cutover_order.md`.
6. Phase B — disable elliot-check-agents, archive deprecated tmux scripts (Atlas PR), reactivate fleet supervisor on v2 path, write `ceo:tmux_layer_retired_<date>`.
7. Author `scripts/proof_fleet_cutover_execution.sh` proving the canonical key + Phase B §6 verify suite pass.

---

## §7 Anchors

- `docs/cutover/session_retirement_plan.md` (Max, 357 lines)
- `docs/cutover/cutover_runbook.md` (Atlas, 236 lines)
- `docs/runbooks/s4_supervisor_v2_cutover_order.md`
- `docs/runbooks/ephemeral_agent_decommission_tracker.md`
- `docs/architecture/ephemeral_persistence_boundary.md`
- `src/dispatcher/session_manager.py` + `tmux_lifecycle.py` + `container_lifecycle.py`
- `scripts/fleet_supervisor.py` (silent v1 fallback at line 1367)
- `ceo:ephemeral_spawn_contract_ratified` (canonical, 2026-05-28)
- `ceo:listener_architecture_post_cutover_ratified` (canonical, 2026-05-28)
- `ceo:cutover_plan_v1` (canonical, 2026-05-27)
- KEI-184 / KEI-185 / KEI-191 (dismissed) / KEI-193 / KEI-194 / KEI-213
- gate_roadmap rows: `fleet_session_mgmt` (built), `fleet_supervisor` (built, service DOWN), `fleet_stability_gate` (not_started)
