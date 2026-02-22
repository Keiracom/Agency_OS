-- ============================================================================
-- Migration 061: Conversion Intelligence System (CIS) Schema
-- ============================================================================
-- CIS captures learning data to answer: "What works and why?"
-- Complements existing: conversion_patterns, activities, replies, ab_tests
-- ============================================================================

-- ============================================================================
-- A. CIS Outreach Outcomes - Explicit funnel tracking
-- ============================================================================
-- Tracks: message sent → delivered → opened → clicked → replied → meeting → converted
-- Links to existing: activities, leads, campaigns

CREATE TABLE IF NOT EXISTS cis_outreach_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    activity_id UUID NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    
    -- Channel info
    channel channel_type NOT NULL,
    sequence_step INTEGER,
    
    -- Funnel stages with timestamps
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    meeting_booked_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ,
    
    -- Outcome classification
    final_outcome TEXT CHECK (final_outcome IN (
        'no_response', 'opened_only', 'clicked_only', 
        'replied_positive', 'replied_negative', 'replied_neutral',
        'meeting_booked', 'converted', 'unsubscribed', 'bounced'
    )),
    
    -- Attribution data
    touches_before_outcome INTEGER DEFAULT 0,
    days_to_outcome INTEGER,
    time_to_open_minutes INTEGER,
    time_to_reply_minutes INTEGER,
    
    -- Content fingerprint for pattern matching
    subject_hash TEXT,  -- hash of subject line for grouping
    hook_type TEXT,     -- e.g., 'pain_point', 'social_proof', 'question'
    personalization_level TEXT CHECK (personalization_level IN ('none', 'basic', 'deep', 'sdk_enhanced')),
    
    -- ALS snapshot at send time
    als_score_at_send INTEGER,
    als_tier_at_send TEXT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_cis_outcomes_client_channel ON cis_outreach_outcomes(client_id, channel);
CREATE INDEX idx_cis_outcomes_campaign ON cis_outreach_outcomes(campaign_id);
CREATE INDEX idx_cis_outcomes_sent_at ON cis_outreach_outcomes(sent_at);
CREATE INDEX idx_cis_outcomes_final_outcome ON cis_outreach_outcomes(final_outcome);
CREATE INDEX idx_cis_outcomes_als_tier ON cis_outreach_outcomes(als_tier_at_send);

COMMENT ON TABLE cis_outreach_outcomes IS 'Tracks full outreach funnel from send to conversion. Answers: "What percentage of emails to hot leads convert?"';


-- ============================================================================
-- B. CIS Reply Classifications - Detailed intent analysis
-- ============================================================================
-- Extends replies table with richer classification from reply_analyzer.py

