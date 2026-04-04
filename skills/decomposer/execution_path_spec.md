# EVO-007 Execution Path Spec

## 1. Responsibility Split
- **Railway (Prefect)**: Orchestrate only. Write task to `evo_task_queue`, poll `evo_task_results` for outcome. Never invoke agents.
- **VPS (task_consumer)**: Sole executor. Claim row → spawn sub-agent locally → run verification → write result to `evo_task_results`.

## 2. Queue Protocol
### Railway side (writer + poller)
1. INSERT into `evo_task_queue` with status=`pending`, fields: task_id, agent_id, description, flow_run_id, verification_cmd, expected_output.
2. Poll `evo_task_results` WHERE task_id=X AND flow_run_id=Y every 10s, timeout 600s.

### VPS side (claimer + executor)
1. SELECT from `evo_task_queue` WHERE status=`pending` ORDER BY created_at LIMIT 1.
2. UPDATE status=`claimed` (atomic; skip if already claimed).
3. Invoke agent locally (see §3). Run verification command. Write result row to `evo_task_results`.
4. UPDATE queue row status to `completed` or `failed`.

## 3. Invocation Method: `openclaw agent` CLI (Option A)
**Evidence**: `openclaw agent --agent <id> --local --message "<prompt>" --json --timeout 120` returns JSON with agent reply including `text` field. Tested on VPS — exit 0, reply "PONG" in ~15s.
**Why not Option B (HTTP gateway)**: `/api/sessions` returns 404; no spawn endpoint exposed.
**Why not Option C (Python import)**: No Python SDK; OpenClaw is Node/TS.

### Invocation template
```
openclaw agent --agent <agent_id> --local --message "<description>" --json --timeout 300
```
Parse `text` from JSON stdout. Non-zero exit = agent failure.

## 4. Timeout / Retry
| Parameter | Value |
|---|---|
| Railway poll timeout | 600s |
| Railway poll interval | 10s |
| VPS agent timeout | 300s |
| VPS retries | 1 (re-invoke on verification fail) |
| Budget gate | check_budget() before retry; request_authorisation() if >120% |

## 5. File Map (T2–T4)
| Task | File | Change |
|---|---|---|
| T2 | `src/evo/agent_invoker.py` | Strip to write-queue + poll-results only (remove agent call) |
| T2 | `src/evo/task_executor.py` | DELETE — logic moves into consumer |
| T3 | `src/evo/task_consumer.py` | Rewrite: claim → `openclaw agent` subprocess → verify → write result |
| T3 | `src/evo/consumer_helpers.py` | Add `invoke_agent_local()` using subprocess |
| T4 | `src/evo/flow_builder.py` | Update to use new invoker (no execute_task import) |
