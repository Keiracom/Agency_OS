# Callback Bridge Spec — EVO-003
# Author: architect-0 (Opus) | Date: 2026-04-04

## Purpose
Close the one-way Prefect → Elliottbot gap. Prefect flows write completion
events to Supabase; Elliottbot polls and reacts without any networking changes.

## Table: evo_flow_callbacks
See T3 for CREATE TABLE SQL. Key columns:
- flow_name, flow_run_id, deployment_id — identifies the flow
- status: completed | failed | crashed
- result_summary (jsonb) — task results, error details, verification evidence
- consumed_at / consumed_by — pickup tracking (NULL = unclaimed)

## Write Path (Prefect → Supabase)
Prefect on_completion/on_failure hooks call write_flow_callback() in
src/prefect_utils/callback_writer.py, which POSTs to Supabase REST API
using SUPABASE_URL + SUPABASE_SERVICE_KEY from environment.

## Poll Path (Elliottbot cron → Supabase)
OpenClaw cron fires every 60 seconds, runs src/evo/callback_poller.py:
  SELECT * FROM evo_flow_callbacks WHERE consumed_at IS NULL
  ORDER BY created_at ASC LIMIT 5

## Atomic Pickup (prevents double-processing)
  UPDATE evo_flow_callbacks
  SET consumed_at = now(), consumed_by = '<agent_id>'
  WHERE id = <row_id> AND consumed_at IS NULL
  RETURNING *
Only proceeds if RETURNING returns a row (lost-update safe).

## Response Actions
- status = completed → format completion report, send Telegram to Dave
- status = failed/crashed → call send_failure_alert() from failure_alert.py

## Stale Row Handling
Rows with consumed_at still NULL after 24h → alert Dave, mark
consumed_by = 'elliottbot:stale-sweep' to prevent re-alert on next poll.

## Offline Resilience
Rows persist in Supabase indefinitely. If Elliottbot is offline, the
poller catches up in created_at order on next run. No data is lost.
