# Dynamic Prefect Flow Generator — Design Spec
# Author: architect-0 (Opus) | T1 of EVO-004 | 2026-04-04

## Architecture Overview
The flow generator dynamically constructs a Prefect flow from a JSON task graph.
It parses task dependencies into `wait_for` chains, launches dependency-free tasks
in parallel, invokes sub-agents via Supabase task queue (Option C), runs verification
gates, retries once on failure, and writes results to `evo_flow_callbacks` on completion.

## Input Schema
```json
{"objective":"string","tasks":[{"id":"T1","description":"string",
"agent":"research-1","dependencies":[],"verification":{"command":"str",
"expected":"str"},"complexity":"low"}]}
```

## Invocation Method — Option C: Supabase Task Queue
Prefect writes row to `evo_task_queue` (agent, description, flow_run_id).
Elliottbot cron polls queue, spawns sub-agent, writes result to `evo_task_results`.
Prefect polls `evo_task_results` until complete or timeout (300s).
**Why C:** decoupled, resilient (survives restarts), consistent with callback_bridge
pattern, zero new infra. A/B rejected: no confirmed CLI; gateway API schema unknown.

## Dependency Resolution
1. Build adjacency map `{task_id: [upstream_ids]}` from `dependencies` field.
2. Each task becomes `@task(retries=1)` Prefect task function.
3. Empty-dependency tasks submit immediately (parallel via task runner).
4. Tasks with deps pass upstream Prefect futures via `wait_for=[...]`.
5. Cycle detection: topological sort pre-check; raise on cycle.

## Verification Gate Pattern
After sub-agent result returns, run `verification.command` via `subprocess.run`.
Compare stdout against `verification.expected` (substring match). Pass → record.
Fail → Prefect retry (retries=1). Second fail → raise → on_failure hook.
Evidence (stdout/stderr) attached to task result dict.

## Output / Callback Pattern
- **on_completion:** `write_flow_callback(status="completed", result_summary={...})`.
- **on_failure:** `write_flow_callback(status="failed", result_summary={...})`.
Both use existing `src/prefect_utils/callback_writer.py`.

## File Map (T2–T4 deliverables)
| File | Owner | Purpose |
|------|-------|---------|
| `src/evo/flow_generator.py` | T2 | Core: parse graph, build flow, submit |
| `src/evo/agent_invoker.py` | T2 | Write to evo_task_queue, poll result |
| `supabase/migrations/evo_task_queue.sql` | T3 | CREATE TABLE evo_task_queue + evo_task_results |
| `src/evo/callback_poller.py` | T3 | Poll evo_flow_callbacks (exists, extend) |
| `tests/test_flow_generator.py` | T4 | Unit tests for graph parse + dep resolution |