CREATE TABLE IF NOT EXISTS cis_reply_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    reply_id UUID NOT NULL REFERENCES replies(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Primary classification
    primary_intent TEXT NOT NULL CHECK (primary_intent IN (
        'meeting_request', 'interested', 'question', 'objection',
        'not_interested', 'referral', 'unsubscribe', 'out_of_office',
        'auto_reply', 'angry', 'confused', 'wrong_person'
    )),
    intent_confidence FLOAT CHECK (intent_confidence >= 0 AND intent_confidence <= 1),
    
    -- Sub-classification for objections
    objection_category TEXT CHECK (objection_category IN (
        'timing', 'budget', 'authority', 'need', 'trust', 
        'competitor', 'too_busy', 'bad_experience', 'other'
    )),
    
    -- Sentiment analysis
    sentiment TEXT CHECK (sentiment IN ('positive', 'neutral', 'negative', 'mixed')),
    sentiment_score FLOAT,  -- -1 to 1
    
    -- Extracted information
    questions_asked TEXT[],
    topics_mentioned TEXT[],
    competitor_mentioned TEXT,
    timeline_mentioned TEXT,  -- e.g., 'next_quarter', 'next_year'
    budget_mentioned BOOLEAN DEFAULT false,
    
    -- Response quality indicators
    is_substantive BOOLEAN DEFAULT true,  -- vs one-word reply
    word_count INTEGER,
    response_time_hours FLOAT,
    
    -- Classification metadata
    classifier_version TEXT DEFAULT 'v1',
    classified_at TIMESTAMPTZ DEFAULT now(),
    manual_override BOOLEAN DEFAULT false,
    override_by UUID REFERENCES users(id),
    
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cis_reply_class_client ON cis_reply_classifications(client_id);
CREATE INDEX idx_cis_reply_class_intent ON cis_reply_classifications(primary_intent);
CREATE INDEX idx_cis_reply_class_objection ON cis_reply_classifications(objection_category);

COMMENT ON TABLE cis_reply_classifications IS 'Detailed reply intent classification. Answers: "What objections do we see most from enterprise leads?"';


-- ============================================================================
-- C. CIS Channel Performance - Aggregated channel stats
-- ============================================================================
-- Pre-aggregated metrics per campaign/channel for fast dashboards

CREATE TABLE IF NOT EXISTS cis_channel_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Dimensions
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    channel channel_type NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Volume metrics
    sends INTEGER DEFAULT 0,
    deliveries INTEGER DEFAULT 0,
    opens INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    positive_replies INTEGER DEFAULT 0,
    meetings_booked INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    
    -- Rate metrics (pre-calculated for performance)
    delivery_rate NUMERIC(5,4),  -- deliveries/sends
    open_rate NUMERIC(5,4),      -- opens/deliveries
    click_rate NUMERIC(5,4),     -- clicks/opens
    reply_rate NUMERIC(5,4),     -- replies/deliveries
    positive_reply_rate NUMERIC(5,4),
    meeting_rate NUMERIC(5,4),   -- meetings/sends
    conversion_rate NUMERIC(5,4), -- conversions/sends
    
    -- Efficiency metrics
    avg_touches_to_reply NUMERIC(4,2),
    avg_touches_to_meeting NUMERIC(4,2),
    avg_days_to_reply NUMERIC(5,2),
    avg_days_to_meeting NUMERIC(5,2),
    
    -- Cost metrics (if applicable)
    total_cost_aud NUMERIC(10,2) DEFAULT 0,
    cost_per_reply_aud NUMERIC(10,2),
    cost_per_meeting_aud NUMERIC(10,2),
    
    -- Metadata
    computed_at TIMESTAMPTZ DEFAULT now(),
    
    -- Unique constraint for upsert
    CONSTRAINT uq_channel_perf_daily UNIQUE (client_id, campaign_id, channel, date)
);

CREATE INDEX idx_cis_channel_perf_client_date ON cis_channel_performance(client_id, date);
CREATE INDEX idx_cis_channel_perf_campaign ON cis_channel_performance(campaign_id);

COMMENT ON TABLE cis_channel_performance IS 'Daily aggregated channel metrics. Answers: "Which channel has best ROI for this campaign?"';


-- ============================================================================
-- D. CIS ALS Tier Conversions - Tier effectiveness tracking
-- ============================================================================
-- Tracks which ALS tiers actually convert

CREATE TABLE IF NOT EXISTS cis_als_tier_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Dimensions
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    als_tier TEXT NOT NULL CHECK (als_tier IN ('hot', 'warm', 'cool', 'cold', 'dead')),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Volume at each stage
    leads_in_tier INTEGER DEFAULT 0,
    leads_contacted INTEGER DEFAULT 0,
    leads_opened INTEGER DEFAULT 0,
    leads_replied INTEGER DEFAULT 0,
    leads_positive_reply INTEGER DEFAULT 0,
    leads_meeting_booked INTEGER DEFAULT 0,
    leads_converted INTEGER DEFAULT 0,
    
    -- Conversion rates
    contact_rate NUMERIC(5,4),
    open_rate NUMERIC(5,4),
    reply_rate NUMERIC(5,4),
    positive_reply_rate NUMERIC(5,4),
    meeting_rate NUMERIC(5,4),
    conversion_rate NUMERIC(5,4),
    
    -- ALS accuracy metrics
    avg_als_score_converted NUMERIC(5,2),
    avg_als_score_not_converted NUMERIC(5,2),
    
    -- Value metrics
    total_deal_value_aud NUMERIC(12,2),
    avg_deal_value_aud NUMERIC(10,2),
    
    -- Computed insights
    roi_multiplier NUMERIC(6,2),  -- value generated / cost
    tier_effectiveness_rank INTEGER,  -- 1 = best tier for this client
    
    computed_at TIMESTAMPTZ DEFAULT now(),
    
    CONSTRAINT uq_als_tier_period UNIQUE (client_id, campaign_id, als_tier, period_start)
);

CREATE INDEX idx_cis_als_tier_client ON cis_als_tier_conversions(client_id);
CREATE INDEX idx_cis_als_tier_tier ON cis_als_tier_conversions(als_tier);

COMMENT ON TABLE cis_als_tier_conversions IS 'ALS tier conversion tracking. Answers: "Do hot leads actually convert better than warm?"';


