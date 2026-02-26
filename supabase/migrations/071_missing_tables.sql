-- Migration: 071_missing_tables.sql
-- Bug #12 Fix: Create all missing tables found during full audit
-- CEO Directive #100 - LAW I-A Full Audit Applied
--
-- Missing tables found:
-- 1. digest_logs (Phase H, Item 44 - Daily Digest Email)
-- 2. icp_refinement_log (Phase 19 - ICP Refinement from CIS)

-- ============================================
-- TABLE: digest_logs
-- Purpose: Track sent digest emails to clients
-- Phase: H (Client Transparency)
-- ============================================
CREATE TABLE IF NOT EXISTS digest_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Client reference
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    
    -- Digest metadata
    digest_date DATE NOT NULL,
    digest_type TEXT NOT NULL DEFAULT 'daily',
    
    -- Recipients (list of email addresses)
    recipients JSONB NOT NULL DEFAULT '[]'::jsonb,
    
    -- Content snapshot - metrics at time of digest
    metrics_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Content summary - what content was sent
    content_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- Delivery status
    status TEXT NOT NULL DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    
    -- Engagement tracking
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps (TimestampMixin)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for digest_logs
CREATE INDEX IF NOT EXISTS idx_digest_logs_client_id ON digest_logs(client_id);
CREATE INDEX IF NOT EXISTS idx_digest_logs_digest_date ON digest_logs(digest_date);
CREATE INDEX IF NOT EXISTS idx_digest_logs_status ON digest_logs(status);
CREATE INDEX IF NOT EXISTS idx_digest_logs_client_date ON digest_logs(client_id, digest_date);

-- ============================================
-- TABLE: icp_refinement_log
-- Purpose: Audit log of WHO pattern refinements applied to ICP searches
-- Phase: 19 (ICP Refinement from CIS)
-- ============================================
CREATE TABLE IF NOT EXISTS icp_refinement_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign keys
    client_id UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    pattern_id UUID NOT NULL REFERENCES conversion_patterns(id) ON DELETE CASCADE,
    
    -- Original ICP criteria before WHO refinement
    base_criteria JSONB NOT NULL,
    
    -- Final criteria after WHO refinement applied
    refined_criteria JSONB NOT NULL,
    
    -- Array of refinement actions taken
    refinements_applied JSONB NOT NULL,
    
    -- WHO pattern confidence at time of refinement
    confidence FLOAT NOT NULL,
    
    -- When the refinement was applied
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Soft delete
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps (TimestampMixin)
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes for icp_refinement_log
CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_client_id ON icp_refinement_log(client_id);
CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_pattern_id ON icp_refinement_log(pattern_id);
CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_applied_at ON icp_refinement_log(applied_at);
CREATE INDEX IF NOT EXISTS idx_icp_refinement_log_deleted_at ON icp_refinement_log(deleted_at) WHERE deleted_at IS NULL;

-- ============================================
-- AUDIT SUMMARY
-- ============================================
-- Tables checked: 30 models in src/models/*.py
-- Tables existing: 88 tables in public schema
-- Tables missing: 2
--   1. digest_logs
--   2. icp_refinement_log
-- 
-- All other model tables already exist in database.
