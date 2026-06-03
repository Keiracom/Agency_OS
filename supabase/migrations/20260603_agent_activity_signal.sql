-- agent_activity_signal — per-agent fine-grained activity from public.tool_call_log.
--
-- Bug this exists to fix: fleet_liveness_status today reads one aggregate
-- sweep timestamp (fleet_liveness.checked_at written by the on-box checker
-- every 5 min) and stamps every callsign with it. Two agents with NO actual
-- tool-call activity for ~50 min (nova + scout observed 2026-06-03 11:25 UTC)
-- still showed GREEN because the aggregate sweep timestamp was fresh.
--
-- agent_activity_signal aggregates tool_call_log per callsign so the status
-- view can JOIN it and emit RED for any agent that hasn't actually done
-- anything in the last 10 minutes — independent of whether the tmux pane
-- still exists.
--
-- Dispatched by Elliot 2026-06-03 ref: scout-agent-activity-signal.

CREATE OR REPLACE VIEW public.agent_activity_signal AS
SELECT
    callsign,
    MAX(started_at) AS last_tool_call,
    COUNT(*) FILTER (WHERE started_at > NOW() - INTERVAL '10 minutes') AS calls_last_10m,
    CASE
        WHEN COUNT(*) FILTER (WHERE started_at > NOW() - INTERVAL '10 minutes') = 0 THEN 'idle'
        ELSE 'active'
    END AS activity_state
FROM public.tool_call_log
GROUP BY callsign;

COMMENT ON VIEW public.agent_activity_signal IS
    'Per-agent activity rollup over public.tool_call_log. activity_state = '
    '"active" when ≥1 tool call landed in the last 10 minutes; "idle" otherwise. '
    'Source of truth for fleet_liveness_status''s per-agent RED/GREEN decision. '
    'Caller does not need to call any compact function — this view IS the per-call '
    'signal, NOT a sweep aggregate.';

-- Replace fleet_liveness_status to JOIN agent_activity_signal so the per-agent
-- activity decision becomes a first-class column AND drives RED/GREEN. Old
-- behaviour preserved: tmux_dead = RED (highest precedence — process gone),
-- callsign_match=false = MISMATCH, then activity_state='idle' = RED, only
-- tmux_alive AND active = GREEN. UNKNOWN unchanged.
--
-- IMPORTANT for CREATE OR REPLACE VIEW: existing column names/positions are
-- frozen. We keep the original 5 columns (callsign, status, last_seen,
-- reported_callsign, callsign_match) and APPEND last_tool_call,
-- activity_state, calls_last_10m at the end. `last_seen` continues to be
-- fl.checked_at (the on-box-checker sweep) — its meaning is unchanged; the
-- NEW signals are the appended columns, which is where consumers should
-- read activity from going forward.
CREATE OR REPLACE VIEW public.fleet_liveness_status AS
SELECT DISTINCT ON (fl.callsign)
    fl.callsign,
    CASE
        WHEN NOT fl.tmux_alive AND fl.checked_at > NOW() - INTERVAL '15 min' THEN 'RED'
        WHEN fl.callsign_match = FALSE AND fl.checked_at > NOW() - INTERVAL '15 min' THEN 'MISMATCH'
        WHEN COALESCE(aas.activity_state, 'idle') = 'idle'
             AND fl.tmux_alive
             AND fl.checked_at > NOW() - INTERVAL '15 min' THEN 'RED'
        WHEN fl.tmux_alive
             AND aas.activity_state = 'active'
             AND fl.checked_at > NOW() - INTERVAL '15 min' THEN 'GREEN'
        WHEN fl.checked_at > NOW() - INTERVAL '15 min' THEN 'RED'
        ELSE 'UNKNOWN'
    END AS status,
    fl.checked_at AS last_seen,
    fl.reported_callsign,
    fl.callsign_match,
    aas.last_tool_call,
    COALESCE(aas.activity_state, 'no_data') AS activity_state,
    aas.calls_last_10m
FROM public.fleet_liveness fl
LEFT JOIN public.agent_activity_signal aas
       ON aas.callsign = fl.callsign
ORDER BY fl.callsign, fl.checked_at DESC;

COMMENT ON VIEW public.fleet_liveness_status IS
    'Per-callsign liveness. RED when tmux dead OR activity_state=idle (no tool '
    'calls in 10m) — fixes the aggregate-sweep bug where two agents idle '
    '~50min still showed GREEN because fleet_liveness.checked_at was fresh. '
    'MISMATCH when CALLSIGN env differs from session name. UNKNOWN when no '
    'checker row in the last 15 min. The idle_with_work_queued state (idle + '
    'pending file in /tmp/telegram-relay-<callsign>/inbox/) is computed by '
    'scripts/orchestrator/agent_activity.py — a filesystem signal a SQL view '
    'cannot read directly.';

-- gate_roadmap row: agent_activity_signal, phase 0_foundation, scout-built,
-- status=built. Scout's session sets agency_os.callsign=scout so the
-- fn_gate_roadmap_capture_builder trigger captures scout as builder. Aiden+Max
-- must attest before proven (fn_gate_proven_dual_attest); scout cannot
-- self-attest (fn_gate_proof_no_self_attest).
-- Note: the migration runs as the supabase migration role, which does NOT
-- set agency_os.callsign. We INSERT with status=not_started + explicit
-- built_by_callsign=NULL, then scout flips status=built from the worktree
-- session post-merge (where the session var is set correctly).
-- The migration is idempotent (ON CONFLICT DO NOTHING via component+phase).
INSERT INTO public.gate_roadmap (component, phase, status, proof_gate, blocker_text)
SELECT 'agent_activity_signal', '0_foundation', 'not_started',
       'fleet_liveness_status RED for any agent with 0 tool_call_log rows in last 10 min, GREEN only when activity_state=active; idle_with_work_queued state computable via scripts/orchestrator/agent_activity.py for the existing watchdog to consume',
       'View + fleet_liveness_status JOIN landed; flip status=built from scout''s session + idle_with_work_queued helper present at scripts/orchestrator/agent_activity.py. Aiden+Max dual-attest required for proven (scout cannot self-attest).'
WHERE NOT EXISTS (
    SELECT 1 FROM public.gate_roadmap WHERE component = 'agent_activity_signal'
);
