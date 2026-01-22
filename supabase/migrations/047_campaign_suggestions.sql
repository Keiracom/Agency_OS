-- Migration: 047_campaign_suggestions.sql
-- Purpose: Campaign evolution suggestions from CIS pattern analysis
-- Phase: Phase D - Item 18
-- Task: Implement campaign evolution agents

-- ============================================
-- CAMPAIGN SUGGESTIONS TABLE
-- ============================================

CREATE TYPE suggestion_type AS ENUM (
    'create_campaign',      -- Create new campaign for untapped segment
    'pause_campaign',       -- Pause underperforming campaign
    'adjust_allocation',    -- Change lead allocation percentages
    'refine_targeting',     -- Refine ICP/targeting criteria
    'change_channel_mix',   -- Adjust channel distribution
    'update_content',       -- Update messaging/templates
    'adjust_timing'         -- Change send times/sequence gaps
);

CREATE TYPE suggestion_status AS ENUM (
    'pending',      -- Awaiting client review
    'approved',     -- Client approved, ready to apply
    'rejected',     -- Client rejected
    'applied',      -- Changes applied to campaign
    'expired'       -- Suggestion expired (patterns changed)
);

CREATE TABLE campaign_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Ownership
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,  -- NULL for create_campaign

    -- Suggestion details
    suggestion_type suggestion_type NOT NULL,
    status suggestion_status NOT NULL DEFAULT 'pending',

    -- Analysis data
    title TEXT NOT NULL,                    -- Short summary
    description TEXT NOT NULL,              -- Detailed explanation
    rationale JSONB NOT NULL DEFAULT '{}',  -- Which patterns triggered this
    recommended_action JSONB NOT NULL,      -- Specific changes to make

    -- Confidence and priority
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    priority INTEGER NOT NULL DEFAULT 50 CHECK (priority >= 1 AND priority <= 100),

    -- Pattern source
    pattern_types TEXT[] NOT NULL DEFAULT '{}',  -- ['who', 'what', 'how'] that informed this
    pattern_snapshot JSONB,                       -- Snapshot of patterns at suggestion time

    -- Metrics at suggestion time
    current_metrics JSONB,  -- Campaign performance when suggestion was made
    projected_improvement JSONB,  -- Expected improvement if applied

    -- Lifecycle
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES auth.users(id),
    applied_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '14 days'),

    -- Client feedback
    client_notes TEXT,
    rejection_reason TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete
);

-- Indexes for common queries
CREATE INDEX idx_campaign_suggestions_client_id ON campaign_suggestions(client_id);
CREATE INDEX idx_campaign_suggestions_campaign_id ON campaign_suggestions(campaign_id);
CREATE INDEX idx_campaign_suggestions_status ON campaign_suggestions(status);
CREATE INDEX idx_campaign_suggestions_type ON campaign_suggestions(suggestion_type);
CREATE INDEX idx_campaign_suggestions_pending ON campaign_suggestions(client_id, status)
    WHERE status = 'pending' AND deleted_at IS NULL;
CREATE INDEX idx_campaign_suggestions_expires ON campaign_suggestions(expires_at)
    WHERE status = 'pending';

-- Updated_at trigger
CREATE TRIGGER set_campaign_suggestions_updated_at
    BEFORE UPDATE ON campaign_suggestions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SUGGESTION HISTORY TABLE (Audit Trail)
-- ============================================

CREATE TABLE campaign_suggestion_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suggestion_id UUID NOT NULL REFERENCES campaign_suggestions(id) ON DELETE CASCADE,

    -- What changed
    old_status suggestion_status,
    new_status suggestion_status NOT NULL,
    changed_by UUID REFERENCES auth.users(id),
    change_reason TEXT,

    -- Timestamp
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_suggestion_history_suggestion_id ON campaign_suggestion_history(suggestion_id);

-- ============================================
-- RLS POLICIES
-- ============================================

ALTER TABLE campaign_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_suggestion_history ENABLE ROW LEVEL SECURITY;

-- Clients can view their own suggestions
CREATE POLICY "Clients can view own suggestions"
    ON campaign_suggestions FOR SELECT
    USING (
        client_id IN (
            SELECT id FROM clients
            WHERE user_id = auth.uid()
        )
    );

-- Clients can update status of their own suggestions (approve/reject)
CREATE POLICY "Clients can update own suggestions"
    ON campaign_suggestions FOR UPDATE
    USING (
        client_id IN (
            SELECT id FROM clients
            WHERE user_id = auth.uid()
        )
    )
    WITH CHECK (
        client_id IN (
            SELECT id FROM clients
            WHERE user_id = auth.uid()
        )
    );

-- Service role can do everything
CREATE POLICY "Service role full access suggestions"
    ON campaign_suggestions FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access history"
    ON campaign_suggestion_history FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get pending suggestions count for a client
CREATE OR REPLACE FUNCTION get_pending_suggestions_count(p_client_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)::INTEGER
        FROM campaign_suggestions
        WHERE client_id = p_client_id
        AND status = 'pending'
        AND deleted_at IS NULL
        AND expires_at > NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Expire old suggestions
CREATE OR REPLACE FUNCTION expire_old_suggestions()
RETURNS INTEGER AS $$
DECLARE
    expired_count INTEGER;
BEGIN
    UPDATE campaign_suggestions
    SET status = 'expired',
        updated_at = NOW()
    WHERE status = 'pending'
    AND expires_at <= NOW()
    AND deleted_at IS NULL;

    GET DIAGNOSTICS expired_count = ROW_COUNT;
    RETURN expired_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- VERIFICATION
-- ============================================
-- [x] campaign_suggestions table with all required fields
-- [x] suggestion_type enum for action types
-- [x] suggestion_status enum for lifecycle
-- [x] History table for audit trail
-- [x] Indexes for common queries
-- [x] RLS policies for multi-tenancy
-- [x] Soft delete support (deleted_at)
-- [x] Expiration support (expires_at)
-- [x] Helper functions for common operations
