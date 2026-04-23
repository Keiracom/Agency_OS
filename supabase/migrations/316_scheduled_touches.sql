-- Migration 316: scheduled_touches — pending outreach touches fired by hourly_cadence_flow
--
-- Each row is one pre-planned touch for a lead. The hourly cadence flow
-- (src/orchestration/flows/hourly_cadence_flow.py) selects pending rows
-- where scheduled_at <= now() and runs them through OutreachDispatcher.
-- The CadenceDecisionTree (src/outreach/cadence/decision_tree.py) may
-- mutate rows in response to inbound reply events (cancel/pause/reschedule).

CREATE TABLE IF NOT EXISTS scheduled_touches (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id      UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id        UUID NOT NULL,
    campaign_id    UUID,
    channel        TEXT NOT NULL,
    prospect       JSONB NOT NULL DEFAULT '{}'::jsonb,
    content        JSONB DEFAULT '{}'::jsonb,
    sequence_step  INT  NOT NULL DEFAULT 1,
    scheduled_at   TIMESTAMPTZ NOT NULL,
    status         TEXT NOT NULL DEFAULT 'pending'
                   CHECK (status IN ('pending','sent','failed','skipped','cancelled','paused')),
    -- Dispatch outcome fields populated by hourly_cadence_flow
    dispatched_at       TIMESTAMPTZ,
    skipped_reason      TEXT,
    failure_reason      TEXT,
    provider_message_id TEXT,

    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The hot query — pending rows due now, oldest first
CREATE INDEX IF NOT EXISTS idx_sched_touches_due
    ON scheduled_touches (status, scheduled_at)
    WHERE status = 'pending';

-- Reply-driven mutations look up by lead
CREATE INDEX IF NOT EXISTS idx_sched_touches_lead
    ON scheduled_touches (lead_id);

-- Campaign-level reporting
CREATE INDEX IF NOT EXISTS idx_sched_touches_campaign
    ON scheduled_touches (campaign_id) WHERE campaign_id IS NOT NULL;

-- Row Level Security — clients see their own rows; service role full access
ALTER TABLE scheduled_touches ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS scheduled_touches_client_select ON scheduled_touches;
CREATE POLICY scheduled_touches_client_select
    ON scheduled_touches FOR SELECT
    USING (client_id = auth.uid() OR auth.role() = 'service_role');

DROP POLICY IF EXISTS scheduled_touches_service_write ON scheduled_touches;
CREATE POLICY scheduled_touches_service_write
    ON scheduled_touches FOR ALL
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

COMMENT ON TABLE scheduled_touches IS
    'Pending outreach touches for hourly_cadence_flow. CadenceDecisionTree mutates on inbound reply events.';
COMMENT ON COLUMN scheduled_touches.status IS
    'pending -> sent/failed/skipped by dispatcher; cancelled/paused by decision_tree';
