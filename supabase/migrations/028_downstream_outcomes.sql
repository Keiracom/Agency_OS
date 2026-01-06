-- Migration: 028_downstream_outcomes.sql
-- Phase: 24E (Downstream Outcomes)
-- Purpose: Track meetings, deals, and full funnel outcomes for CIS learning
-- Date: 2026-01-06

-- ============================================================================
-- 1. CREATE MEETINGS TABLE
-- ============================================================================
-- The meetings table tracks scheduled meetings and their outcomes

CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,

    -- Booking info
    booked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    booked_by TEXT,  -- 'ai', 'human', 'lead'
    booking_method TEXT,  -- 'calendly', 'direct', 'phone'

    -- Meeting details
    scheduled_at TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER DEFAULT 30,
    meeting_type TEXT DEFAULT 'discovery',  -- 'discovery', 'demo', 'follow_up', 'close'
    meeting_link TEXT,
    calendar_event_id TEXT,  -- External calendar ID for sync

    -- Confirmation
    confirmed BOOLEAN DEFAULT FALSE,
    confirmed_at TIMESTAMPTZ,
    reminder_sent BOOLEAN DEFAULT FALSE,
    reminder_sent_at TIMESTAMPTZ,

    -- Attendance
    showed_up BOOLEAN,
    showed_up_confirmed_at TIMESTAMPTZ,
    showed_up_confirmed_by TEXT,  -- 'webhook', 'manual', 'calendar'
    no_show_reason TEXT,

    -- Meeting outcome
    meeting_outcome TEXT,  -- 'good', 'bad', 'rescheduled', 'no_show', 'cancelled'
    meeting_outcome_at TIMESTAMPTZ,
    meeting_notes TEXT,
    next_steps TEXT,

    -- Follow-up meeting
    follow_up_scheduled BOOLEAN DEFAULT FALSE,
    follow_up_meeting_id UUID REFERENCES meetings(id),

    -- Deal creation
    deal_created BOOLEAN DEFAULT FALSE,
    deal_id UUID,  -- Will reference deals table (circular, set after deals created)

    -- Attribution
    converting_activity_id UUID REFERENCES activities(id),
    converting_channel channel_type,
    touches_before_booking INTEGER,  -- How many touches before they booked
    days_to_booking INTEGER,  -- Days from first touch to booking

    -- Reschedule tracking
    rescheduled_count INTEGER DEFAULT 0,
    original_scheduled_at TIMESTAMPTZ,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_meeting_outcome CHECK (meeting_outcome IS NULL OR meeting_outcome IN (
        'good', 'bad', 'rescheduled', 'no_show', 'cancelled', 'pending'
    )),
    CONSTRAINT valid_meeting_type CHECK (meeting_type IN (
        'discovery', 'demo', 'follow_up', 'close', 'onboarding', 'other'
    ))
);

-- ============================================================================
-- 2. CREATE DEALS TABLE (Lightweight CRM)
-- ============================================================================

-- Create deal stage type
DO $$ BEGIN
    CREATE TYPE deal_stage_type AS ENUM (
        'qualification',
        'proposal',
        'negotiation',
        'verbal_commit',
        'contract_sent',
        'closed_won',
        'closed_lost'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create lost reason type
DO $$ BEGIN
    CREATE TYPE deal_lost_reason_type AS ENUM (
        'price_too_high',
        'chose_competitor',
        'no_budget',
        'timing_not_right',
        'no_decision',
        'champion_left',
        'project_cancelled',
        'went_silent',
        'bad_fit',
        'other'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    meeting_id UUID REFERENCES meetings(id) ON DELETE SET NULL,

    -- Deal info
    name TEXT NOT NULL,
    value DECIMAL(12,2),
    currency TEXT DEFAULT 'AUD',
    probability INTEGER DEFAULT 50,  -- 0-100% chance of closing

    -- Stage tracking
    stage deal_stage_type DEFAULT 'qualification',
    stage_changed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Expected close
    expected_close_date DATE,

    -- Outcome
    closed_at TIMESTAMPTZ,
    won BOOLEAN,
    lost_reason deal_lost_reason_type,
    lost_notes TEXT,

    -- Timing metrics
    days_in_stage INTEGER DEFAULT 0,  -- Days in current stage
    days_to_close INTEGER,  -- Total days from creation to close

    -- Attribution (which outreach created this deal)
    converting_activity_id UUID REFERENCES activities(id),
    converting_channel channel_type,
    first_touch_channel channel_type,
    touches_before_deal INTEGER,

    -- External CRM sync
    external_crm TEXT,  -- 'hubspot', 'salesforce', 'pipedrive', etc.
    external_deal_id TEXT,
    external_synced_at TIMESTAMPTZ,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT valid_probability CHECK (probability >= 0 AND probability <= 100)
);

-- ============================================================================
-- 3. CREATE DEAL STAGE HISTORY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS deal_stage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    from_stage deal_stage_type,
    to_stage deal_stage_type NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    changed_by TEXT DEFAULT 'system',  -- 'system', 'user', 'webhook', 'ai'
    days_in_previous_stage INTEGER,
    notes TEXT
);

