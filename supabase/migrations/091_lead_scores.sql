-- 091_lead_scores.sql
-- Directive #217: Add opportunity_score and opportunity_reason to leads
ALTER TABLE leads
    ADD COLUMN IF NOT EXISTS opportunity_score INTEGER,
    ADD COLUMN IF NOT EXISTS opportunity_reason TEXT;

COMMENT ON COLUMN leads.opportunity_score IS 'Opportunity score 0-100. High = real business + low digital presence. Directive #217.';
COMMENT ON COLUMN leads.opportunity_reason IS 'Plain English reason for opportunity score. Shown on dashboard. Directive #217.';
