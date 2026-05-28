# Session Retirement Plan — Persistent tmux → Event-Triggered Ephemeral Spawning

**Owner:** Max (code-quality lens); Aiden gate D approval required before Step 6 execution.
**Status:** SPEC — awaiting Aiden CONCUR + Dave ratify before any host-side steps.
**bd:** Agency_OS — cutover gate item 3 (session retirement).
**Companion docs:**
- `docs/runbooks/ephemeral_agent_decommission_tracker.md` — post-cutover cleanup checklist (per-callsign; run AFTER this plan completes).
- `docs/architecture/dispatcher_wiring_inventory_kei213.md` — 9 launch-blocker gates; all 5 dispatcher-wired gates must be verified green before Step 3.
- `docs/runbooks/ephemeral_agent_dispatcher_install.md` — dispatcher scaffold install procedure.

---

## §1 What Gets Retired

### 1.1 Inbox watcher + send-keys relay

Per-callsign systemd service that polls the callsign's inbox directory and injects the message content into the running tmux pane via `tmux send-keys`. One unit per callsign:

```
{elliot,aiden,max,atlas,orion,scout,nova}-inbox-watcher.service
```

Supporting relay scripts (all reference `tmux send-keys`):

| Script | Role |
|--------|------|
| `scripts/orchestrator/relay_watcher.sh` | Inbox-dir → tmux send-keys |
| `scripts/orchestrator/kei45_realtime_listener.py` | NATS event → tmux send-keys |
| `scripts/orchestrator/auto_session_recovery.py` | Session death → re-inject via send-keys |
| `scripts/orchestrator/elliot_polling_loop.py` | 5-min bd poll → send-keys to all 6 panes |
| `scripts/orchestrator/deliberator_concur_router.py` | Route concur votes via tmux capture-pane |

Why: all of these assume a **persistent, named tmux session** that accepts injected input. After cutover, agents are ephemeral — they spawn per-task, run to completion, and exit. There is no persistent pane to send-keys to.

### 1.2 Persistent keepalive tmux sessions

Per-callsign systemd service that maintains a named tmux session across reboots and process deaths:

```
{elliot,aiden,max,atlas,orion,scout,nova}-agent.service
  └── ExecStart: scripts/agent_keepalive.sh <session> <callsign> <worktree>
```

The keepalive script (`scripts/agent_keepalive.sh`) creates the tmux session, spawns `claude` inside it, and uses systemd `Restart=on-failure` to resurrect it when the process dies. Bounded-spawn discipline (Dave 2026-05-27) already mandates fresh-context restarts — this was a step toward ephemeral but is still a persistent session model.

Also retired: per-callsign NATS bridge units (3 per callsign = 21 total):
```
{callsign}-nats-inbox-bridge.service
{callsign}-nats-{dispatch,review}-bridge.service
```

And the Elliot-only liveness checker:
```
elliot-check-agents.service + elliot-check-agents.timer
```

### 1.3 Fleet supervisor (current form)

`scripts/fleet_supervisor.py` + its systemd timer (every 5 minutes). Current role: scan all 7 tmux panes via `tmux capture-pane`, detect idle/stale/dead agents, inject task prompts via `tmux send-keys`.

The 5-minute polling + tmux-scan pattern is fundamentally incompatible with ephemeral agents: a spawned agent exits on task completion — there is no pane to capture. The supervisor must move from "scan panes" to "query dispatcher state."

---

## §2 What Replaces It

### 2.1 Event-triggered spawning via KEI-213 dispatcher

**Canonical dispatcher:** `src/dispatcher/main.py` (FastAPI, port 4001). Receives `POST /dispatcher/spawn`, routes through all 5 wired cutover-blocker gates, calls `SessionManager.spawn()`.

`SessionManager` supports two backends:
- **tmux backend** (current default): spawns an ephemeral tmux session per task; session exits when the Claude process completes. No keepalive. No send-keys injection needed — the task brief is embedded in the spawn call's `context` field.
- **container backend**: Docker container per task; health-checked; exit on task completion.

Both backends are **ephemeral**: the agent process terminates when the task is done. No persistent session is kept alive between tasks.

**Spawn flow (replaces inbox watcher + send-keys relay):**