-- ============================================================================
-- 4. ADD DEAL REFERENCE TO MEETINGS (NOW THAT DEALS EXISTS)
-- ============================================================================

-- Add foreign key constraint for deal_id in meetings
ALTER TABLE meetings DROP CONSTRAINT IF EXISTS meetings_deal_id_fkey;
ALTER TABLE meetings ADD CONSTRAINT meetings_deal_id_fkey
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE SET NULL;

-- ============================================================================
-- 5. CREATE REVENUE ATTRIBUTION TABLE
-- ============================================================================
-- Track which activities contributed to revenue

CREATE TABLE IF NOT EXISTS revenue_attribution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Attribution model
    model TEXT NOT NULL DEFAULT 'first_touch',  -- 'first_touch', 'last_touch', 'linear', 'time_decay'

    -- The activity being credited
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    activity_channel channel_type NOT NULL,
    activity_at TIMESTAMPTZ NOT NULL,

    -- Credit
    credit_percentage DECIMAL(5,2) NOT NULL,  -- Percentage of deal value attributed
    credit_value DECIMAL(12,2),  -- Actual dollar value attributed

    -- Position in journey
    touch_position INTEGER,  -- 1 = first, -1 = last, etc.
    total_touches INTEGER,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- 6. CREATE INDEXES
-- ============================================================================

