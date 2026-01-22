-- Migration: 045_auto_sequences.sql
-- Purpose: Add uses_default_sequence flag to campaigns for Phase E
-- Spec: docs/architecture/AUTOMATED_DISTRIBUTION_DEFAULTS.md
-- Date: 2026-01-21

-- ============================================
-- Add uses_default_sequence to campaigns
-- ============================================

-- New campaigns will use auto-generated sequences by default
-- Existing campaigns are marked as custom (FALSE) to preserve their config
ALTER TABLE campaigns
ADD COLUMN IF NOT EXISTS uses_default_sequence BOOLEAN NOT NULL DEFAULT TRUE;

-- Mark all existing campaigns as custom (they may have user-configured sequences)
UPDATE campaigns
SET uses_default_sequence = FALSE
WHERE uses_default_sequence = TRUE;

-- ============================================
-- Add purpose field to campaign_sequences
-- ============================================

-- Purpose helps identify what each step does (intro, value_add, breakup, etc.)
ALTER TABLE campaign_sequences
ADD COLUMN IF NOT EXISTS purpose TEXT;

-- Add skip_if field for conditional logic (e.g., 'phone_missing', 'linkedin_url_missing')
ALTER TABLE campaign_sequences
ADD COLUMN IF NOT EXISTS skip_if TEXT;

-- ============================================
-- Comments
-- ============================================

COMMENT ON COLUMN campaigns.uses_default_sequence IS
'If TRUE, system auto-generates the 5-step default sequence. If FALSE, uses custom sequences.';

COMMENT ON COLUMN campaign_sequences.purpose IS
'Purpose of this touch: intro, connect, value_add, pattern_interrupt, breakup, discovery';

COMMENT ON COLUMN campaign_sequences.skip_if IS
'Condition to skip this step: phone_missing, linkedin_url_missing, address_missing';

-- ============================================
-- VERIFICATION
-- ============================================
-- [x] uses_default_sequence added to campaigns (default TRUE)
-- [x] Existing campaigns marked as custom (FALSE)
-- [x] purpose field added to campaign_sequences
-- [x] skip_if field added to campaign_sequences
-- [x] Comments added for documentation