-- ============================================================================
-- E. CIS Message Patterns - What content works
-- ============================================================================
-- Track which hooks, templates, angles perform best

CREATE TABLE IF NOT EXISTS cis_message_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    ab_test_id UUID REFERENCES ab_tests(id) ON DELETE SET NULL,
    
    -- Pattern identification
    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'subject_line', 'opening_hook', 'cta', 'proof_point',
        'personalization_angle', 'full_template', 'voice_script'
    )),
    pattern_name TEXT NOT NULL,  -- human readable name
    pattern_hash TEXT NOT NULL,  -- for deduplication
    pattern_content TEXT,        -- the actual content
    
    -- Classification
    style TEXT CHECK (style IN (
        'direct', 'question', 'social_proof', 'pain_point',
        'curiosity', 'humor', 'formal', 'casual', 'data_driven'
    )),
    channel channel_type,
    target_persona TEXT,  -- e.g., 'CEO', 'Marketing Director'
    
    -- Performance metrics
    times_used INTEGER DEFAULT 0,
    opens INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    positive_replies INTEGER DEFAULT 0,
    meetings INTEGER DEFAULT 0,
    
    -- Calculated rates
    open_rate NUMERIC(5,4),
    reply_rate NUMERIC(5,4),
    positive_reply_rate NUMERIC(5,4),
    meeting_rate NUMERIC(5,4),
    
    -- Statistical significance
    sample_size INTEGER DEFAULT 0,
    confidence_level NUMERIC(5,4),  -- 0.95 = 95% confident
    is_winner BOOLEAN DEFAULT false,
    
    -- Period tracking
    first_used_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'testing', 'retired', 'champion')),
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cis_msg_patterns_client ON cis_message_patterns(client_id);
CREATE INDEX idx_cis_msg_patterns_type ON cis_message_patterns(pattern_type);
CREATE INDEX idx_cis_msg_patterns_status ON cis_message_patterns(status);
CREATE UNIQUE INDEX idx_cis_msg_patterns_hash ON cis_message_patterns(client_id, pattern_hash);

COMMENT ON TABLE cis_message_patterns IS 'Message pattern performance tracking. Answers: "Which opening hook converts CEOs best?"';


-- ============================================================================
-- F. CIS Agency Learnings - Client-specific patterns
-- ============================================================================
-- What works for this specific agency's ICP

CREATE TABLE IF NOT EXISTS cis_agency_learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Learning category
    learning_type TEXT NOT NULL CHECK (learning_type IN (
        'best_channel', 'best_time', 'best_day', 'best_hook',
        'best_persona_target', 'best_industry_angle', 'best_proof_point',
        'optimal_sequence_length', 'optimal_touchpoint_spacing',
        'avoid_topic', 'avoid_phrase'
    )),
    
    -- Learning content
    learning_key TEXT NOT NULL,      -- e.g., 'ceo', 'email', 'tuesday'
    learning_value JSONB NOT NULL,   -- structured learning data
    
    -- Evidence
    sample_size INTEGER NOT NULL,
    confidence_score NUMERIC(5,4) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    supporting_metrics JSONB,        -- stats backing this learning
    
    -- Performance impact
    performance_lift_percent NUMERIC(6,2),  -- e.g., +15.5% reply rate
    compared_to_baseline JSONB,
    
    -- Validity
    valid_from TIMESTAMPTZ DEFAULT now(),
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    
    -- Lineage
    derived_from_patterns UUID[],    -- cis_message_patterns.id array
    derived_from_outcomes UUID[],    -- cis_outreach_outcomes.id array
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    CONSTRAINT uq_agency_learning UNIQUE (client_id, learning_type, learning_key)
);

CREATE INDEX idx_cis_agency_learnings_client ON cis_agency_learnings(client_id);
CREATE INDEX idx_cis_agency_learnings_type ON cis_agency_learnings(learning_type);
CREATE INDEX idx_cis_agency_learnings_active ON cis_agency_learnings(client_id, is_active);

COMMENT ON TABLE cis_agency_learnings IS 'Agency-specific learnings. Answers: "What works best for THIS agency''s ICP?"';


-- ============================================================================
-- G. CIS Global Learning Pool - Cross-agency anonymized patterns
-- ============================================================================
-- Aggregated, anonymized learnings across all agencies