```
Orchestrator / NATS event / timer
    │
    └── POST /dispatcher/spawn
            {callsign, task_brief, context, task_type, idempotency_key}
            │
            ├── Idempotency gate (PR A #1222) — drop duplicates
            ├── Budget ceiling gate (PR B #1223) — queue/drop if overage
            ├── SessionManager.spawn() — ephemeral Claude process
            ├── Spawn attribution emit (PR D #1225)
            └── HTTP 200 {spawned: true, handle: ...}
```

**Why this replaces inbox watchers:** the dispatcher's `SessionManager.spawn()` passes the task brief directly as a CLI argument or environment variable to the spawned `claude` process. No running pane exists to inject into — the brief is delivered at spawn-time, not via send-keys after the session is already running.

### 2.2 Fleet supervisor — reactivated in new role

Fleet supervisor **is not deleted** — it is updated to operate without tmux dependencies. Post-cutover role:

| Old behaviour | New behaviour |
|---|---|
| `tmux capture-pane` to detect agent state | Query `dispatcher.sessions` DB table (or REST `GET /dispatcher/sessions`) |
| `tmux send-keys` to inject task prompts | `POST /dispatcher/spawn` to request a new ephemeral spawn |
| 5-min polling for dead sessions | Subscribe to spawn-lifecycle events (task_complete / spawn_failed) OR keep 5-min poll against dispatcher state |
| Release stale claims (>2h, no activity) | Call `POST /dispatcher/spawn` with `force_evict: true` on stale sessions |

The fleet supervisor becomes a **dispatcher health monitor and requeue agent** rather than a tmux supervisor. The `FLEET_SUPERVISOR_V2_ENABLED` and `AGENT_ROUTING=v2` flags that are already gated in `fleet_supervisor.py` provide the v2 code path for this transition.

Scripts that need targeted updates (not archive):

| Script | Update required |
|--------|----------------|
| `scripts/fleet_supervisor.py` | Replace `tmux capture-pane` + `tmux send-keys` calls with dispatcher REST calls under `v2` flag |
| `scripts/bd_fleet_check.py` | Read dispatcher `sessions` endpoint instead of `tmux capture-pane` |
| `scripts/orchestrator/elliot_polling_loop.py` | Poll dispatcher state instead of injecting into 6 tmux panes |
| `scripts/orchestrator/deliberator_concur_router.py` | Read from inbox queue files directly; remove capture-pane dependency |
| `scripts/orchestrator/bd_complete_hook.sh` | Strip `tmux capture-pane` calls |

### 2.3 NATS-to-inbox bridge replacement

The NATS bridge units (`{callsign}-nats-*-bridge.service`) fan NATS events into per-callsign inbox JSON files. Post-cutover, the dispatcher listens on its own NATS subjects directly (`keiracom.{callsign}.spawn`) — no bridge layer needed. Bridge units are disabled and archived.

---

## §3 Step-by-Step Cutover Procedure

**Reversibility boundary: Steps 1–5 are fully reversible** (re-enable any disabled service). **Step 6 is the point of no return** — archive steps remove service files from `~/.config/systemd/user/`. Mark this explicitly before proceeding past Step 5.

**Callsign order:** `max` → `nova` → `scout` → `aiden` → `atlas` → `orion` → `elliot` (Elliot last; it is the orchestrator and has the most blast radius if something breaks).

### Pre-flight (run once, before any per-callsign steps)

```bash
# PF-1: Verify dispatcher service is running on all callsigns
for c in max nova scout aiden atlas orion elliot; do
    systemctl --user is-active keiracom-dispatcher@${c}.service && echo "OK $c" || echo "FAIL $c"
done

# PF-2: Smoke-test one spawn through the canonical dispatcher
curl -s -X POST http://localhost:4001/dispatcher/spawn \
  -H 'Content-Type: application/json' \
  -d '{"callsign":"max","task_brief":"echo smoke-test","task_type":"smoke","idempotency_key":"retirement-preflight-1"}' \
  | jq '.spawned, .handle'
# Expected: true, <handle-id>

# PF-3: Verify all 5 dispatcher-wired launch-blocker gates are green
# (idempotency PR A #1222, budget ceiling PR B #1223, context-window PR C #1224,
#  spawn attribution PR D #1225, bounded-spawn-kill Agency_OS-gcpm)
python3 -m pytest tests/dispatcher/ -q
# Must be 0 failures before proceeding.

# PF-4: Snapshot current service state for rollback reference
systemctl --user list-units --all '*-agent.service' '*-inbox-watcher.service' \
  '*-nats-*-bridge.service' --no-legend > /tmp/service_state_pre_cutover_$(date +%Y%m%d_%H%M%S).txt
```

