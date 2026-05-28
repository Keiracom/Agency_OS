# Hindsight Read-Path Cutover — Rollback Plan

**Author:** orion · **Dispatched by:** elliot (STEP 0 PRE-CONFIRMED) · 2026-05-28
**Scope:** Rollback companion for the A3-c2 step 5-B reader cutover (`Agency_OS-0zv1`) — the move of the retrieval **read path** from LlamaIndex/Weaviate to self-hosted Hindsight.
**Status:** Plan. Read-only authoring; no runtime change in this PR.

---

## Conceptual summary (plain English)

We have switched *reads* (recall) over to Hindsight, but we still *write* to the old Weaviate store as the authoritative copy and mirror a second copy into Hindsight's Postgres. That "write to both, read from Hindsight" state is the **partial cutover**. Because Weaviate is still complete and authoritative, rolling back is currently **cheap** — we point reads back at Weaviate and the fleet is whole again. This document says exactly *when* to roll back, *how*, *how to prove nothing was lost*, *how long the cheap window lasts*, and *who decides*.

## Current state (what we are rolling back from)

| Path | Today | Authority |
| --- | --- | --- |
| **Read / recall** | `orchestrator._hindsight_recall` → Hindsight v0.6.2 at `http://localhost:8889` (hard code cutover, no runtime flag) | Hindsight |
| **Write / index** | LlamaIndex → Weaviate **and** mirror into Hindsight Postgres (dual-write) | **Weaviate (source of truth)** |
| **Fallback** | Weaviate remains the complete recall fallback for the whole dual-write window | Weaviate |

Empirical gates currently green:
- `scripts/research/hindsight_smoke/validate_hybrid_recall.py` (stz8) — BM25 + vector legs both PASS at rank 1.
- `scripts/migrations/a5_smoke_recall.py` (a5) — **3/4 PASS**, `rc=1` strict; relevance gate = **≥2 signal tokens per memory**. Frozen baseline: `docs/migration/evidence/a5_smoke_recall_results_2026-05-27.json`.

> A rollback restores the read path to Weaviate/LlamaIndex. Because writes never stopped flowing to Weaviate, **no corpus reconstruction is needed** *provided* the dual-write window held and Weaviate was not purged (see §4).

---

## 1. Rollback trigger criteria (specific + falsifiable)

Roll back if **any one** of these fires and cannot be fixed-forward inside the same operating window:

**T1 — Recall surface regression.** `a5_smoke_recall.py` drops below **3/4 pieces PASS**, OR any of the three currently-passing pieces (`piece_1b_ceo_memory`, `piece_2_weaviate_snapshot`, `piece_3_drive_manual`) falls back under the **≥2 signal-tokens-per-memory** gate vs the frozen `2026-05-27` baseline. (Piece 4 is a known operator-prereq gap, `Agency_OS-ygxz` — its failure is NOT a trigger.)

**T2 — Hybrid recall broken.** `validate_hybrid_recall.py` shows **either** leg failing — the BM25/lexical leg (rare-exact-token query) **or** the vector/semantic leg (paraphrase query) no longer surfaces its target at rank 1. A single-leg collapse means Hindsight is silently degraded to pure-vector or pure-lexical.

**T3 — Service unavailable.** `GET http://localhost:8889/version` returns non-200 for **>5 min**, OR the `keiracom-fleet-hindsight` container is restart-looping, OR recall latency exceeds the 30 s `HINDSIGHT_RECALL_TIMEOUT_SECONDS` budget on **>10%** of calls sustained over 15 min.