CREATE TABLE IF NOT EXISTS cis_global_learning_pool (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Learning identification
    learning_category TEXT NOT NULL CHECK (learning_category IN (
        'industry_pattern', 'role_pattern', 'company_size_pattern',
        'channel_benchmark', 'timing_pattern', 'content_pattern',
        'objection_pattern', 'conversion_pattern'
    )),
    
    -- Segmentation (anonymized)
    target_industry TEXT,
    target_role_category TEXT,  -- e.g., 'c_suite', 'director', 'manager'
    target_company_size TEXT,   -- e.g., '1-10', '11-50', '51-200'
    target_region TEXT,         -- e.g., 'AU', 'US', 'EU'
    
    -- Pattern content (anonymized)
    pattern_summary TEXT NOT NULL,
    pattern_metrics JSONB NOT NULL,
    
    -- Aggregated stats
    contributing_agencies INTEGER DEFAULT 0,  -- how many agencies contributed
    total_sample_size INTEGER NOT NULL,
    confidence_score NUMERIC(5,4),
    
    -- Benchmark metrics
    benchmark_open_rate NUMERIC(5,4),
    benchmark_reply_rate NUMERIC(5,4),
    benchmark_meeting_rate NUMERIC(5,4),
    benchmark_conversion_rate NUMERIC(5,4),
    
    -- Statistical validity
    std_deviation_open NUMERIC(5,4),
    std_deviation_reply NUMERIC(5,4),
    percentile_25_reply NUMERIC(5,4),
    percentile_75_reply NUMERIC(5,4),
    
    -- Freshness
    last_updated TIMESTAMPTZ DEFAULT now(),
    data_from_period_start DATE,
    data_from_period_end DATE,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cis_global_pool_category ON cis_global_learning_pool(learning_category);
CREATE INDEX idx_cis_global_pool_industry ON cis_global_learning_pool(target_industry);
CREATE INDEX idx_cis_global_pool_role ON cis_global_learning_pool(target_role_category);

COMMENT ON TABLE cis_global_learning_pool IS 'Cross-agency anonymized learnings. Answers: "What''s the industry benchmark for reply rates to CEOs?"';


-- ============================================================================
-- H. CIS Agency Pool Opt-Out - Privacy control
-- ============================================================================
-- Agencies can opt out of contributing to global pool

CREATE TABLE IF NOT EXISTS cis_agency_pool_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE UNIQUE,
    
    -- Opt-out controls
    contribute_to_global_pool BOOLEAN DEFAULT true,
    receive_from_global_pool BOOLEAN DEFAULT true,
    
    -- Granular controls
    exclude_industries TEXT[],     -- don't share learnings about these industries
    exclude_pattern_types TEXT[],  -- don't share certain pattern types
    
    -- Consent tracking
    consent_given_at TIMESTAMPTZ,
    consent_given_by UUID REFERENCES users(id),
    last_modified_at TIMESTAMPTZ DEFAULT now(),
    last_modified_by UUID REFERENCES users(id),
    
    created_at TIMESTAMPTZ DEFAULT now()
);

COMMENT ON TABLE cis_agency_pool_config IS 'Controls agency participation in global learning pool';


-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE cis_outreach_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE cis_reply_classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE cis_channel_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE cis_als_tier_conversions ENABLE ROW LEVEL SECURITY;
ALTER TABLE cis_message_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE cis_agency_learnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE cis_agency_pool_config ENABLE ROW LEVEL SECURITY;

