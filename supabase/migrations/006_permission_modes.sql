-- FILE: supabase/migrations/006_permission_modes.sql
-- PURPOSE: Autopilot/Co-Pilot/Manual permission mode infrastructure
-- PHASE: 1 (Foundation + DevOps)
-- TASK: DB-007
-- DEPENDENCIES: 005_activities.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only

-- ============================================
-- APPROVAL QUEUE (For Co-Pilot Mode)
-- ============================================

-- When permission_mode = 'co_pilot', actions queue here for approval
CREATE TABLE approval_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,

    -- What action is being requested
    action_type TEXT NOT NULL,  -- send_email, send_sms, connect_linkedin, etc.
    channel channel_type,

    -- Proposed content
    proposed_content JSONB NOT NULL,
    /*
    Example for email:
    {
        "subject": "Quick question about...",
        "body": "Hi {{first_name}}...",
        "from_email": "john@company.com",
        "sequence_step": 1
    }
    */

    -- AI recommendation context
    ai_recommendation TEXT,        -- Why AI recommends this action
    ai_confidence FLOAT,           -- How confident AI is (0-1)
    als_score INTEGER,             -- Lead's ALS score for context

    -- Approval status
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, expired
    approved_by UUID REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,

    -- Expiration (actions auto-expire if not reviewed)
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger for updated_at
CREATE TRIGGER approval_queue_updated_at
    BEFORE UPDATE ON approval_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Indexes
CREATE INDEX idx_approval_queue_client ON approval_queue(client_id, status)
    WHERE status = 'pending';
CREATE INDEX idx_approval_queue_campaign ON approval_queue(campaign_id)
    WHERE status = 'pending';
CREATE INDEX idx_approval_queue_expires ON approval_queue(expires_at)
    WHERE status = 'pending';

-- ============================================
-- PERMISSION OVERRIDES (Per-Lead)
-- ============================================

-- Override permission mode for specific leads
CREATE TABLE lead_permission_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    permission_mode permission_mode NOT NULL,
    reason TEXT,
    created_by UUID REFERENCES users(id),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_lead_override UNIQUE (lead_id)
);

-- Index for lookup
CREATE INDEX idx_lead_overrides ON lead_permission_overrides(lead_id);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get effective permission mode for a lead
CREATE OR REPLACE FUNCTION get_effective_permission_mode(
    p_lead_id UUID
)
RETURNS permission_mode AS $$
DECLARE
    v_override permission_mode;
    v_campaign_mode permission_mode;
    v_client_mode permission_mode;
    v_campaign_id UUID;
    v_client_id UUID;
BEGIN
    -- Check for lead-specific override
    SELECT permission_mode INTO v_override
    FROM lead_permission_overrides
    WHERE lead_id = p_lead_id
    AND (expires_at IS NULL OR expires_at > NOW());

    IF v_override IS NOT NULL THEN
        RETURN v_override;
    END IF;

    -- Get campaign and client IDs
    SELECT campaign_id, client_id INTO v_campaign_id, v_client_id
    FROM leads WHERE id = p_lead_id;

    -- Check campaign-level setting
    SELECT permission_mode INTO v_campaign_mode
    FROM campaigns WHERE id = v_campaign_id;

    IF v_campaign_mode IS NOT NULL THEN
        RETURN v_campaign_mode;
    END IF;

    -- Fall back to client default
    SELECT default_permission_mode INTO v_client_mode
    FROM clients WHERE id = v_client_id;

    RETURN COALESCE(v_client_mode, 'co_pilot');
END;
$$ LANGUAGE plpgsql STABLE;

-- Check if action requires approval
CREATE OR REPLACE FUNCTION requires_approval(
    p_lead_id UUID,
    p_action_type TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_mode permission_mode;
BEGIN
    v_mode := get_effective_permission_mode(p_lead_id);

    CASE v_mode
        WHEN 'autopilot' THEN RETURN FALSE;
        WHEN 'manual' THEN RETURN TRUE;
        WHEN 'co_pilot' THEN RETURN TRUE;
        ELSE RETURN TRUE;
    END CASE;
END;
$$ LANGUAGE plpgsql STABLE;

-- Queue action for approval
CREATE OR REPLACE FUNCTION queue_for_approval(
    p_client_id UUID,
    p_campaign_id UUID,
    p_lead_id UUID,
    p_action_type TEXT,
    p_channel channel_type,
    p_content JSONB,
    p_ai_recommendation TEXT DEFAULT NULL,
    p_ai_confidence FLOAT DEFAULT NULL,
    p_als_score INTEGER DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_queue_id UUID;
BEGIN
    INSERT INTO approval_queue (
        client_id, campaign_id, lead_id,
        action_type, channel, proposed_content,
        ai_recommendation, ai_confidence, als_score
    ) VALUES (
        p_client_id, p_campaign_id, p_lead_id,
        p_action_type, p_channel, p_content,
        p_ai_recommendation, p_ai_confidence, p_als_score
    )
    RETURNING id INTO v_queue_id;

    RETURN v_queue_id;
END;
$$ LANGUAGE plpgsql;

-- Approve action from queue
CREATE OR REPLACE FUNCTION approve_action(
    p_queue_id UUID,
    p_user_id UUID
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE approval_queue
    SET status = 'approved',
        approved_by = p_user_id,
        approved_at = NOW()
    WHERE id = p_queue_id
    AND status = 'pending';

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Reject action from queue
CREATE OR REPLACE FUNCTION reject_action(
    p_queue_id UUID,
    p_user_id UUID,
    p_reason TEXT DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE approval_queue
    SET status = 'rejected',
        approved_by = p_user_id,
        approved_at = NOW(),
        rejection_reason = p_reason
    WHERE id = p_queue_id
    AND status = 'pending';

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Expire old pending approvals
CREATE OR REPLACE FUNCTION expire_pending_approvals()
RETURNS INTEGER AS $$
DECLARE
    v_count INTEGER;
BEGIN
    UPDATE approval_queue
    SET status = 'expired'
    WHERE status = 'pending'
    AND expires_at < NOW();

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] approval_queue table for co-pilot mode
-- [x] lead_permission_overrides for per-lead settings
-- [x] get_effective_permission_mode() function
-- [x] requires_approval() function
-- [x] queue_for_approval() function
-- [x] approve_action() and reject_action() functions
-- [x] expire_pending_approvals() for cleanup
-- [x] Proper indexes for performance
-- [x] updated_at trigger
