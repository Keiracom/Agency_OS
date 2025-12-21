-- FILE: supabase/migrations/003_campaigns.sql
-- PURPOSE: Campaigns with channel allocation percentages
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-004
-- DEPENDENCIES: 002_clients_users_memberships.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (deleted_at column)

-- ============================================
-- CAMPAIGNS
-- ============================================

CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,

    -- Basic info
    name TEXT NOT NULL,
    description TEXT,
    status campaign_status NOT NULL DEFAULT 'draft',

    -- Permission mode (overrides client default)
    permission_mode permission_mode,

    -- Target settings
    target_industries TEXT[],
    target_titles TEXT[],
    target_company_sizes TEXT[],  -- e.g., ['1-10', '11-50', '51-200']
    target_locations TEXT[],       -- e.g., ['Australia', 'New Zealand']

    -- Channel allocation percentages (must sum to 100)
    allocation_email INTEGER NOT NULL DEFAULT 100,
    allocation_sms INTEGER NOT NULL DEFAULT 0,
    allocation_linkedin INTEGER NOT NULL DEFAULT 0,
    allocation_voice INTEGER NOT NULL DEFAULT 0,
    allocation_mail INTEGER NOT NULL DEFAULT 0,

    -- Scheduling
    start_date DATE,
    end_date DATE,
    daily_limit INTEGER DEFAULT 50,  -- Max outreach per day
    timezone TEXT DEFAULT 'Australia/Sydney',

    -- Working hours (24h format)
    work_hours_start TIME DEFAULT '09:00',
    work_hours_end TIME DEFAULT '17:00',
    work_days INTEGER[] DEFAULT ARRAY[1,2,3,4,5],  -- Mon-Fri

    -- Metrics (denormalized for performance)
    total_leads INTEGER DEFAULT 0,
    leads_contacted INTEGER DEFAULT 0,
    leads_replied INTEGER DEFAULT 0,
    leads_converted INTEGER DEFAULT 0,

    -- Sequence settings
    sequence_steps INTEGER DEFAULT 5,
    sequence_delay_days INTEGER DEFAULT 3,

    -- Metadata
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,  -- Soft delete (Rule 14)

    -- Constraints
    CONSTRAINT valid_allocation CHECK (
        allocation_email + allocation_sms + allocation_linkedin +
        allocation_voice + allocation_mail = 100
    ),
    CONSTRAINT valid_email_allocation CHECK (allocation_email >= 0 AND allocation_email <= 100),
    CONSTRAINT valid_sms_allocation CHECK (allocation_sms >= 0 AND allocation_sms <= 100),
    CONSTRAINT valid_linkedin_allocation CHECK (allocation_linkedin >= 0 AND allocation_linkedin <= 100),
    CONSTRAINT valid_voice_allocation CHECK (allocation_voice >= 0 AND allocation_voice <= 100),
    CONSTRAINT valid_mail_allocation CHECK (allocation_mail >= 0 AND allocation_mail <= 100),
    CONSTRAINT valid_daily_limit CHECK (daily_limit > 0 AND daily_limit <= 500)
);

-- Trigger for updated_at
CREATE TRIGGER campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Indexes for common queries
CREATE INDEX idx_campaigns_client ON campaigns(client_id)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_status ON campaigns(client_id, status)
    WHERE deleted_at IS NULL;
CREATE INDEX idx_campaigns_active ON campaigns(client_id)
    WHERE status = 'active' AND deleted_at IS NULL;
CREATE INDEX idx_campaigns_dates ON campaigns(start_date, end_date)
    WHERE status = 'active' AND deleted_at IS NULL;

-- ============================================
-- CAMPAIGN RESOURCES (Email domains, LinkedIn seats, etc.)
-- ============================================

CREATE TABLE campaign_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    channel channel_type NOT NULL,

    -- Resource identifier
    resource_id TEXT NOT NULL,  -- e.g., email domain, phone number, linkedin seat ID
    resource_name TEXT,         -- e.g., "john@company.com", "+61412345678"

    -- Rate limit tracking (resource-level, Rule 17)
    daily_limit INTEGER NOT NULL,
    daily_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    last_reset_at TIMESTAMPTZ DEFAULT NOW(),

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_warmed BOOLEAN DEFAULT FALSE,  -- For email warmup

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique per campaign + channel + resource
    CONSTRAINT unique_campaign_resource UNIQUE (campaign_id, channel, resource_id)
);

-- Trigger for updated_at
CREATE TRIGGER campaign_resources_updated_at
    BEFORE UPDATE ON campaign_resources
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Function to reset daily usage (called by cron)
CREATE OR REPLACE FUNCTION reset_resource_daily_usage()
RETURNS void AS $$
BEGIN
    UPDATE campaign_resources
    SET daily_used = 0,
        last_reset_at = NOW()
    WHERE last_reset_at < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;

-- Index for rate limit checks
CREATE INDEX idx_campaign_resources_active ON campaign_resources(campaign_id, channel)
    WHERE is_active = TRUE;
CREATE INDEX idx_campaign_resources_available ON campaign_resources(campaign_id, channel)
    WHERE is_active = TRUE AND daily_used < daily_limit;

-- ============================================
-- CAMPAIGN SEQUENCES
-- ============================================

CREATE TABLE campaign_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,

    -- Sequence step configuration
    channel channel_type NOT NULL,
    delay_days INTEGER NOT NULL DEFAULT 3,
    subject_template TEXT,
    body_template TEXT NOT NULL,

    -- Conditional logic
    skip_if_replied BOOLEAN DEFAULT TRUE,
    skip_if_bounced BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique step per campaign
    CONSTRAINT unique_sequence_step UNIQUE (campaign_id, step_number)
);

-- Trigger for updated_at
CREATE TRIGGER campaign_sequences_updated_at
    BEFORE UPDATE ON campaign_sequences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Index for sequence ordering
CREATE INDEX idx_campaign_sequences ON campaign_sequences(campaign_id, step_number);

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] campaigns table with all fields
-- [x] Channel allocation percentages (must sum to 100)
-- [x] Soft delete column (deleted_at)
-- [x] Permission mode override
-- [x] Scheduling fields (dates, hours, work days)
-- [x] Denormalized metrics
-- [x] campaign_resources for resource-level rate limits (Rule 17)
-- [x] campaign_sequences for multi-step sequences
-- [x] Indexes for performance
-- [x] updated_at triggers