### Step 1 — Stop inbox watcher for target callsign

```bash
CALLSIGN=max  # repeat for each callsign in order

systemctl --user stop ${CALLSIGN}-inbox-watcher.service
systemctl --user disable ${CALLSIGN}-inbox-watcher.service
# Reversible: systemctl --user enable --now ${CALLSIGN}-inbox-watcher.service
```

**Verify:** no new messages are being injected via send-keys into the old tmux pane. Inbox dir (`/tmp/telegram-relay-${CALLSIGN}/inbox/`) still accumulates files — they are now processed by the dispatcher's inbox loop, not the relay watcher.

### Step 2 — Stop persistent keepalive agent session

```bash
systemctl --user stop ${CALLSIGN}-agent.service
systemctl --user disable ${CALLSIGN}-agent.service
# Reversible: systemctl --user enable --now ${CALLSIGN}-agent.service
```

**Verify:** `tmux has-session -t ${CALLSIGN}` returns non-zero (session gone). Any in-flight work should have been allowed to complete before this step — check `bd show` for active claims and wait for completion before stopping.

### Step 3 — Disable NATS bridge units for callsign

```bash
for unit in ${CALLSIGN}-nats-inbox-bridge.service \
            ${CALLSIGN}-nats-dispatch-bridge.service \
            ${CALLSIGN}-nats-review-bridge.service; do
    systemctl --user stop ${unit} 2>/dev/null || true
    systemctl --user disable ${unit} 2>/dev/null || true
done
# Reversible: systemctl --user enable --now ${unit}
```

### Step 4 — Verify dispatcher handles the callsign

```bash
# Smoke spawn — confirm ephemeral session spawns, runs, and exits cleanly
curl -s -X POST http://localhost:4001/dispatcher/spawn \
  -H 'Content-Type: application/json' \
  -d "{\"callsign\":\"${CALLSIGN}\",\"task_brief\":\"echo cutover-smoke-ok\",\"task_type\":\"smoke\",\"idempotency_key\":\"retirement-step4-${CALLSIGN}-$(date +%s)\"}" \
  | jq '.spawned, .handle'

# Confirm the spawned session exited after task completion
sleep 10
curl -s "http://localhost:4001/dispatcher/sessions" | jq ".[] | select(.callsign == \"${CALLSIGN}\")"
# Expected: no active session for callsign (it completed and exited)
```

**Pass criteria:** `spawned: true`, session appears in dispatcher, then exits within task-completion window (~30s for a smoke task). If this fails, immediately re-enable the stopped services (rollback, see §4).

### Step 5 — Repeat Steps 1–4 for next callsign

Work through: `max` → `nova` → `scout` → `aiden` → `atlas` → `orion` → `elliot`. Do not proceed to Step 6 until all 7 callsigns have passed Step 4.

### Step 6 — Fleet supervisor migration (POINT OF NO RETURN begins here)

**Pre-condition:** all 7 callsigns have passed Step 4 smoke tests.

```bash
# Enable v2 path in fleet supervisor
export FLEET_SUPERVISOR_V2_ENABLED=1
# Add to ~/.config/agency-os/.env for persistence

# Run fleet supervisor in dry-run mode against dispatcher
python3 scripts/fleet_supervisor.py --dry-run 2>&1 | head -40
# Verify: output shows dispatcher REST calls, NOT tmux capture-pane calls

# If v2 dry-run looks clean, restart the supervisor timer
systemctl --user restart fleet-supervisor.timer
```

### Step 7 — Disable Elliot liveness checker + relay scripts

```bash
systemctl --user stop elliot-check-agents.service elliot-check-agents.timer
systemctl --user disable elliot-check-agents.service elliot-check-agents.timer
```

### Step 8 — Archive deprecated scripts (decommission tracker execution)

Run the per-callsign cleanup from `docs/runbooks/ephemeral_agent_decommission_tracker.md`. This archives (moves to `scripts/archive/`) the scripts listed in §2 of that document. **Requires Aiden gate D approval before execution.**

```bash
# Archive tmux-dependent scripts
for script in \
  scripts/agent_keepalive.sh \
  scripts/orchestrator/relay_watcher.sh \
  scripts/orchestrator/kei45_realtime_listener.py \
  scripts/orchestrator/kei45_idle_daemon.sh \
  scripts/orchestrator/auto_session_recovery.py \
  scripts/orchestrator/kei45_acceptance_test.sh \
  scripts/systemd_agent_supervisor.sh; do
    git mv "${script}" "scripts/archive/$(basename ${script})"
done
git commit -m "[MAX] chore(cutover): archive deprecated tmux-session scripts post-retirement"
```

