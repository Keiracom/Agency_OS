-- Migration 028: Pipeline drop reasons
-- Extends rejection_reason_type ENUM with pipeline-specific values
-- and adds rejection_phase column to separate pipeline vs outreach rejections.

-- Add pipeline drop reasons to existing ENUM
ALTER TYPE rejection_reason_type ADD VALUE IF NOT EXISTS 'enterprise_or_chain';
ALTER TYPE rejection_reason_type ADD VALUE IF NOT EXISTS 'no_dm_found';
ALTER TYPE rejection_reason_type ADD VALUE IF NOT EXISTS 'score_below_gate';
ALTER TYPE rejection_reason_type ADD VALUE IF NOT EXISTS 'stage_failed';
ALTER TYPE rejection_reason_type ADD VALUE IF NOT EXISTS 'viability';

-- Add rejection_phase column to separate pipeline vs outreach rejections
ALTER TABLE leads ADD COLUMN IF NOT EXISTS rejection_phase TEXT;
COMMENT ON COLUMN leads.rejection_phase IS 'pipeline or outreach — separates pipeline quality drops from sales rejections';