**T4 — Mirror-write integrity loss.** Hindsight Postgres rejects mirror writes (the `shm_size`/`PG0` class of failure addressed by #1247) and the reject rate is non-zero after one restart. Dual-write is the safety net; if it is broken, the cheap-rollback window is closing — escalate immediately.

**Not a trigger:** a single transient recall miss, piece 4, or one flaky CI run. Triggers are sustained/threshold conditions, not one-off noise.

---

## 2. Recovery steps — restore the persistent tmux fleet

**Step A — Revert the read path (code).** There is **no runtime flag** on the Hindsight reader; it is a hard cutover in `src/retrieval/orchestrator.py` (`_gather_ann_pool` → `_hindsight_recall`). Fastest path back is to revert the reader-cutover commit on `main` and redeploy:

```bash
# On main, after the rollback call (§5):
git revert --no-edit <Agency_OS-0zv1 reader-cutover sha>   # restores LlamaIndex/Weaviate read path
git push                                                    # CI + deploy picks it up
```

**Step B — Hindsight service.** Reads no longer touch it after Step A, so it can be left running. To stop it cleanly:

```bash
systemctl --user stop keiracom-fleet-hindsight    # or: docker compose -f keiracom_system/fleet/hindsight/docker-compose.yml down
# Do NOT delete the named volume keiracom_fleet_hindsight_pg_data — it holds the mirror (needed for §3).
```

**Step C — Restore the fleet to operational state.** The persistent tmux fleet (sessions `aiden atlas elliottbot maxbot nova orion scout`) is supervised by systemd `--user` units: `<callsign>-agent.service` (KEI-94 tmux keep-alive — recreates the session if it died), `<callsign>-inbox-watcher.service` (dispatch routing), `<callsign>-nats-*-bridge.service` (NATS routing — the suffix varies per callsign: `-dispatch-`, `-review-`, `-inbox-`), and `agent-self-claim-loop@<callsign>.service` (KEI-92). After Step A's redeploy, restart **every running fleet unit** so each callsign reattaches to a clean worktree on latest `main`.

Enumerate-live (drift-proof as the fleet grows — do **not** hardcode a callsign list):

```bash
systemctl --user list-units --type=service --state=running --plain --no-legend \
  | awk '{print $1}' \
  | grep -E -- '-(agent|inbox-watcher|nats-[a-z]+-bridge)\.service$|^agent-self-claim-loop@' \
  | grep -vE '^(gpg-agent|agent-memories-indexer)\.service$' \
  | xargs -r systemctl --user restart
```

The pattern matches all four fleet unit families for every callsign. The second `grep -v` excludes the only non-fleet collisions (`gpg-agent`, `agent-memories-indexer`); the `nats-server` broker is **not** matched (it has no `-agent`/`-inbox-watcher`/`-nats-*-bridge` suffix) and must never be restarted here — doing so disrupts all inter-agent comms. Verified live 2026-05-28: the pattern selects 27 units (7 agents + 7 inbox-watchers + 7 NATS bridges + 6 active claim-loops; `agent-self-claim-loop@elliot` is intentionally inactive and is correctly left untouched). Relay-watchers are intentionally inactive and excluded; resurrect them only if a specific recovery needs them.

**Step D — Confirm operational.** `tmux list-sessions` shows all 7; `systemctl --user --failed` is clean (note: `migration-apply-watcher.service` may already be failed pre-rollback — confirm it is not newly broken); one `a5_smoke_recall.py` run returns relevant memories from the restored Weaviate read path.

---

## 3. Data integrity check — verify no corpus writes were lost

The only way a write is *lost* on rollback is if it landed in **Hindsight only** and never in Weaviate. The standing write path dual-writes (Weaviate authoritative + Hindsight mirror), so under normal operation Weaviate is a superset and rollback loses nothing. The check confirms that invariant held for the cutover window.

1. **Define the window.** `cutover_ts` (A3-c2 step 5-B merge) → `rollback_ts` (now). Only writes in this window are at risk.
2. **Per-store reconciliation.** For each `(Weaviate class ↔ Hindsight bank)` pair in `orchestrator.HINDSIGHT_BANK_BY_CLASS` (Decisions↔fleet_decisions, Keis↔fleet_keis, AgentMemories↔fleet_agent_memories, Discoveries↔fleet_discoveries, …), compare object counts created in-window:
   - Weaviate class object count (authoritative).
   - Hindsight bank `fact_count` (the a5 doc tracked `fleet_smoke` 703 → 1341).
   - **Invariant:** Weaviate count ≥ Hindsight mirror count for that window. If Weaviate ≥ Hindsight, rollback is loss-free.
3. **Hindsight-only residue.** If any bank shows atoms with no Weaviate counterpart (Hindsight count > Weaviate, or content-hash diff), those writes bypassed Weaviate. **Back-fill them to Weaviate before declaring rollback complete** — do not purge the `keiracom_fleet_hindsight_pg_data` volume until this is done.
4. **Recall-surface confirmation.** Re-run `a5_smoke_recall.py` against the restored Weaviate path and compare relevant-memory counts to the frozen `2026-05-27` baseline. Equal-or-better = corpus intact on the read side.

---

## 4. Time window — how long rollback stays cheap

Rollback is **low-cost while Weaviate remains complete and authoritative**. Two events end the cheap window — after either, rollback requires reverse-migrating from Hindsight Postgres (expensive, bespoke, error-prone):

- **The source purge runs.** `scripts/migration/weaviate_cutover.py --purge-old` (opt-in, Step 5 of the Weaviate cutover plan) deletes from the source collection. After purge, Weaviate is no longer a full fallback.
- **The write path is cut to Hindsight-only.** The current LlamaIndex→Weaviate write path is transitional (per `orchestrator.py`). When it is removed, new writes land only in Hindsight and rollback can no longer rely on Weaviate.

**Recommendation:** keep the dual-write window open — **do not purge, do not remove the LlamaIndex write path** — until the empirical gates hold green across a defined soak (e.g. N consecutive green `a5_smoke_recall` + `validate_hybrid_recall` runs over a fixed period). Treat the purge/write-cut as the point of no cheap return; gate it behind an explicit Dave GO (§5).

---

## 5. Who makes the rollback call

- **Detection:** any worker (orion/atlas) or the CI/smoke harness can *flag* a trigger (§1) with verbatim evidence.
- **Decision:** the GO/NO-GO on rollback is **Dave's**. Per blocker-escalation governance (Dave R13), **Elliot surfaces the trigger to #ceo first** — the moment a §1 criterion fires, not after peer debate — in plain English: what fired, the evidence, the reversible action, and the resume condition.
- **Execution:** once Dave calls it, a worker (orion/atlas) runs §2; a deliberator (Aiden) verifies §3 before the rollback is declared complete.
- **The purge / write-cut (the point of no cheap return, §4) requires a separate explicit Dave GO** — it is not bundled into routine cutover progress.

---

## Notes — canonical key cross-check (per audit-dispatch checklist, `_orchestrator.md`)

This artefact describes the memory-layer cutover, so the relevant canonical key is **`ceo:memory_abstraction_layer_v1`** (RATIFIED — Hindsight self-hosted as engine; Aiden gate F: "Migration runner is P0 critical-path"; eleven-agreed-positions: "Hindsight self-hosted as engine", per-tenant VPC). The reader-cutover this rolls back is the fleet-internal precursor to that per-tenant migration. Claims above (dual-write, Weaviate-as-fallback, no-flag-day, per-step reversibility) are consistent with `docs/migration/weaviate_cutover_plan.md` and the `Agency_OS-0zv1` reader cutover. The Hindsight migration runner itself (multi-tenant, rollback-per-tenant, built before launch) is the Phase 2.1+ generalisation of this plan.
