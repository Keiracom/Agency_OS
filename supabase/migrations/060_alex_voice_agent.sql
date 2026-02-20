-- FILE: supabase/migrations/060_alex_voice_agent.sql
-- PURPOSE: Voice calling tables for Alex Voice Agent (AI outbound calls)
-- PHASE: Voice Agent Architecture
-- TASK: VOICE-001
-- DEPENDENCIES: 024_lead_pool.sql, clients table, campaigns table
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (where applicable)

-- ============================================
-- ROLLBACK (Idempotent cleanup)
-- ============================================

DROP TRIGGER IF EXISTS voice_calls_updated_at ON voice_calls;
DROP TABLE IF EXISTS voice_call_context CASCADE;
DROP TABLE IF EXISTS voice_calls CASCADE;

-- ============================================
-- TABLE: voice_calls
-- Records each AI voice call attempt and outcome
-- ============================================

CREATE TABLE voice_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- ===== RELATIONSHIPS =====
    lead_id UUID NOT NULL REFERENCES lead_pool(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID REFERENCES campaigns(id),
    
    -- ===== CALL IDENTIFIERS =====
    phone_number TEXT NOT NULL,
    call_sid TEXT,                      -- Twilio SID
    elevenagets_call_id TEXT,           -- ElevenAgents call ID
    
    -- ===== CALL OUTCOME =====
    outcome TEXT CHECK (outcome IN (
        'BOOKED',           -- Appointment booked
        'CALLBACK',         -- Callback requested
        'INTERESTED',       -- Interest expressed, no booking
        'NOT_INTERESTED',   -- Politely declined
        'VOICEMAIL',        -- Left voicemail
        'NO_ANSWER',        -- Call not answered
        'UNSUBSCRIBE',      -- Requested removal
        'ESCALATION',       -- Transferred to human
        'ANGRY',            -- Hostile response
        'DNCR_BLOCKED',     -- Blocked by Do Not Call Registry
        'EXCLUDED',         -- Excluded before call (compliance)
        'INITIATED',        -- Call started, no outcome yet
        'FAILED'            -- Technical failure
    )),
    
    -- ===== CALL METRICS =====
    duration_seconds INTEGER,
    transcript TEXT,
    sentiment_summary TEXT,
    
    -- ===== PERSONALISATION =====
    hook_used TEXT,                     -- Which personalisation hook was selected
    als_score_at_call INTEGER,          -- ALS score at time of call
    
    -- ===== FOLLOW-UP =====
    callback_scheduled_at TIMESTAMPTZ,
    escalation_notified BOOLEAN DEFAULT false,
    
    -- ===== COMPLIANCE =====
    compliance_dncr_checked_at TIMESTAMPTZ,
    compliance_hours_valid BOOLEAN,
    recording_disclosure_delivered BOOLEAN,
    
    -- ===== TIMESTAMPS =====
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- TABLE: voice_call_context
-- Stores full context sent to AI agent for each call
-- ============================================

CREATE TABLE voice_call_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- ===== RELATIONSHIP =====
    voice_call_id UUID NOT NULL REFERENCES voice_calls(id) ON DELETE CASCADE,
    
    -- ===== CONTEXT DATA =====
    context_json JSONB NOT NULL,        -- Full compiled prompt context
    sdk_hook_selected TEXT,             -- Selected SDK hook for personalisation
    sdk_case_study_selected TEXT,       -- Selected case study for relevance
    prior_touchpoints_summary TEXT,     -- Summary of previous interactions
    
    -- ===== TIMESTAMPS =====
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- TRIGGER: updated_at auto-update
-- ============================================

CREATE TRIGGER voice_calls_updated_at
    BEFORE UPDATE ON voice_calls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- INDEXES: Performance optimisation
-- ============================================

-- Primary lookups
CREATE INDEX idx_voice_calls_lead_id ON voice_calls(lead_id);
CREATE INDEX idx_voice_calls_client_id ON voice_calls(client_id);

-- Outcome analysis
CREATE INDEX idx_voice_calls_outcome ON voice_calls(outcome);

-- Time-series queries (most recent first)
CREATE INDEX idx_voice_calls_created_at ON voice_calls(created_at DESC);

-- Context lookup
CREATE INDEX idx_voice_call_context_call_id ON voice_call_context(voice_call_id);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE voice_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE voice_call_context ENABLE ROW LEVEL SECURITY;

-- ============================================
-- RLS POLICIES: voice_calls
-- Agency can only see/modify their own calls
-- ============================================

-- SELECT: Client can view their own calls
CREATE POLICY voice_calls_select ON voice_calls
    FOR SELECT
    USING (client_id::text = auth.jwt() ->> 'client_id');

-- INSERT: Client can only create calls for themselves
CREATE POLICY voice_calls_insert ON voice_calls
    FOR INSERT
    WITH CHECK (client_id::text = auth.jwt() ->> 'client_id');

-- UPDATE: Client can only update their own calls
CREATE POLICY voice_calls_update ON voice_calls
    FOR UPDATE
    USING (client_id::text = auth.jwt() ->> 'client_id');

-- ============================================
-- RLS POLICIES: voice_call_context
-- Agency isolation via parent voice_call
-- ============================================

-- SELECT: Client can view context for their calls
CREATE POLICY voice_call_context_select ON voice_call_context
    FOR SELECT
    USING (
        voice_call_id IN (
            SELECT id FROM voice_calls 
            WHERE client_id::text = auth.jwt() ->> 'client_id'
        )
    );

-- INSERT: Client can create context for their calls
CREATE POLICY voice_call_context_insert ON voice_call_context
    FOR INSERT
    WITH CHECK (
        voice_call_id IN (
            SELECT id FROM voice_calls 
            WHERE client_id::text = auth.jwt() ->> 'client_id'
        )
    );

-- UPDATE: Client can update context for their calls
CREATE POLICY voice_call_context_update ON voice_call_context
    FOR UPDATE
    USING (
        voice_call_id IN (
            SELECT id FROM voice_calls 
            WHERE client_id::text = auth.jwt() ->> 'client_id'
        )
    );

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] voice_calls table with all required columns
-- [x] voice_call_context table with JSONB context
-- [x] ON DELETE CASCADE for context when call deleted
-- [x] updated_at trigger using existing function
-- [x] All specified indexes created
-- [x] RLS enabled on both tables
-- [x] Agency-scoped RLS policies (SELECT, INSERT, UPDATE)
-- [x] Rollback DROP statements at top
-- [x] Comments documenting purpose
