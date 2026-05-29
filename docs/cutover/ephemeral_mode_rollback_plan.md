# Ephemeral Agent Mode Cutover — Rollback Plan

**Author:** elliot · 2026-05-28
**Scope:** Rollback for the **persistent-tmux → ephemeral self-driving-loop** cutover (Dave personal cutover, Phase 1). Companion to `rollback_plan.md` (which covers only the Hindsight **read-path**). This doc covers falling the **whole self-driving loop** back to manual / persistent-tmux operation.
**Status:** Plan. No runtime change.

---

## Conceptual summary (plain English)

We are switching from always-on tmux agents that Elliot dispatches by hand, to an **ephemeral self-driving loop**: a task row trips a Postgres trigger → a bridge publishes it to Valkey → a consumer admits it under a tenant ceiling → the dispatcher spawns an agent on demand → the agent exits and frees its slot.

Until that loop proves stable **unattended for 48–72 hours**, the old always-on tmux fleet stays **WARM — running, not torn down**. Rollback is therefore one move: **switch the loop off, fall back to manual/tmux operation.** Dave is the entire business running through this, so "we can get back if it breaks at 9pm" matters more than "the test passed."

## Current state (what we roll back from / to)

| Path | Cutover (new) | Fallback (kept warm) |
| --- | --- | --- |
| **Dispatch** | task row → trigger → bridge → Valkey → consumer → `/dispatcher/spawn` (ephemeral) | Elliot manual dispatch into persistent tmux panes |
| **Agents** | spawned on demand, exit when done | 7 always-on tmux sessions (supervised by systemd) |
| **Loop units** | `keiracom-workloop-bridge` + `keiracom-workloop-consumer` (systemd --user) | left **UNENABLED** during the warm window |

> The persistent tmux fleet is **not decommissioned** at cutover. It is the live fallback. Tearing it down is the point of no cheap return (§4).

---

## 1. Rollback trigger criteria (specific + falsifiable)

Roll back if **any one** fires and cannot be fixed-forward inside the same operating window:

- **T1 — Loop seizure.** Tasks accumulate in `keiracom:tasks:available` unconsumed for >10 min, OR the per-tenant `active_spawns` counter stays pinned at ceiling with no releases (slots not freeing), OR the bridge/consumer process is down/restart-looping.
- **T2 — Cost runaway.** The spend circuit breaker fires (daily tripwire), OR projected monthly spend crosses the **A$350/mo** ceiling. (Depends on the cost-guard blocker, `Agency_OS-wdws`.)
- **T3 — Spawn crash-loop.** Repeated spawn → crash → reconcile → respawn with no task progress; dead-letter rate spiking above baseline.
- **T4 — Memory/data corruption.** Live AtomV1 writes malformed, or Hindsight integrity loss (cross-ref `rollback_plan.md` §1 for the read-path triggers).
- **T5 — Silent component death.** A loop component dies and a heartbeat is missed (depends on silent-failure alerting, `Agency_OS-52wu`).

**Not a trigger:** a single task failing and dead-lettering (that is normal handling), one transient spawn error, one flaky run.

---

## 2. Recovery steps — switch the loop off, fall back to tmux

**Step A — Halt new spawns (the one move).** Disable the two loop units so nothing new is admitted or published:

```bash
systemctl --user disable --now keiracom-workloop-consumer keiracom-workloop-bridge
```

During the warm window these units are the *only* thing turned on for the loop — flipping them off stops the self-driving behaviour immediately.

**Step B — Preserve in-flight work (lose nothing).** Do **not** purge the Valkey queue. Let active spawns finish or terminate them via `/dispatcher/terminate` (which frees their slots). Any unconsumed tasks remain in `keiracom:tasks:available` + per-tenant overflow for replay; dead-lettered tasks already notify #ceo (`Agency_OS-gl3v`). Confirm no task is silently dropped.

**Step C — Confirm the persistent tmux fleet is live.** It was never torn down (keep-warm rule, §4), so it should already be running. Verify the 7 sessions + their supervisor units, reusing the drift-proof enumeration from `rollback_plan.md` §2:

```bash
tmux list-sessions                       # expect aiden atlas elliottbot maxbot nova orion scout
systemctl --user list-units --type=service --state=running --plain --no-legend \
  | awk '{print $1}' \
  | grep -E -- '-(agent|inbox-watcher|nats-[a-z]+-bridge)\.service$|^agent-self-claim-loop@' \
  | grep -vE '^(gpg-agent|agent-memories-indexer)\.service$'
# (verify present; restart any that died — never restart nats-server here)
```

Resume **manual Elliot dispatch** into the tmux panes (the pre-cutover operating mode).

**Step D — Confirm operational.** Agents respond to a test dispatch; `systemctl --user --failed` is clean (note `migration-apply-watcher.service` may be pre-failed — confirm not newly broken); spend returns to baseline; no orphaned spawns (`/dispatcher/health` slot counters at zero or expected).

---

## 3. Data integrity — verify nothing was dropped

1. **In-flight tasks.** Reconcile `keiracom:tasks:available` + per-tenant overflow + the dead-letter set against the source `tasks` table — every admitted task either completed, requeued, or dead-lettered-with-notification. None vanished.
2. **Slot accounting.** All `active_spawns:{tenant}` counters return to 0 after spawns drain (no leaked slots). `reconcile_all()` reclaims any crashed-agent residue.
3. **Memory writes.** If AtomV1 live writes were active, confirm no partial/corrupt atoms landed (cross-ref `rollback_plan.md` §3 dual-write invariant). The old store stays authoritative (additive-not-destructive), so recall is intact.

---

## 4. Time window — how long rollback stays cheap

Rollback is **one move while the persistent tmux fleet stays warm.** The point of no cheap return:

- **Tearing down the persistent tmux fleet** (disabling `<callsign>-agent.service` keep-alives / removing worktrees).
- **Retiring the old memory store** before the verify-before-retire gate passes (`Agency_OS-jolj`).

**Recommendation:** keep the persistent tmux fleet warm and the old memory store intact until the ephemeral loop runs cleanly **unattended for 48–72 h** (the soak), with the cost guard, dead-letter notification, and silent-failure alerting all live. Treat teardown/retire as the point of no cheap return — gate it behind an explicit Dave GO (§5).

---

## 5. Who makes the rollback call

- **Detection:** any worker, the circuit breaker, the heartbeat alerting, or Elliot's sweep can *flag* a §1 trigger with verbatim evidence.
- **Decision:** GO/NO-GO is **Dave's**. Per blocker-escalation governance (Dave R13), **Elliot surfaces the trigger to #ceo first** — the moment a §1 criterion fires — in plain English: what fired, the evidence, the reversible action (Step A), and the resume condition.
- **Execution:** Step A (halt) is reversible and may be run immediately to stop bleeding (cost/crash-loop) while Dave is looped in; Steps B–D follow on Dave's call.
- **Teardown / retire (point of no cheap return, §4) requires a separate explicit Dave GO** — never bundled into routine cutover progress.

---

## Dependencies (rollback can only detect what these provide)

The triggers above depend on the operational-safety blockers being live: cost guard / circuit breaker (`Agency_OS-wdws`, T2), dead-letter → #ceo notification (`Agency_OS-gl3v`, §2/§3), silent-failure heartbeat alerting (`Agency_OS-52wu`, T5). Until those land, detection is manual (Elliot sweeps) and rollback leans on the keep-warm fallback — which is exactly why the fleet stays warm through the soak.