---

## §4 Rollback Plan

Each retired service can be individually re-enabled until Step 6 completes. Steps 1–5 are additive disables only — no files are moved or deleted.

### Per-callsign rollback (Steps 1–5)

```bash
CALLSIGN=<failing-callsign>

# Re-enable inbox watcher
systemctl --user enable --now ${CALLSIGN}-inbox-watcher.service

# Re-enable persistent keepalive session
systemctl --user enable --now ${CALLSIGN}-agent.service

# Re-enable NATS bridges
for unit in ${CALLSIGN}-nats-inbox-bridge.service \
            ${CALLSIGN}-nats-dispatch-bridge.service \
            ${CALLSIGN}-nats-review-bridge.service; do
    systemctl --user enable --now ${unit} 2>/dev/null || true
done

# Confirm session is back
tmux has-session -t ${CALLSIGN} && echo "session restored" || echo "may need ~10s for keepalive to recreate"
```

**Recovery time:** ~30 seconds (systemd restart + tmux keepalive spin-up).

### Fleet supervisor rollback (Step 6)

```bash
# Revert to v1 path
unset FLEET_SUPERVISOR_V2_ENABLED
# Remove from ~/.config/agency-os/.env
sed -i '/FLEET_SUPERVISOR_V2_ENABLED/d' ~/.config/agency-os/.env
systemctl --user restart fleet-supervisor.timer
```

### Full fleet rollback (all steps failed)

```bash
# Restore from pre-cutover snapshot
cat /tmp/service_state_pre_cutover_*.txt

# Re-enable everything from the snapshot
for svc in elliot aiden max atlas orion scout nova; do
    systemctl --user enable --now ${svc}-agent.service
    systemctl --user enable --now ${svc}-inbox-watcher.service
done
```

### Archive rollback (Step 8 — requires git revert)

```bash
git revert <archive-commit-sha>
# Restores files from scripts/archive/ back to scripts/
```

---

## §5 Estimated Downtime

**Definition:** time a given callsign cannot accept or process new task dispatches.

| Phase | Duration | Scope |
|---|---|---|
| Pre-flight (Steps PF-1 – PF-4) | 0 (read-only checks) | None |
| Per-callsign Steps 1–4 | ~30–60 seconds per callsign | One callsign at a time |
| Fleet supervisor migration (Step 6) | ~30 seconds (timer restart) | Supervisor gap only; agents unaffected |
| Archive step (Step 8) | 0 (git mv; services already disabled) | None |

**Total fleet window:** 7 callsigns × ~45s = ~5 minutes of aggregate per-callsign downtime, but staggered: no two callsigns go dark simultaneously.

**Zero-downtime conditions (must be true for the 30–60s window to hold):**
1. KEI-213 dispatcher is healthy on port 4001 before per-callsign steps begin (verified in PF-1 + PF-2).
2. No in-flight task is active for the target callsign when Step 2 fires (verified by checking `bd show --active` before stopping the agent service).
3. The tmux backend in `SessionManager` is used (not container backend) — same spawn latency as the old keepalive.

If the dispatcher is not reachable at cutover time, **do not proceed** — execute the pre-flight rollback (nothing has been disabled yet) and investigate dispatcher health.

---

## §6 Open Prerequisites

The following must be complete before executing this plan:

| # | Prerequisite | Status | Owner |
|---|---|---|---|
| P1 | All 5 dispatcher-wired cutover-blocker gates passing in CI | Merged (PRs #1222–#1225 + Agency_OS-gcpm) | Orion/Atlas |
| P2 | `keiracom-dispatcher@<callsign>.service` running for all 7 callsigns | Verify: `systemctl --user is-active keiracom-dispatcher@elliot.service` | Elliot ops |
| P3 | Fleet supervisor v2 flag implemented and tested | Flag exists; v2 code path needs tmux-removal pass | Max / Atlas |
| P4 | Empirical probe (adversarial probe suite PR #1251) baseline run against live dispatcher | Needed to confirm recall quality is unchanged post-cutover | Scout |
| P5 | Aiden gate D approval on Step 6 archive execution | Required per governance | Aiden |