-- Global pool is readable by all authenticated users (it's anonymized)
ALTER TABLE cis_global_learning_pool ENABLE ROW LEVEL SECURITY;

-- RLS for client-scoped tables
CREATE POLICY cis_outcomes_client_access ON cis_outreach_outcomes
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

CREATE POLICY cis_reply_class_client_access ON cis_reply_classifications
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

CREATE POLICY cis_channel_perf_client_access ON cis_channel_performance
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

CREATE POLICY cis_als_tier_client_access ON cis_als_tier_conversions
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

CREATE POLICY cis_msg_patterns_client_access ON cis_message_patterns
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

CREATE POLICY cis_agency_learnings_client_access ON cis_agency_learnings
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

CREATE POLICY cis_pool_config_client_access ON cis_agency_pool_config
    FOR ALL USING (
        client_id IN (
            SELECT m.client_id FROM memberships m 
            WHERE m.user_id = auth.uid() AND m.deleted_at IS NULL
        )
    );

-- Global pool is readable by all authenticated users
CREATE POLICY cis_global_pool_read ON cis_global_learning_pool
    FOR SELECT USING (auth.role() = 'authenticated');


-- ============================================================================
-- Helper function: Refresh channel performance daily
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_cis_channel_performance(
    p_client_id UUID,
    p_date DATE DEFAULT CURRENT_DATE
) RETURNS void AS $$
BEGIN
    INSERT INTO cis_channel_performance (
        client_id, campaign_id, channel, date,
        sends, deliveries, opens, clicks, replies,
        positive_replies, meetings_booked, conversions,
        delivery_rate, open_rate, click_rate, reply_rate,
        positive_reply_rate, meeting_rate, conversion_rate,
        computed_at
    )
    SELECT 
        o.client_id,
        o.campaign_id,
        o.channel,
        p_date,
        COUNT(*) AS sends,
        COUNT(*) FILTER (WHERE o.delivered_at IS NOT NULL) AS deliveries,
        COUNT(*) FILTER (WHERE o.opened_at IS NOT NULL) AS opens,
        COUNT(*) FILTER (WHERE o.clicked_at IS NOT NULL) AS clicks,
        COUNT(*) FILTER (WHERE o.replied_at IS NOT NULL) AS replies,
        COUNT(*) FILTER (WHERE o.final_outcome = 'replied_positive') AS positive_replies,
        COUNT(*) FILTER (WHERE o.meeting_booked_at IS NOT NULL) AS meetings_booked,
        COUNT(*) FILTER (WHERE o.converted_at IS NOT NULL) AS conversions,
        -- Rates
        CASE WHEN COUNT(*) > 0 
            THEN COUNT(*) FILTER (WHERE o.delivered_at IS NOT NULL)::NUMERIC / COUNT(*)
            ELSE 0 END,
        CASE WHEN COUNT(*) FILTER (WHERE o.delivered_at IS NOT NULL) > 0 
            THEN COUNT(*) FILTER (WHERE o.opened_at IS NOT NULL)::NUMERIC / COUNT(*) FILTER (WHERE o.delivered_at IS NOT NULL)
            ELSE 0 END,
        CASE WHEN COUNT(*) FILTER (WHERE o.opened_at IS NOT NULL) > 0 
            THEN COUNT(*) FILTER (WHERE o.clicked_at IS NOT NULL)::NUMERIC / COUNT(*) FILTER (WHERE o.opened_at IS NOT NULL)
            ELSE 0 END,
        CASE WHEN COUNT(*) FILTER (WHERE o.delivered_at IS NOT NULL) > 0 
            THEN COUNT(*) FILTER (WHERE o.replied_at IS NOT NULL)::NUMERIC / COUNT(*) FILTER (WHERE o.delivered_at IS NOT NULL)
            ELSE 0 END,
        CASE WHEN COUNT(*) FILTER (WHERE o.replied_at IS NOT NULL) > 0 
            THEN COUNT(*) FILTER (WHERE o.final_outcome = 'replied_positive')::NUMERIC / COUNT(*) FILTER (WHERE o.replied_at IS NOT NULL)
            ELSE 0 END,
        CASE WHEN COUNT(*) > 0 
            THEN COUNT(*) FILTER (WHERE o.meeting_booked_at IS NOT NULL)::NUMERIC / COUNT(*)
            ELSE 0 END,
        CASE WHEN COUNT(*) > 0 
            THEN COUNT(*) FILTER (WHERE o.converted_at IS NOT NULL)::NUMERIC / COUNT(*)
            ELSE 0 END,
        now()
    FROM cis_outreach_outcomes o
    WHERE o.client_id = p_client_id
      AND o.sent_at::DATE = p_date
    GROUP BY o.client_id, o.campaign_id, o.channel
    ON CONFLICT (client_id, campaign_id, channel, date)
    DO UPDATE SET
        sends = EXCLUDED.sends,
        deliveries = EXCLUDED.deliveries,
        opens = EXCLUDED.opens,
        clicks = EXCLUDED.clicks,
        replies = EXCLUDED.replies,
        positive_replies = EXCLUDED.positive_replies,
        meetings_booked = EXCLUDED.meetings_booked,
        conversions = EXCLUDED.conversions,
        delivery_rate = EXCLUDED.delivery_rate,
        open_rate = EXCLUDED.open_rate,
        click_rate = EXCLUDED.click_rate,
        reply_rate = EXCLUDED.reply_rate,
        positive_reply_rate = EXCLUDED.positive_reply_rate,
        meeting_rate = EXCLUDED.meeting_rate,
        conversion_rate = EXCLUDED.conversion_rate,
        computed_at = now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION refresh_cis_channel_performance IS 'Refresh daily channel performance metrics for a client';
