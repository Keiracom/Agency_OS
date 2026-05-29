# Work-Loop Wire — Single Shared Interface

**Owner:** Atlas (producer/consumer) · **Consumed by:** Scout (#1279 dress-rehearsal Slack-origin step)
**Status:** Canonical interface contract — Atlas's bridge + Scout's test build against THIS, not two divergent half-pipes (Dave seam-risk flag, 2026-05-29).

One wire, one row schema, one queue payload. Do not invent a second.

---

## The wire (entry → spawn)

```
Dave #ceo message ──[CEO]prefix──▶ central_listener._create_kei_via_linear
                                      └▶ Linear issueCreate ──webhook──▶ src/api/webhooks/linear.py _dispatch_to_tasks
                                                                            └▶ INSERT public.tasks (status='available')
public.tasks INSERT(status='available') ──▶ kei45_emit_task_event trigger ──▶ pg_notify('task_event', …)
   ──▶ work_loop/bridge.py (LISTEN task_event, filter new_available) ──▶ PUBLISH keiracom:tasks:available
   ──▶ work_loop consumer (admit under tenant ceiling) ──▶ POST /dispatcher/spawn ──▶ container spawn
```

## ⚠️ Entry-point reality (Dave's critical-unknown — CONFIRMED + FLAGGED)

- The dedicated **#ceo CAPTURE listeners do NOT create task rows.** Nova #1268 `exit_cycle.classify_and_save` and Scout #1270 `ceo_capture_listener` write **DECISIONS to `public.ceo_memory`** (→ atomization → Hindsight). They are **not** the task-creation path. *(Confirmed: `src/keiracom_system/chat/exit_cycle.py:195` → `ceo_memory_writer`; `scripts/ceo_capture_listener.py:103` → ceo_memory only.)*
- The **only** Slack→task-row path is the **`[CEO]`-prefix → Linear → Linear-webhook** route (`src/slack_bot/central_listener.py:470` → Linear `issueCreate` → `src/api/webhooks/linear.py:276` `_dispatch_to_tasks` → `INSERT … status='available'`). It is **indirect** (via Linear, ~1–3 s eventual-consistency) and **conditional** on (a) the `[CEO]` prefix and (b) the Linear webhook being live.
- **SEAM FLAG:** the loop's Slack entry is **not missing, but it is gated** on the `[CEO]` prefix + a live Linear webhook. A plain (un-prefixed) #ceo message becomes a *decision in memory*, **not** an actionable task row. If "Dave's daily input auto-creates tasks" is the goal, decide: keep the `[CEO]`-prefix+Linear convention, or add a direct Slack→`public.tasks` creator. Today, non-`[CEO]` input does NOT enter the loop — only `[CEO]`/Linear/GitHub webhooks + manual inserts do.

## Row schema — `public.tasks` (fields the wire reads)

| column | type | role in the wire |
|---|---|---|
| `id` | TEXT PK (supplied) | → `task_id` / spawn `key` |
| `title` | TEXT NOT NULL | → `brief` (feeds spawn-recall) |
| `status` | TEXT | **MUST be `'available'`** — the kei45 trigger fires `new_available` only on INSERT with this status |
| `priority` | INT (default 2) | passed through |
| `claimed_by` | TEXT (nullable) | → `callsign` (fallback `worker`) |
| `tags` | TEXT[] (nullable) | → `task_type` (first of `build`/`review`/`research`/`devops`, else `build`) |
| `tenant_id` | TEXT (default `internal`) | **ignored in Phase-1** — bridge stamps `FLEET_TENANT_ID` env instead |

## Queue payload — `keiracom:tasks:available` (the bridge → consumer contract)

```json
{
  "task_id": "<tasks.id>",
  "tenant_id": "<FLEET_TENANT_ID env>",
  "backend": "container",
  "spawn_kwargs": {
    "callsign": "<claimed_by or 'worker'>",
    "task_id": "<tasks.id>",
    "title": "<title>",
    "brief": "<title>",
    "task_type": "<build|review|research|devops>",
    "priority": <priority>,
    "tags": [<tags>]
  }
}
```

Consumer then POSTs `/dispatcher/spawn` `{backend, key:task_id, spawn_kwargs:{…+task_id+tenant_id}}`; the dispatcher's container-defaults injection (PR #1282) translates that to `spawn_container(image, name, port, env=AGENT_*)`.

## For Scout's #1279 Slack-origin step

- **Deterministic loop test (recommended):** seed directly — `INSERT INTO public.tasks (id, title, status) VALUES ('rehearsal-1','rehearsal','available');` — exercises trigger → bridge → consumer → spawn without Linear/webhook flakiness.
- **Full Slack-origin integration (separate check):** post a `[CEO]`-prefixed #ceo message and assert the row lands via the Linear webhook (Linear-dependent, eventual-consistency). Use this to validate the *entry* convention, not the loop mechanics.
- Recall arm: toggle `DISPATCHER_SPAWN_RECALL_ENABLED` + restart the dispatcher between recall-active and cold runs (it's a module-global, not per-task).
