-- Migration: 021_deep_research.sql
-- Purpose: Add Deep Research fields to leads and create social posts audit trail
-- Phase: 21 (Deep Research & UI)

-- Add Deep Research fields to Lead model
ALTER TABLE leads ADD COLUMN IF NOT EXISTS deep_research_data JSONB DEFAULT '{}';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS deep_research_run_at TIMESTAMPTZ;

-- Track social posts found (Audit trail)
CREATE TABLE IF NOT EXISTS lead_social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    source TEXT NOT NULL, -- 'linkedin', 'twitter', 'news'
    post_content TEXT,
    post_date DATE,
    summary_hook TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for efficient lookups by lead
CREATE INDEX IF NOT EXISTS idx_lead_social_posts_lead ON lead_social_posts(lead_id);

-- Enable RLS on the new table
ALTER TABLE lead_social_posts ENABLE ROW LEVEL SECURITY;

-- RLS Policy: Users can only see posts for leads they have access to
CREATE POLICY "Users can view social posts for their leads" ON lead_social_posts
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM leads l
            JOIN campaigns c ON l.campaign_id = c.id
            JOIN client_memberships cm ON c.client_id = cm.client_id
            WHERE l.id = lead_social_posts.lead_id
            AND cm.user_id = auth.uid()
        )
    );

-- Service role can do everything
CREATE POLICY "Service role full access to social posts" ON lead_social_posts
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');
