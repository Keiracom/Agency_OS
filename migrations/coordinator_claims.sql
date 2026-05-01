-- migrations/coordinator_claims.sql
-- GOV-PHASE1-TRACK-B / B2 — shared-state claims table for inter-bot coordination.
-- Used by src/governance/coordinator.py to enforce R2 (Claim-Before-Commit) +
-- Claim-Before-Touch shared-files rule.

CREATE TABLE IF NOT EXISTS public.coordinator_claims (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    callsign      text        NOT NULL,                       -- 'elliot' | 'aiden' | 'orion' | 'atlas'
    action        text        NOT NULL,                       -- 'commit' | 'dispatch' | 'shared-file-edit' | 'watcher'
    target_path   text        NOT NULL,                       -- file path / branch / watcher subject
    claimed_at    timestamptz NOT NULL DEFAULT now(),
    released_at   timestamptz,                                -- NULL while active
    status        text        NOT NULL DEFAULT 'active',      -- 'active' | 'released' | 'expired'
    expires_at    timestamptz NOT NULL DEFAULT now() + interval '5 minutes',
    metadata      jsonb,                                      -- arbitrary context (commit SHA, dispatch ID, etc.)
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- Active-claim lookup index — most reads filter by status + target.
CREATE INDEX IF NOT EXISTS idx_coordinator_claims_active
    ON public.coordinator_claims (target_path, action)
    WHERE status = 'active';

-- Per-callsign filter for "what is bot X currently holding?"
CREATE INDEX IF NOT EXISTS idx_coordinator_claims_callsign
    ON public.coordinator_claims (callsign, status);

-- Realtime publication: bots subscribe via Supabase Realtime to this table
-- so peer-claim posts are seen instantly without polling.
ALTER PUBLICATION supabase_realtime ADD TABLE public.coordinator_claims;

-- Safety: ensure status enum-style values only.
ALTER TABLE public.coordinator_claims
    DROP CONSTRAINT IF EXISTS coordinator_claims_status_chk;
ALTER TABLE public.coordinator_claims
    ADD  CONSTRAINT coordinator_claims_status_chk
    CHECK (status IN ('active', 'released', 'expired'));

-- Action enum-style.
ALTER TABLE public.coordinator_claims
    DROP CONSTRAINT IF EXISTS coordinator_claims_action_chk;
ALTER TABLE public.coordinator_claims
    ADD  CONSTRAINT coordinator_claims_action_chk
    CHECK (action IN ('commit', 'dispatch', 'shared-file-edit', 'watcher', 'merge'));
