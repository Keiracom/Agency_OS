-- KEI-136 — Claim-queue observability view.
--
-- Read-only view over public.tasks exposing the metrics that the periodic
-- exporter (scripts/orchestrator/claim_queue_metrics_export.py) needs to
-- decide whether to ping the Better Stack heartbeat or skip (stall alert).
--
-- Post-KEI-150: equal-worker model — no per-clone queues, so the metrics are
-- single-row aggregates over public.tasks.
--
-- Columns:
--   available_count            — open work waiting to be claimed
--   active_count               — claimed + in-progress
--   blocked_count              — depends_on unresolved
--   oldest_available_age_sec   — NOW() − MIN(created_at) over available rows
--   oldest_active_age_sec      — NOW() − MIN(claimed_at) over active rows
--   max_idle_seconds           — NOW() − MIN(heartbeat_at) over active rows
--                                (i.e. longest time since any active task heartbeat)
--   computed_at                — server timestamp for staleness checks

CREATE OR REPLACE VIEW public.claim_queue_metrics_v AS
SELECT
    COUNT(*) FILTER (WHERE status = 'available')                  AS available_count,
    COUNT(*) FILTER (WHERE status = 'active')                     AS active_count,
    COUNT(*) FILTER (WHERE status = 'blocked')                    AS blocked_count,
    EXTRACT(EPOCH FROM (NOW() - MIN(created_at)
        FILTER (WHERE status = 'available')))::bigint              AS oldest_available_age_sec,
    EXTRACT(EPOCH FROM (NOW() - MIN(claimed_at)
        FILTER (WHERE status = 'active' AND claimed_at IS NOT NULL)))::bigint
                                                                   AS oldest_active_age_sec,
    EXTRACT(EPOCH FROM (NOW() - MIN(heartbeat_at)
        FILTER (WHERE status = 'active' AND heartbeat_at IS NOT NULL)))::bigint
                                                                   AS max_idle_seconds,
    NOW()                                                          AS computed_at
FROM public.tasks;

COMMENT ON VIEW public.claim_queue_metrics_v IS
    'KEI-136 — single-row aggregate of claim-queue state for Better Stack heartbeat export. NULLs in age columns mean no rows in the corresponding status bucket.';
