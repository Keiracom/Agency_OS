-- Fleet liveness status view — Dave-gate read contract on top of Scout's
-- append-only public.fleet_liveness history (migration
-- 20260602_fleet_liveness.sql, commit bb1e7a950).
--
-- Dave's fleet_check_query is:
--     SELECT callsign, status FROM public.fleet_liveness_status ORDER BY callsign;
--
-- The base table is observability ground truth — append-only with raw signals
-- (tmux_alive, nats_last_publish_at, backend_health, active_task_id). The
-- GREEN/RED/UNKNOWN classification belongs at the read-side so the history
-- stays untouched and re-classification is a view swap, not a backfill.
--
-- Status rules:
--   GREEN   — most-recent row has tmux_alive=TRUE AND checked_at within 10 min
--   RED     — most-recent row has tmux_alive=FALSE AND checked_at within 10 min
--             (agent observed dead by the checker, not just stale)
--   UNKNOWN — most-recent row is older than 10 min (or no row at all — the
--             callsign falls out of DISTINCT ON entirely in that case)
--
-- 10-min staleness window matches the 5-min checker cadence + 1 cycle of slack
-- (a single missed run does not flip to UNKNOWN; two consecutive misses do).
--
-- Authored by ORION (dispatch from Elliot 2026-06-02). Sibling to Scout's
-- 20260602_fleet_liveness.sql; does NOT modify the table.

CREATE OR REPLACE VIEW public.fleet_liveness_status AS
SELECT DISTINCT ON (callsign)
    callsign,
    CASE
        WHEN tmux_alive AND checked_at > NOW() - INTERVAL '10 min' THEN 'GREEN'
        WHEN checked_at > NOW() - INTERVAL '10 min' THEN 'RED'
        ELSE 'UNKNOWN'
    END AS status,
    checked_at AS last_seen
FROM public.fleet_liveness
ORDER BY callsign, checked_at DESC;

COMMENT ON VIEW public.fleet_liveness_status IS
    'Latest GREEN/RED/UNKNOWN classification per callsign computed from '
    'public.fleet_liveness. Read by Dave fleet_check_query; classification '
    'rules in 20260602_fleet_liveness_status_view.sql header.';
