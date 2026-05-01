-- Governance Phase 1 Track A — A1 Recorder
-- Append-only event log for PreToolUse hook recordings, store-write
-- evidence, and gate decisions. Insert-only by design: the Gatekeeper
-- relies on this table being immutable so completion-claim audits cannot
-- be silently rewritten.

CREATE TABLE IF NOT EXISTS public.governance_events (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign      text NOT NULL,
    event_type    text NOT NULL,
    event_data    jsonb,
    tool_name     text,
    file_path     text,
    timestamp     timestamptz NOT NULL DEFAULT now(),
    directive_id  text
);

CREATE INDEX IF NOT EXISTS governance_events_directive_idx
    ON public.governance_events (directive_id, timestamp DESC)
    WHERE directive_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS governance_events_callsign_ts_idx
    ON public.governance_events (callsign, timestamp DESC);

CREATE INDEX IF NOT EXISTS governance_events_event_type_idx
    ON public.governance_events (event_type, timestamp DESC);

-- Append-only: revoke UPDATE / DELETE from every role that can see the
-- table. INSERT + SELECT remain available to authenticated + service
-- roles. Future migrations that need to rewrite history must do so via
-- a tombstone event, not a DELETE.
REVOKE UPDATE, DELETE, TRUNCATE ON public.governance_events FROM PUBLIC;
REVOKE UPDATE, DELETE, TRUNCATE ON public.governance_events FROM anon;
REVOKE UPDATE, DELETE, TRUNCATE ON public.governance_events FROM authenticated;
REVOKE UPDATE, DELETE, TRUNCATE ON public.governance_events FROM service_role;

GRANT INSERT, SELECT ON public.governance_events TO anon;
GRANT INSERT, SELECT ON public.governance_events TO authenticated;
GRANT INSERT, SELECT ON public.governance_events TO service_role;

COMMENT ON TABLE public.governance_events IS
    'Append-only governance event log (Recorder, Gatekeeper, store-write evidence). UPDATE/DELETE revoked.';
