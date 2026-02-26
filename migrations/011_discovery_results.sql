-- Migration: 011_discovery_results.sql
-- Purpose: Create discovery_results table for campaign discovery tracking
-- Phase: E2E Test Infrastructure
-- Date: 2025-02-26

-- ============================================
-- discovery_results table
-- Stores raw discovery results from campaign activation
-- Used by src/enrichment/campaign_trigger.py
-- ============================================

CREATE TABLE IF NOT EXISTS discovery_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Campaign reference
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    
    -- Business identification
    abn TEXT,
    business_name TEXT,
    trading_name TEXT,
    
    -- Discovery metadata
    source TEXT NOT NULL,  -- e.g., 'abn_lookup', 'bright_data', 'serp_maps'
    raw_data JSONB DEFAULT '{}'::jsonb,
    dedup_hash TEXT,
    
    -- Filter results
    passed_filters BOOLEAN NOT NULL DEFAULT false,
    filter_reason TEXT,  -- Reason if filtered out
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_discovery_results_campaign_id 
    ON discovery_results(campaign_id);

CREATE INDEX IF NOT EXISTS idx_discovery_results_dedup_hash 
    ON discovery_results(dedup_hash);

CREATE INDEX IF NOT EXISTS idx_discovery_results_passed 
    ON discovery_results(campaign_id, passed_filters) 
    WHERE passed_filters = true;

-- Prevent duplicate discoveries within same campaign
CREATE UNIQUE INDEX IF NOT EXISTS idx_discovery_results_unique_dedup 
    ON discovery_results(campaign_id, dedup_hash) 
    WHERE dedup_hash IS NOT NULL;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_discovery_results_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_discovery_results_updated_at ON discovery_results;
CREATE TRIGGER trigger_discovery_results_updated_at
    BEFORE UPDATE ON discovery_results
    FOR EACH ROW
    EXECUTE FUNCTION update_discovery_results_updated_at();

-- ============================================
-- VERIFICATION
-- ============================================
-- Columns match campaign_trigger.py _store_discovery_results():
-- [x] campaign_id - UUID FK to campaigns
-- [x] abn - TEXT
-- [x] business_name - TEXT
-- [x] trading_name - TEXT
-- [x] source - TEXT
-- [x] raw_data - JSONB
-- [x] dedup_hash - TEXT
-- [x] passed_filters - BOOLEAN
-- [x] filter_reason - TEXT
