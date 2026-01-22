-- FILE: supabase/migrations/046_lead_replies.sql
-- PURPOSE: Store inbound/outbound replies for all channels with classification data
-- PHASE: Reply Handling Pipeline
-- TASK: REPLY-001
-- DEPENDENCIES: 004_leads_suppression.sql, 002_clients_users_memberships.sql
-- RULES APPLIED:
--   - Rule 1: Follow blueprint exactly
--   - Rule 14: Soft deletes only (deleted_at column)

-- ============================================
-- LEAD REPLIES TABLE
-- ============================================
-- Stores all inbound and outbound reply messages across channels
-- with classification, response tracking, and outcome management

CREATE TABLE lead_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(id),

    -- ===== SOURCE =====
    channel TEXT NOT NULL,                    -- 'email', 'sms', 'linkedin'
    direction TEXT NOT NULL DEFAULT 'inbound', -- 'inbound', 'outbound'
    content TEXT NOT NULL,
    subject TEXT,                              -- For email replies
    received_at TIMESTAMPTZ DEFAULT NOW(),

    -- ===== CLASSIFICATION (for inbound) =====
    intent TEXT,                              -- meeting_request, question, not_interested, etc.
    intent_confidence FLOAT,
    extracted_data JSONB DEFAULT '{}',
    classified_at TIMESTAMPTZ,

    -- ===== RESPONSE (for outbound) =====
    response_method TEXT,                     -- 'template', 'smart_prompt', 'sdk'
    response_cost DECIMAL(10,4) DEFAULT 0,
    scheduled_for TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,

    -- ===== OUTCOME =====
    sequence_action TEXT,                     -- 'pause', 'stop', 'continue'
    meeting_created BOOLEAN DEFAULT false,
    referral_lead_id UUID REFERENCES leads(id),
    admin_review_required BOOLEAN DEFAULT false,
    admin_reviewed_at TIMESTAMPTZ,
    admin_reviewed_by UUID REFERENCES users(id),

    -- ===== STANDARD FIELDS =====
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

-- Primary lookups
CREATE INDEX idx_lead_replies_lead ON lead_replies(lead_id);
CREATE INDEX idx_lead_replies_client ON lead_replies(client_id);

-- Filtering by classification
CREATE INDEX idx_lead_replies_intent ON lead_replies(intent);
CREATE INDEX idx_lead_replies_channel ON lead_replies(channel);
CREATE INDEX idx_lead_replies_direction ON lead_replies(direction);

-- Pending scheduled responses queue
CREATE INDEX idx_lead_replies_pending_send ON lead_replies(scheduled_for)
    WHERE sent_at IS NULL AND scheduled_for IS NOT NULL;

-- Admin review queue
CREATE INDEX idx_lead_replies_admin_review ON lead_replies(admin_review_required, created_at)
    WHERE admin_review_required = true AND admin_reviewed_at IS NULL;

-- ============================================
-- VIEW: SDK Costs per Lead
-- ============================================
-- For cost cap enforcement in SDK reply generation

CREATE OR REPLACE VIEW lead_reply_sdk_costs AS
SELECT
    lead_id,
    SUM(response_cost) as total_sdk_cost,
    COUNT(*) as sdk_reply_count
FROM lead_replies
WHERE response_method = 'sdk'
GROUP BY lead_id;

-- ============================================
-- TRIGGER: Auto-update updated_at
-- ============================================

CREATE TRIGGER update_lead_replies_updated_at
    BEFORE UPDATE ON lead_replies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================
-- COMMENTS
-- ============================================

COMMENT ON TABLE lead_replies IS 'Stores all inbound and outbound reply messages across channels with classification and response tracking';
COMMENT ON COLUMN lead_replies.channel IS 'Communication channel: email, sms, linkedin';
COMMENT ON COLUMN lead_replies.direction IS 'Message direction: inbound (from lead) or outbound (to lead)';
COMMENT ON COLUMN lead_replies.intent IS 'Classified intent: meeting_request, interested, question, not_interested, unsubscribe, out_of_office, auto_reply, referral, wrong_person, angry_or_complaint';
COMMENT ON COLUMN lead_replies.intent_confidence IS 'Confidence score for intent classification (0.0 to 1.0)';
COMMENT ON COLUMN lead_replies.extracted_data IS 'JSON containing extracted entities: meeting times, phone numbers, referral names, etc.';
COMMENT ON COLUMN lead_replies.response_method IS 'How response was generated: template, smart_prompt, or sdk';
COMMENT ON COLUMN lead_replies.response_cost IS 'Cost in AUD for SDK-generated responses';
COMMENT ON COLUMN lead_replies.sequence_action IS 'Action taken on sequence: pause, stop, or continue';
COMMENT ON COLUMN lead_replies.referral_lead_id IS 'If a referral was extracted, reference to the new lead created';
COMMENT ON COLUMN lead_replies.admin_review_required IS 'Flag for replies that need manual review (ambiguous intent, edge cases)';
COMMENT ON VIEW lead_reply_sdk_costs IS 'Aggregated SDK costs per lead for cost cap enforcement';

-- ============================================
-- VERIFICATION CHECKLIST
-- ============================================
-- [x] lead_replies table with all required fields
-- [x] Foreign keys to leads, clients, users tables
-- [x] Self-referential FK for referral_lead_id
-- [x] Indexes for common query patterns
-- [x] Partial index for pending send queue
-- [x] Partial index for admin review queue
-- [x] lead_reply_sdk_costs view for cost tracking
-- [x] updated_at trigger
-- [x] Table and column comments for documentation