-- Meetings indexes
CREATE INDEX IF NOT EXISTS idx_meetings_client ON meetings(client_id);
CREATE INDEX IF NOT EXISTS idx_meetings_lead ON meetings(lead_id);
CREATE INDEX IF NOT EXISTS idx_meetings_campaign ON meetings(campaign_id);
CREATE INDEX IF NOT EXISTS idx_meetings_scheduled ON meetings(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_meetings_outcome ON meetings(meeting_outcome);
CREATE INDEX IF NOT EXISTS idx_meetings_showed_up ON meetings(showed_up);
CREATE INDEX IF NOT EXISTS idx_meetings_booked_at ON meetings(booked_at);

-- Deals indexes
CREATE INDEX IF NOT EXISTS idx_deals_client ON deals(client_id);
CREATE INDEX IF NOT EXISTS idx_deals_lead ON deals(lead_id);
CREATE INDEX IF NOT EXISTS idx_deals_meeting ON deals(meeting_id);
CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
CREATE INDEX IF NOT EXISTS idx_deals_won ON deals(won) WHERE won IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_deals_closed_at ON deals(closed_at);
CREATE INDEX IF NOT EXISTS idx_deals_value ON deals(value) WHERE value IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_deals_external ON deals(external_crm, external_deal_id);

-- Deal history indexes
CREATE INDEX IF NOT EXISTS idx_deal_history_deal ON deal_stage_history(deal_id);
CREATE INDEX IF NOT EXISTS idx_deal_history_stage ON deal_stage_history(to_stage);
CREATE INDEX IF NOT EXISTS idx_deal_history_date ON deal_stage_history(changed_at);

-- Revenue attribution indexes
CREATE INDEX IF NOT EXISTS idx_revenue_attr_deal ON revenue_attribution(deal_id);
CREATE INDEX IF NOT EXISTS idx_revenue_attr_activity ON revenue_attribution(activity_id);
CREATE INDEX IF NOT EXISTS idx_revenue_attr_channel ON revenue_attribution(activity_channel);

-- ============================================================================
-- 7. TRIGGER TO TRACK DEAL STAGE CHANGES
-- ============================================================================

CREATE OR REPLACE FUNCTION track_deal_stage_change()
RETURNS TRIGGER AS $$
DECLARE
    days_in_prev INTEGER;
BEGIN
    -- Only track if stage actually changed
    IF OLD.stage IS DISTINCT FROM NEW.stage THEN
        -- Calculate days in previous stage
        days_in_prev := EXTRACT(DAY FROM (NOW() - COALESCE(OLD.stage_changed_at, OLD.created_at)));

        -- Insert history record
        INSERT INTO deal_stage_history (deal_id, from_stage, to_stage, changed_by, days_in_previous_stage)
        VALUES (NEW.id, OLD.stage, NEW.stage, 'system', days_in_prev);

        -- Update stage changed timestamp
        NEW.stage_changed_at := NOW();
        NEW.days_in_stage := 0;

        -- Handle closing
        IF NEW.stage IN ('closed_won', 'closed_lost') AND NEW.closed_at IS NULL THEN
            NEW.closed_at := NOW();
            NEW.days_to_close := EXTRACT(DAY FROM (NOW() - NEW.created_at));
            NEW.won := (NEW.stage = 'closed_won');
        END IF;
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS on_deal_stage_change ON deals;
CREATE TRIGGER on_deal_stage_change
    BEFORE UPDATE ON deals
    FOR EACH ROW
    EXECUTE FUNCTION track_deal_stage_change();

-- ============================================================================
-- 8. TRIGGER TO UPDATE MEETING STATS
-- ============================================================================

CREATE OR REPLACE FUNCTION update_meeting_on_outcome()
RETURNS TRIGGER AS $$
BEGIN
    -- Set outcome timestamp
    IF NEW.meeting_outcome IS NOT NULL AND OLD.meeting_outcome IS NULL THEN
        NEW.meeting_outcome_at := NOW();
    END IF;

    -- Auto-set showed_up based on outcome
    IF NEW.meeting_outcome = 'no_show' THEN
        NEW.showed_up := FALSE;
        NEW.showed_up_confirmed_at := COALESCE(NEW.showed_up_confirmed_at, NOW());
    ELSIF NEW.meeting_outcome IN ('good', 'bad') THEN
        NEW.showed_up := TRUE;
        NEW.showed_up_confirmed_at := COALESCE(NEW.showed_up_confirmed_at, NOW());
    END IF;

    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS on_meeting_outcome ON meetings;
CREATE TRIGGER on_meeting_outcome
    BEFORE UPDATE ON meetings
    FOR EACH ROW
    EXECUTE FUNCTION update_meeting_on_outcome();

-- ============================================================================
-- 9. HELPER FUNCTION: CALCULATE REVENUE ATTRIBUTION
-- ============================================================================

CREATE OR REPLACE FUNCTION calculate_revenue_attribution(
    p_deal_id UUID,
    p_model TEXT DEFAULT 'first_touch'
)
RETURNS void AS $$
DECLARE
    v_deal RECORD;
    v_activities RECORD;
    v_total_activities INTEGER;
    v_credit_per DECIMAL(5,2);
    v_position INTEGER := 0;
    v_time_weight DECIMAL;
BEGIN
    -- Get deal info
    SELECT * INTO v_deal FROM deals WHERE id = p_deal_id;
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Clear existing attribution
    DELETE FROM revenue_attribution WHERE deal_id = p_deal_id AND model = p_model;

    -- Get all activities for this lead before deal creation
    SELECT COUNT(*) INTO v_total_activities
    FROM activities a
    JOIN leads l ON l.id = a.lead_id
    WHERE l.id = v_deal.lead_id
    AND a.created_at <= v_deal.created_at;

    IF v_total_activities = 0 THEN
        RETURN;
    END IF;

    -- Calculate credit based on model
    FOR v_activities IN
        SELECT a.id, a.channel, a.created_at
        FROM activities a
        WHERE a.lead_id = v_deal.lead_id
        AND a.created_at <= v_deal.created_at
        ORDER BY a.created_at ASC
    LOOP
        v_position := v_position + 1;

        CASE p_model
            WHEN 'first_touch' THEN
                v_credit_per := CASE WHEN v_position = 1 THEN 100.0 ELSE 0.0 END;
            WHEN 'last_touch' THEN
                v_credit_per := CASE WHEN v_position = v_total_activities THEN 100.0 ELSE 0.0 END;
            WHEN 'linear' THEN
                v_credit_per := 100.0 / v_total_activities;
            WHEN 'time_decay' THEN
                -- More recent touches get more credit (exponential decay)
                v_time_weight := POWER(2.0, (v_position - v_total_activities)::DECIMAL / 3.0);
                v_credit_per := (v_time_weight / v_total_activities) * 100.0;
            ELSE
                v_credit_per := 100.0 / v_total_activities;
        END CASE;

        IF v_credit_per > 0 THEN
            INSERT INTO revenue_attribution (
                deal_id, client_id, model, activity_id, activity_channel, activity_at,
                credit_percentage, credit_value, touch_position, total_touches
            ) VALUES (
                p_deal_id, v_deal.client_id, p_model, v_activities.id, v_activities.channel, v_activities.created_at,
                v_credit_per, (v_deal.value * v_credit_per / 100.0), v_position, v_total_activities
            );
        END IF;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 10. HELPER FUNCTION: GET FUNNEL ANALYTICS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_funnel_analytics(
    p_client_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_leads BIGINT,
    leads_with_activities BIGINT,
    meetings_booked BIGINT,
    meetings_showed BIGINT,
    deals_created BIGINT,
    deals_won BIGINT,
    deals_lost BIGINT,
    total_pipeline_value DECIMAL,
    total_won_value DECIMAL,
    avg_deal_value DECIMAL,
    avg_days_to_close NUMERIC,
    show_rate NUMERIC,
    meeting_to_deal_rate NUMERIC,
    deal_win_rate NUMERIC,
    lead_to_meeting_rate NUMERIC,
    lead_to_win_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH period_stats AS (
        SELECT
            (SELECT COUNT(*) FROM leads WHERE client_id = p_client_id AND created_at >= NOW() - (p_days || ' days')::INTERVAL) as leads,
            (SELECT COUNT(DISTINCT lead_id) FROM activities WHERE client_id = p_client_id AND created_at >= NOW() - (p_days || ' days')::INTERVAL) as contacted,
            (SELECT COUNT(*) FROM meetings WHERE client_id = p_client_id AND booked_at >= NOW() - (p_days || ' days')::INTERVAL) as meetings,
            (SELECT COUNT(*) FROM meetings WHERE client_id = p_client_id AND showed_up = TRUE AND booked_at >= NOW() - (p_days || ' days')::INTERVAL) as showed,
            (SELECT COUNT(*) FROM deals WHERE client_id = p_client_id AND created_at >= NOW() - (p_days || ' days')::INTERVAL) as deals,
            (SELECT COUNT(*) FROM deals WHERE client_id = p_client_id AND won = TRUE AND closed_at >= NOW() - (p_days || ' days')::INTERVAL) as won,
            (SELECT COUNT(*) FROM deals WHERE client_id = p_client_id AND won = FALSE AND closed_at >= NOW() - (p_days || ' days')::INTERVAL) as lost,
            (SELECT COALESCE(SUM(value), 0) FROM deals WHERE client_id = p_client_id AND stage NOT IN ('closed_won', 'closed_lost') AND created_at >= NOW() - (p_days || ' days')::INTERVAL) as pipeline,
            (SELECT COALESCE(SUM(value), 0) FROM deals WHERE client_id = p_client_id AND won = TRUE AND closed_at >= NOW() - (p_days || ' days')::INTERVAL) as won_value,
            (SELECT AVG(value) FROM deals WHERE client_id = p_client_id AND won = TRUE AND closed_at >= NOW() - (p_days || ' days')::INTERVAL) as avg_value,
            (SELECT AVG(days_to_close) FROM deals WHERE client_id = p_client_id AND closed_at IS NOT NULL AND closed_at >= NOW() - (p_days || ' days')::INTERVAL) as avg_close
    )
    SELECT
        ps.leads::BIGINT,
        ps.contacted::BIGINT,
        ps.meetings::BIGINT,
        ps.showed::BIGINT,
        ps.deals::BIGINT,
        ps.won::BIGINT,
        ps.lost::BIGINT,
        ps.pipeline::DECIMAL,
        ps.won_value::DECIMAL,
        ROUND(ps.avg_value, 2)::DECIMAL,
        ROUND(ps.avg_close, 1),
        ROUND(ps.showed::NUMERIC / NULLIF(ps.meetings, 0) * 100, 1),  -- Show rate
        ROUND(ps.deals::NUMERIC / NULLIF(ps.showed, 0) * 100, 1),  -- Meeting to deal
        ROUND(ps.won::NUMERIC / NULLIF(ps.deals, 0) * 100, 1),  -- Win rate
        ROUND(ps.meetings::NUMERIC / NULLIF(ps.contacted, 0) * 100, 2),  -- Lead to meeting
        ROUND(ps.won::NUMERIC / NULLIF(ps.contacted, 0) * 100, 2)  -- Lead to win
    FROM period_stats ps;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 11. HELPER FUNCTION: GET CHANNEL REVENUE ATTRIBUTION
-- ============================================================================

CREATE OR REPLACE FUNCTION get_channel_revenue_attribution(
    p_client_id UUID,
    p_days INTEGER DEFAULT 90,
    p_model TEXT DEFAULT 'first_touch'
)
RETURNS TABLE (
    channel TEXT,
    deals_attributed BIGINT,
    total_value DECIMAL,
    avg_deal_value DECIMAL,
    percentage_of_revenue NUMERIC
) AS $$
DECLARE
    v_total_revenue DECIMAL;
BEGIN
    -- Get total attributed revenue
    SELECT COALESCE(SUM(credit_value), 0) INTO v_total_revenue
    FROM revenue_attribution ra
    JOIN deals d ON d.id = ra.deal_id
    WHERE ra.client_id = p_client_id
    AND ra.model = p_model
    AND d.closed_at >= NOW() - (p_days || ' days')::INTERVAL;

    RETURN QUERY
    SELECT
        ra.activity_channel::TEXT as channel,
        COUNT(DISTINCT ra.deal_id) as deals_attributed,
        SUM(ra.credit_value)::DECIMAL as total_value,
        ROUND(AVG(ra.credit_value), 2)::DECIMAL as avg_deal_value,
        ROUND(SUM(ra.credit_value) / NULLIF(v_total_revenue, 0) * 100, 1)::NUMERIC as percentage_of_revenue
    FROM revenue_attribution ra
    JOIN deals d ON d.id = ra.deal_id
    WHERE ra.client_id = p_client_id
    AND ra.model = p_model
    AND d.closed_at >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY ra.activity_channel
    ORDER BY total_value DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 12. HELPER FUNCTION: GET LOST DEAL ANALYSIS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_lost_deal_analysis(
    p_client_id UUID,
    p_days INTEGER DEFAULT 90
)
RETURNS TABLE (
    lost_reason TEXT,
    count BIGINT,
    total_lost_value DECIMAL,
    avg_days_in_pipeline NUMERIC,
    common_stage_lost TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH stage_counts AS (
        SELECT
            d.lost_reason,
            dsh.from_stage as stage_lost,
            COUNT(*) as cnt
        FROM deals d
        JOIN deal_stage_history dsh ON dsh.deal_id = d.id AND dsh.to_stage = 'closed_lost'
        WHERE d.client_id = p_client_id
        AND d.won = FALSE
        AND d.closed_at >= NOW() - (p_days || ' days')::INTERVAL
        GROUP BY d.lost_reason, dsh.from_stage
    ),
    ranked_stages AS (
        SELECT
            lost_reason,
            stage_lost,
            cnt,
            ROW_NUMBER() OVER (PARTITION BY lost_reason ORDER BY cnt DESC) as rn
        FROM stage_counts
    )
    SELECT
        d.lost_reason::TEXT,
        COUNT(*)::BIGINT as count,
        SUM(d.value)::DECIMAL as total_lost_value,
        ROUND(AVG(d.days_to_close), 1) as avg_days_in_pipeline,
        (SELECT rs.stage_lost::TEXT FROM ranked_stages rs WHERE rs.lost_reason = d.lost_reason AND rs.rn = 1) as common_stage_lost
    FROM deals d
    WHERE d.client_id = p_client_id
    AND d.won = FALSE
    AND d.closed_at >= NOW() - (p_days || ' days')::INTERVAL
    GROUP BY d.lost_reason
    ORDER BY count DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 13. HELPER FUNCTION: GET SHOW RATE ANALYSIS
-- ============================================================================

CREATE OR REPLACE FUNCTION get_show_rate_analysis(
    p_client_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    metric TEXT,
    value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    WITH meeting_stats AS (
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE showed_up = TRUE) as showed,
            COUNT(*) FILTER (WHERE showed_up = FALSE) as no_show,
            COUNT(*) FILTER (WHERE meeting_outcome = 'rescheduled') as rescheduled,
            COUNT(*) FILTER (WHERE confirmed = TRUE) as confirmed,
            COUNT(*) FILTER (WHERE reminder_sent = TRUE) as reminded,
            COUNT(*) FILTER (WHERE showed_up = TRUE AND confirmed = TRUE) as confirmed_showed,
            COUNT(*) FILTER (WHERE confirmed = TRUE) as confirmed_total,
            COUNT(*) FILTER (WHERE showed_up = TRUE AND reminder_sent = TRUE) as reminded_showed,
            COUNT(*) FILTER (WHERE reminder_sent = TRUE) as reminded_total
        FROM meetings
        WHERE client_id = p_client_id
        AND scheduled_at >= NOW() - (p_days || ' days')::INTERVAL
        AND scheduled_at <= NOW()
    )
    SELECT 'total_meetings'::TEXT, total::NUMERIC FROM meeting_stats
    UNION ALL
    SELECT 'show_rate', ROUND(showed::NUMERIC / NULLIF(total, 0) * 100, 1) FROM meeting_stats
    UNION ALL
    SELECT 'no_show_rate', ROUND(no_show::NUMERIC / NULLIF(total, 0) * 100, 1) FROM meeting_stats
    UNION ALL
    SELECT 'reschedule_rate', ROUND(rescheduled::NUMERIC / NULLIF(total, 0) * 100, 1) FROM meeting_stats
    UNION ALL
    SELECT 'confirmed_show_rate', ROUND(confirmed_showed::NUMERIC / NULLIF(confirmed_total, 0) * 100, 1) FROM meeting_stats
    UNION ALL
    SELECT 'reminded_show_rate', ROUND(reminded_showed::NUMERIC / NULLIF(reminded_total, 0) * 100, 1) FROM meeting_stats;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 14. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE deal_stage_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE revenue_attribution ENABLE ROW LEVEL SECURITY;

-- Meetings policy
CREATE POLICY meetings_client_isolation ON meetings
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

-- Deals policy
CREATE POLICY deals_client_isolation ON deals
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

-- Deal history policy
CREATE POLICY deal_history_client_isolation ON deal_stage_history
    FOR ALL
    USING (
        deal_id IN (
            SELECT id FROM deals WHERE client_id IN (
                SELECT client_id FROM memberships
                WHERE user_id = auth.uid()
            )
        )
    );

-- Revenue attribution policy
CREATE POLICY revenue_attr_client_isolation ON revenue_attribution
    FOR ALL
    USING (
        client_id IN (
            SELECT client_id FROM memberships
            WHERE user_id = auth.uid()
        )
    );

-- ============================================================================
-- 15. ADD MEETING/DEAL REFERENCES TO LEADS
-- ============================================================================

ALTER TABLE leads ADD COLUMN IF NOT EXISTS meeting_booked BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meeting_booked_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS meeting_id UUID REFERENCES meetings(id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS deal_id UUID REFERENCES deals(id);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS deal_value DECIMAL(12,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS deal_won BOOLEAN;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS deal_won_at TIMESTAMPTZ;

-- ============================================================================
-- COMPLETE
-- ============================================================================
