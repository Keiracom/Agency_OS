# V1 Chain Dress Rehearsal — Runbook

**Owner:** Aiden (chain) + Elliot (orchestration). Authored by scout 2026-05-29 for Agency_OS-jb4e.

This runbook is the operating manual for the **full V1 chain dress rehearsal** — driving a single task from a Slack `TASK:` message (or direct Face invocation) end-to-end through `Face → Aiden(plan) → Max(challenge) → Nova(build) → Orion(spec) + Atlas(safety) → complete → #ceo`, observing every hop, and confirming Dave sees the rolled-up result.

**Runnable when both of these merge:**
- PR **#1339** — Atlas `oevr` consumer loop (`keiracom.agent.handoff` → `advance_step`).
- PR **#1340** — Nova `zqni` final #ceo post on chain complete.

Everything else listed in the dispatch (Face entrypoint #1311, `v1_chain_orchestrator` state machine, AtomV1 handoff publish in `agent_cold_start.py` #1296+, `notify_complete` intermediate-step suppression #1337, spawn-context recall #1335) is already on `origin/main`.

---

## §1 — Pre-flight checklist

Run **all** of these as `elliotbot` on the fleet host. Every check must show ✅ before triggering the chain.

### 1.1 Chain-critical systemd units

```bash
systemctl --user is-active \
  dispatcher.service \
  nats-server.service \
  keiracom-work-loop-bridge.service \
  keiracom-work-loop-consumer.service \
  peer-event-ceo-relay.service \
  agency-os-elliot-slack-listener.service
```
**Expect:** `active` on every line (6 ✅). Any `inactive`/`failed` → §5.1.

### 1.2 All six callsign NATS dispatch bridges + the elliot inbox bridge + review bridges

```bash
for cs in aiden atlas elliot max nova orion scout; do
  unit=$(case $cs in
    elliot)      echo elliot-nats-inbox-bridge.service ;;
    aiden|max)   echo ${cs}-nats-review-bridge.service ;;
    *)           echo ${cs}-nats-dispatch-bridge.service ;;
  esac)
  printf "%-40s %s\n" "$unit" "$(systemctl --user is-active "$unit")"
done
```
**Expect:** 7 lines, every status `active`. Any `inactive` → §5.2.

### 1.3 Inbox-watchers (the post-#1309 reliable injectors)

```bash
for cs in aiden atlas elliot max nova orion scout; do
  printf "%-32s %s\n" "${cs}-inbox-watcher.service" \
    "$(systemctl --user is-active ${cs}-inbox-watcher.service)"
done
```
**Expect:** 7 ✅. Any `inactive` → §5.3 (re-run `bash scripts/install_inbox_watchers.sh`).

### 1.4 NATS reachability (1-second ping)

```bash
nats --server=nats://127.0.0.1:4222 rtt
```
**Expect:** sub-millisecond RTT. Connection refused → §5.4.

### 1.5 Postgres `public.tasks` reachable + the kei45 trigger present

```bash
source /home/elliotbot/.config/agency-os/.env
DSN="${DATABASE_URL//postgresql+asyncpg/postgresql}"
psql "$DSN" -t -c "SELECT to_regclass('public.tasks'), to_regclass('kei45_task_event_trigger');"
```
The `${DATABASE_URL//postgresql+asyncpg/postgresql}` strip is required: `DATABASE_URL` carries the SQLAlchemy-style `postgresql+asyncpg://…` prefix, which `psql` cannot parse, causing it to silently fall back to the missing local socket.

**Expect:** the first column resolves to `public.tasks` (table present). If either column is empty/NULL the relation does not exist → §5.5.

### 1.6 Chain state file clean (no stranded prior run)

```bash
ls -la /tmp/v1_chain_state.json 2>/dev/null && cat /tmp/v1_chain_state.json | jq '.'
```
**Expect:** missing file OR all entries with `current_step == "complete"`. If a stale entry has `pending != []`, see §6.

### 1.7 Dispatcher health

```bash
curl -s http://127.0.0.1:4001/dispatcher/health | jq '.'
```
**Expect:** every component `"ok"` or `"green"`. Any `"degraded"` → §5.6.

---

## §2 — How to trigger

Pick **ONE** of the three. The first is the canonical dress-rehearsal entrypoint; the others are escalation/debug paths.

### 2.A (canonical) — Dave types `TASK:` in #ceo

When the Slack capture → public.tasks wire (`scripts/ceo_capture_listener.py`, Agency_OS-yku8 + evbn / #1291) is live:

> `TASK: <one-line brief of the work>`

Example: `TASK: add a docstring to scripts/orchestrator/ops_failure_publish.py:_handle_envelope and run the existing tests`

- Recognised by `scripts/ceo_capture_listener.py:135` (`message.upper().startswith("TASK:")`).
- Inserts one `public.tasks` row with `status='available'` (line 147-169).
- `kei45_emit_task_event` trigger fires `pg_notify('task_event', …)`.
- `keiracom-work-loop-bridge.service` LISTENs → publishes to Valkey `keiracom:tasks:available` (`src/keiracom_system/work_loop/bridge.py`).
- `keiracom-work-loop-consumer.service` drains → POSTs `/dispatcher/spawn` with `spawn_kwargs.command = python3 -m src.keiracom_system.chat.face` (or its configured chain-entry command).

### 2.B — Direct Face invocation (smoke, no Slack required)

If 2.A's auto-spawn-Face wiring isn't yet exposed, drive Face directly from the host:

```bash
cd /home/elliotbot/clawd/Agency_OS
FACE_BRIEF="add a docstring to scripts/orchestrator/ops_failure_publish.py:_handle_envelope and run the existing tests" \
  python3 -m src.keiracom_system.chat.face
```
Face publishes the initial task_dispatch envelope to `keiracom.dispatch.aiden` (`src/keiracom_system/chat/face.py:58 DISPATCH_SUBJECT = "keiracom.dispatch.aiden"`). The chain begins.

### 2.C — Manual NATS publish (lowest-level debug)

```bash
TASK_ID="dress-rehearsal-$(date -u +%s)"
nats --server=nats://127.0.0.1:4222 pub keiracom.dispatch.aiden \
  "$(jq -nc --arg id "$TASK_ID" --arg b "<brief>" '{
     task_id: $id, chain_id: $id, chain_step: "aiden_plan",
     atom_id: null, brief: $b, ts: now, from: "dress_rehearsal_manual"
   }')"
```
Bypasses Face entirely. Useful when isolating "is the chain consumer working" from "is Face publishing correctly".

---

## §3 — What to watch (in real time, in this order)

Open **four** terminals (or tmux panes) before triggering, so every hop is witnessed.

### 3.1 Terminal A — every chain dispatch on every role

```bash
nats --server=nats://127.0.0.1:4222 sub 'keiracom.dispatch.>'
```
You expect 5 envelopes in sequence: `aiden`, `max`, `nova`, then *parallel* `orion` + `atlas` (order between the last two is non-deterministic). Each envelope carries `{task_id, chain_id, chain_step, atom_id, brief, ts, from}`.

### 3.2 Terminal B — every agent handoff (the Atlas-oevr trigger)

```bash
nats --server=nats://127.0.0.1:4222 sub 'keiracom.agent.handoff'
```
You expect 5 handoff atoms in sequence (one per role completion). Each carries `{task_id, atom_id, from_callsign, to_callsign, ts}` — published by `agent_cold_start._publish_handoff` (`src/keiracom_system/vault/agent_cold_start.py:236`).

### 3.3 Terminal C — chain state machine progression

```bash
watch -n 1 'jq . /tmp/v1_chain_state.json 2>/dev/null'
```
`current_step` walks `aiden_plan → max_challenge → nova_build → (orion_spec | atlas_safety) → complete`. `steps_done` grows by one per successful hop; `atom_ids` records each step's atom; `pending` carries the parallel-fan-out partners and clears as they complete.

### 3.4 Terminal D — dispatcher + chain-orchestrator logs

```bash
tail -F /home/elliotbot/clawd/logs/dispatcher.log \
        /home/elliotbot/clawd/logs/elliot-nats-inbox-bridge.log \
  | grep --line-buffered -E 'chain|advance_step|task_complete|chain_complete|handoff'
```
Key lines to look for:
- `v1_chain: published N bytes to keiracom.dispatch.<role>` (orchestrator → next role)
- `v1_chain: advance_step` (consumer received handoff, updated state)
- `task_complete: SUPPRESSED intermediate chain_step` (nd3b doing its job — §4 confirms)
- `chain_complete: notified #ceo` (zqni final post — §4 success line)

### 3.5 Per-role inbox-watcher logs (optional, deep diagnostic)

If a role's tmux pane never wakes up:
```bash
tail -F /home/elliotbot/clawd/logs/inbox_watcher_{aiden,max,nova,orion,atlas}.log
```
Expect `received: ...` then `injected+committed -> processed/: ...` per envelope hand-off (post-#1309 verify+retry behaviour, see PR #1316 era runbook entries).

---

## §4 — Success criteria

**Primary signal — what Dave sees in #ceo (and only this):**

```
✅ Chain complete — <task_id>
Brief: <the task brief>
Steps: aiden_plan → max_challenge → nova_build → orion_spec + atlas_safety
Cost: A$<x.xxxx>
chain_id: <chain_id>
```

This is the single per-chain Slack post fired by `_post_chain_complete` (zqni / #1340) via the new `/dispatcher/chain_complete` endpoint. nd3b (#1337) guarantees no other #ceo post fires for intermediate steps.

**Secondary signals — all on the watch terminals:**

- Terminal A: **5 envelopes** observed in the expected order/fan-out.
- Terminal B: **5 handoff atoms** observed, one per role.
- Terminal C: state file ends with `current_step: "complete"`, `pending: []`, all 5 step names in `steps_done`, and an atom_id recorded for each.
- Terminal D: exactly **one** `chain_complete: notified #ceo` line, exactly **five** `task_complete: SUPPRESSED intermediate chain_step` lines (one per role).
- `attribution/logger.py` data store shows attributed cost rows for the `task_id` covering all 5 steps.

**Failure of any secondary signal but a green primary post = false positive; do NOT call the rehearsal a pass.** Diagnose via §5.

---

## §5 — Failure modes (by symptom → check first)

### 5.1 A chain-critical service is `inactive` or `failed`

```bash
systemctl --user status <unit>
journalctl --user -u <unit> -n 100 --no-pager
```
Common culprits and fixes:
- `dispatcher.service` failed → check `/home/elliotbot/clawd/logs/dispatcher.log` tail; usually env-file or Vault unreachable.
- `keiracom-work-loop-bridge.service` failed → asyncpg LISTEN requires session-mode DSN; confirm `EnvironmentFile=-/home/elliotbot/.config/agency-os/work-loop-bridge.env` exists and sets `SUPABASE_DB_DSN` on `:5432` (`/home/elliotbot/.config/systemd/user/keiracom-work-loop-bridge.service` unit header).
- `keiracom-work-loop-consumer.service` failed → Valkey unreachable (`REDIS_URL`).
- `nats-server.service` failed → port 4222 collision OR JetStream storage path missing.

### 5.2 A callsign NATS bridge is `inactive`

The chain CANNOT advance past a step whose role bridge is down. Restart and rerun:
```bash
systemctl --user restart <role>-nats-dispatch-bridge.service
```
For `elliot-nats-inbox-bridge.service` failures, the elliot↔#ceo relay degrades but the chain still runs (no role to elliot in the V1 chain).

### 5.3 A callsign inbox-watcher is `inactive`

The role gets the NATS envelope but the tmux pane never sees it. Restart per `scripts/install_inbox_watchers.sh` (idempotent, re-renders the unit + restart). Symptom in §3.5 logs: nothing arrives in `inbox_watcher_<role>.log`.

### 5.4 NATS unreachable (`rtt` fails)

```bash
systemctl --user restart nats-server.service
nats --server=nats://127.0.0.1:4222 rtt
```
If still failing: check port 4222 isn't held by another process (`ss -ltnp | grep 4222`), then re-check JetStream storage path.

### 5.5 Postgres `public.tasks` not present OR kei45 trigger missing

Path A is blocked. Use Path 2.B or 2.C for the rehearsal, and file a follow-up KEI for the schema/trigger restore. Do NOT call the rehearsal a full pass with Path A skipped — Slack-origin is one of the success criteria.

### 5.6 Dispatcher health degraded

`curl /dispatcher/health` returns a component as `degraded`. Inspect `_component_status` keys (watchdog / reaper / etc.) and follow that subsystem's tail in `dispatcher.log`. Don't trigger the chain until health is green.

### 5.7 Chain stalled mid-flight — a hop hasn't fired

Most informative signal: which hop's envelope is **missing** from Terminal A, vs which **handoff atom** is missing from Terminal B.

| Missing | Likely cause | First check |
|---|---|---|
| no `keiracom.dispatch.aiden` envelope | Face never published | re-run §2.B with verbose: `python3 -m src.keiracom_system.chat.face` — look for `face: published … to keiracom.dispatch.aiden` |
| envelope on dispatch.<role> but no handoff atom | the role agent never exited (or `_publish_handoff` failed fail-open) | tail the role's tmux pane + `inbox_watcher_<role>.log`; check `dispatcher.log` for spawn errors |
| handoff atom present but no next envelope | consumer loop (#1339 oevr) not running OR `advance_step` errored | check oevr consumer logs; `jq . /tmp/v1_chain_state.json` — was state mutated? |
| 4 envelopes, no chain_complete post | parallel fan-out didn't both complete OR `_post_chain_complete` errored | confirm both `orion_spec` and `atlas_safety` in `steps_done`; tail dispatcher.log for `chain_complete` |
| #ceo got intermediate post(s) | nd3b suppression broken | grep `dispatcher.log` for `task_complete: SUPPRESSED` count; expect 5, got <5 |

### 5.8 Double-post on #ceo (chain_complete + a stray task_complete)

nd3b's suppression branch didn't recognise the `chain_step`. Usually a naming mismatch (see Agency_OS-qjl7 second-opinion bd comment): the agent set the env under one name and `dispatcher_task_complete` reads another. Confirm both sides use the same form (recommend `AGENT_CHAIN_STEP`).

### 5.9 Cost shows `A$0.0000` in the chain_complete post

`attribution/logger.py` has no rows for this `task_id` yet (race) OR the per-task→AUD conversion misfired. Re-query attribution by `task_id` directly:
```bash
psql "$DATABASE_URL" -c "SELECT * FROM attribution_log WHERE task_id = '<task_id>';"
```
Sum `total_cost_usd * 1.55` should match the posted A$. If attribution rows are missing, the agents didn't attribute their runs — a separate fix.

---

## §6 — Rollback / abort a stuck chain

If the chain is stalled and Dave needs the system back to a clean state, run in this order:

```bash
# 1. Quote-and-stop the stuck chain envelope (so it does not auto-retry on restart)
CHAIN_ID="<chain_id-from-state-file>"
jq "del(.\"$CHAIN_ID\")" /tmp/v1_chain_state.json > /tmp/v1_chain_state.json.new \
  && mv /tmp/v1_chain_state.json.new /tmp/v1_chain_state.json

# 2. Mark the task complete in public.tasks so the work-loop does not re-enqueue
psql "$DATABASE_URL" -c "UPDATE public.tasks SET status='dismissed' WHERE id = '<task_id>';"

# 3. Drain any per-callsign tmux pane that is sitting on a stuck dispatch
for cs in aiden max nova orion atlas; do
  tmux send-keys -t "${cs}:0.0" "/clear" Enter
done

# 4. If a role agent is genuinely hung (not just idle), kill it via the dispatcher
curl -X POST http://127.0.0.1:4001/dispatcher/terminate \
  -H 'Content-Type: application/json' \
  -d '{"key": "<dispatcher-key-of-the-stuck-spawn>"}'

# 5. Post a one-line plain-English #ceo note that the rehearsal was aborted
python3 /home/elliotbot/clawd/Agency_OS/scripts/slack_relay.py -c ceo \
  "Dress rehearsal aborted for chain $CHAIN_ID — investigating."
```

After rollback, re-run §1 pre-flight before any retry. Do NOT re-trigger the same `task_id` — generate a fresh one (Path 2.B / 2.C accept arbitrary briefs).

---

## §7 — Sign-off

The dress rehearsal counts as PASSED when:

1. Path 2.A is used (Slack-origin leg covered).
2. All §1 pre-flight items were ✅ at the start.
3. All §4 success signals (primary + every secondary) fired in order.
4. Dave acknowledges the #ceo post in writing (per the Dave-sign-off requirement on Agency_OS-jb4e).

Any one of (1)–(4) missing → rehearsal does not pass; file a follow-up KEI with the specific gap.

---

## Appendix — components on origin/main + open dependencies

**On `origin/main`:**
- `src/keiracom_system/chat/face.py` (#1311) — Face entrypoint, publishes `keiracom.dispatch.aiden`.
- `src/keiracom_system/chain/v1_chain_orchestrator.py` — `dispatch` + `advance_step` state machine.
- `src/keiracom_system/vault/agent_cold_start.py` — `notify_complete` + `_publish_handoff` (#1296+).
- `src/dispatcher/main.py` — `/dispatcher/spawn`, `/dispatcher/task_complete` (post-#1337 with chain_step suppression).
- `src/keiracom_system/work_loop/{bridge,consumer}.py` — Postgres → Valkey → /dispatcher/spawn.
- `src/keiracom_system/attribution/logger.py` — per-task cost (source of truth for chain_complete cost).
- `scripts/ceo_capture_listener.py` — `TASK:` parser (Path 2.A).

**Open dependencies (must merge before run):**
- PR **#1339** (Atlas) — `oevr` consumer loop wiring `keiracom.agent.handoff` → `advance_step`.
- PR **#1340** (Nova) — `zqni` `_post_chain_complete` helper + `/dispatcher/chain_complete` endpoint.

When both land, walk §1 → §2 → §3 → §4 in that order.
