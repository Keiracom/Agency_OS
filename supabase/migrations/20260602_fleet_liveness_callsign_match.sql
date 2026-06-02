-- Fleet liveness — callsign-mismatch detection (P0 scoreboard fix).
--
-- Extends public.fleet_liveness with two columns capturing the CALLSIGN env
-- var actually exported in the agent's tmux pane process tree, plus a boolean
-- match flag. The on-box checker (scripts/orchestrator/fleet_liveness_checker.py)
-- populates these by walking the pane leader PID and its descendants reading
-- /proc/<pid>/environ. This catches the bug class where an agent runs under
-- the wrong identity (e.g. Max process exporting CALLSIGN=atlas) without any
-- crash — invisible until manual diagnosis.
--
-- Also rewrites public.fleet_liveness_status to emit a new 'MISMATCH' status
-- so the Dave fleet_check_query reports identity drift as a first-class fault
-- alongside RED (tmux dead) and GREEN (alive + matching).
--
-- Authored by SCOUT (dispatch from Elliot 2026-06-02, P0 scoreboard fix).
-- Sibling to 20260602_fleet_liveness.sql + 20260602_fleet_liveness_status_view.sql.

ALTER TABLE public.fleet_liveness
    ADD COLUMN IF NOT EXISTS reported_callsign TEXT,
    ADD COLUMN IF NOT EXISTS callsign_match BOOLEAN;

COMMENT ON COLUMN public.fleet_liveness.reported_callsign IS
    'CALLSIGN env var observed in the agent''s tmux pane process tree. NULL '
    'when the pane has no readable child or no descendant exports CALLSIGN.';

COMMENT ON COLUMN public.fleet_liveness.callsign_match IS
    'TRUE when reported_callsign equals the expected callsign, FALSE when '
    'they differ, NULL when reported_callsign is NULL (cannot decide).';

-- Replace the status view to surface MISMATCH ahead of GREEN so identity
-- drift on an otherwise-alive agent gets flagged. Order matters: a tmux-dead
-- agent stays RED (status is determined before callsign_match is consulted).
CREATE OR REPLACE VIEW public.fleet_liveness_status AS
SELECT DISTINCT ON (callsign)
    callsign,
    CASE
        WHEN NOT tmux_alive AND checked_at > NOW() - INTERVAL '10 min' THEN 'RED'
        WHEN callsign_match = FALSE AND checked_at > NOW() - INTERVAL '10 min' THEN 'MISMATCH'
        WHEN tmux_alive AND checked_at > NOW() - INTERVAL '10 min' THEN 'GREEN'
        WHEN checked_at > NOW() - INTERVAL '10 min' THEN 'RED'
        ELSE 'UNKNOWN'
    END AS status,
    checked_at AS last_seen,
    reported_callsign,
    callsign_match
FROM public.fleet_liveness
ORDER BY callsign, checked_at DESC;

COMMENT ON VIEW public.fleet_liveness_status IS
    'Latest GREEN/RED/MISMATCH/UNKNOWN classification per callsign computed '
    'from public.fleet_liveness. Read by Dave fleet_check_query. MISMATCH '
    'fires when an alive agent reports a CALLSIGN env var that differs from '
    'the expected callsign — catches identity drift bugs that were previously '
    'invisible (anchor: Max-running-as-Atlas incident).';
