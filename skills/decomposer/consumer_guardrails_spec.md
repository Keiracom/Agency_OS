# EVO-005: Task Queue Consumer + Guardrails Spec

## 1. Consumer Poll Loop
- Poll `evo_task_queue` every 10s: `SELECT * FROM evo_task_queue WHERE status='pending' ORDER BY created_at LIMIT 1`
- Atomic claim: `UPDATE evo_task_queue SET status='running', claimed_at=now() WHERE id=X AND status='pending' RETURNING *`
- If no row returned → another consumer claimed it, skip
- Spawn assigned sub-agent (via openclaw sessions_spawn) with task description
- Capture agent output; run `verification_cmd`; check expected output present
- Write to `evo_task_results`: status, agent_output, verification_output, verified, actual_cost_usd
- Update `evo_task_queue` status → 'completed' or 'failed'
- On verification failure: retry once. Second failure → tg_notify Dave, mark 'failed'

## 2. Guardrail: API Call Tracking
- Wrap outbound HTTP via a counting proxy (httpx transport hook or middleware)
- Tracked domains: `api.dataforseo.com` (dfs), `api.anthropic.com` (anthropic), `api.brightdata.com` (brightdata)
- All other external HTTP → `external_http` bucket
- Counts stored in-memory dict per task execution, flushed to `evo_task_results.actual_cost`

## 3. Budget Check Logic
- Each task carries `estimated_cost.api_calls` (set by decomposer)
- After each tracked call: compare actual vs estimated per domain
- If ANY domain actual > estimated × 1.2 → PAUSE execution
- Send Telegram: "⚠️ Task {id} budget exceeded — {domain}: {actual}/{estimated}. Reply GO or STOP"
- Poll `evo_auth_requests` for response (max 30 min timeout)
- GO → raise ceiling 50% (new limit = estimated × 1.8), resume
- STOP → terminate task, mark failed, log reason

## 4. Auth Flow: Option B Recommended (Supabase flag table)
**Why not Option A (inline buttons)?** Requires Telegram bot webhook/callback handler infra we don't have. New surface area, new failure mode.
**Why Option B?** We already have the pattern: callback_poller.py polls Supabase rows. Consumer writes `evo_auth_requests` row, tg_notify sends human-readable alert. Dave replies in Telegram; Elliottbot parses "GO"/"STOP", writes response to same row. Consumer polls row for `response` field. Zero new infra — just one new table + tg_notify message.

## 5. New Tables
**evo_auth_requests:** id (uuid), task_id (text), flow_run_id (text), reason (text), request_type (text: 'budget_exceeded'|'verification_failed'), requested_at (timestamptz), response (text: null|'go'|'stop'), responded_at (timestamptz)
**Schema extension to evo_task_queue:** add `estimated_cost` (jsonb) column
**Schema extension to evo_task_results:** add `actual_cost` (jsonb) column

## 6. File Map (T2–T5)
| Task | File | Description |
|------|------|-------------|
| T2 | `src/evo/task_consumer.py` | Poll loop, claim, spawn, verify, result write |
| T2 | `src/evo/cost_tracker.py` | HTTP call counting middleware + budget check |
| T3 | `src/evo/auth_gate.py` | Write auth request, poll for response, timeout |
| T3 | `migrations/005_consumer_tables.sql` | New tables + column additions |
| T4 | Update `skills/decomposer/SKILL.md` | Add estimated_cost block to decomposition step |
| T5 | `tests/test_consumer.py` | Unit tests for claim, tracking, budget, auth |
