-- Migration 073: Create industry_keywords table with seed data
-- Bug #22 fix: KeywordExpander requires this table for discovery queries
-- CEO Directive #110

-- =====================================================
-- CREATE TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS industry_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry_slug TEXT UNIQUE NOT NULL,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    maps_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    discovery_mode TEXT DEFAULT 'both' CHECK (discovery_mode IN ('abn', 'maps', 'both')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_industry_keywords_slug ON industry_keywords(industry_slug);

-- =====================================================
-- SEED DATA: Agency verticals for Australian market
-- Keywords optimized for ABN search and Google Maps Business discovery
-- =====================================================

INSERT INTO industry_keywords (industry_slug, keywords, maps_categories, discovery_mode) VALUES

-- Marketing Agency
('marketing_agency', 
 '["marketing agency", "digital marketing", "marketing consultant", "marketing services", "brand marketing", "growth marketing", "performance marketing", "integrated marketing", "marketing strategy", "marketing solutions"]'::jsonb,
 '["Marketing agency", "Marketing consultant", "Business marketing service", "Internet marketing service"]'::jsonb,
 'both'),

-- Digital Agency
('digital_agency',
 '["digital agency", "web design agency", "digital marketing agency", "digital transformation", "digital solutions", "digital consulting", "web development agency", "digital services", "online marketing agency", "ecommerce agency"]'::jsonb,
 '["Web designer", "Internet marketing service", "Software company", "Website designer"]'::jsonb,
 'both'),

-- Advertising Agency
('advertising_agency',
 '["advertising agency", "ad agency", "creative advertising", "media buying", "advertising services", "display advertising", "advertising consultant", "ad campaign", "brand advertising", "advertising solutions"]'::jsonb,
 '["Advertising agency", "Marketing agency", "Media company", "Marketing consultant"]'::jsonb,
 'both'),

-- SEO Agency
('seo_agency',
 '["seo agency", "search engine optimization", "seo services", "seo consultant", "local seo", "seo company", "organic search", "seo marketing", "search marketing", "seo specialist"]'::jsonb,
 '["Internet marketing service", "Marketing consultant", "Marketing agency", "Web designer"]'::jsonb,
 'maps'),

-- PR Agency
('pr_agency',
 '["public relations", "pr agency", "media relations", "pr consultant", "communications agency", "pr services", "reputation management", "crisis communications", "press relations", "pr firm"]'::jsonb,
 '["Public relations firm", "Marketing consultant", "Communications firm", "Marketing agency"]'::jsonb,
 'both'),

-- Creative Agency
('creative_agency',
 '["creative agency", "design agency", "brand agency", "creative services", "creative studio", "graphic design agency", "branding agency", "creative consultant", "visual design", "creative solutions"]'::jsonb,
 '["Graphic designer", "Marketing agency", "Advertising agency", "Design agency"]'::jsonb,
 'both'),

-- Media Agency
('media_agency',
 '["media agency", "media buying", "media planning", "media services", "social media agency", "paid media", "media consultant", "media solutions", "digital media agency", "media management"]'::jsonb,
 '["Media company", "Advertising agency", "Marketing agency", "Internet marketing service"]'::jsonb,
 'both'),

-- Content Agency
('content_agency',
 '["content agency", "content marketing", "content creation", "content strategy", "content services", "copywriting agency", "content production", "content consultant", "video content", "content solutions"]'::jsonb,
 '["Marketing agency", "Marketing consultant", "Video production service", "Advertising agency"]'::jsonb,
 'both'),

-- Social Media Agency
('social_media_agency',
 '["social media agency", "social media marketing", "social media management", "social media consultant", "social media services", "influencer marketing", "social media strategy", "community management", "social advertising", "social media solutions"]'::jsonb,
 '["Internet marketing service", "Marketing agency", "Marketing consultant", "Advertising agency"]'::jsonb,
 'maps'),

-- Web Design Agency
('web_design_agency',
 '["web design", "website design", "web development", "web designer", "website development", "web agency", "web solutions", "website builder", "ui design", "ux design"]'::jsonb,
 '["Web designer", "Website designer", "Software company", "Internet marketing service"]'::jsonb,
 'maps'),

-- Branding Agency
('branding_agency',
 '["branding agency", "brand strategy", "brand identity", "brand consultant", "brand design", "brand development", "rebranding", "brand positioning", "corporate branding", "brand services"]'::jsonb,
 '["Marketing consultant", "Graphic designer", "Marketing agency", "Advertising agency"]'::jsonb,
 'both'),

-- Video Production
('video_production',
 '["video production", "video agency", "corporate video", "video marketing", "video services", "film production", "video content", "commercial production", "video editing", "animation studio"]'::jsonb,
 '["Video production service", "Film production company", "Advertising agency", "Marketing agency"]'::jsonb,
 'maps')

ON CONFLICT (industry_slug) DO UPDATE SET
    keywords = EXCLUDED.keywords,
    maps_categories = EXCLUDED.maps_categories,
    discovery_mode = EXCLUDED.discovery_mode,
    updated_at = NOW();

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE industry_keywords IS 'Lookup table for industry-specific search keywords used by KeywordExpander in discovery pipeline';
COMMENT ON COLUMN industry_keywords.industry_slug IS 'Unique identifier for the industry vertical (e.g., marketing_agency)';
COMMENT ON COLUMN industry_keywords.keywords IS 'JSON array of ABN/business name search keywords';
COMMENT ON COLUMN industry_keywords.maps_categories IS 'JSON array of Google Maps category terms for GMB discovery';
COMMENT ON COLUMN industry_keywords.discovery_mode IS 'Recommended discovery mode: abn (ABN-first), maps (Maps-first), or both (parallel)';

-- =====================================================
-- VERIFICATION
-- =====================================================
-- [x] Table created with correct schema for KeywordExpander
-- [x] Unique constraint on industry_slug
-- [x] Index for fast lookups
-- [x] 12 agency verticals seeded with 10 keywords each
-- [x] Maps categories included for GMB discovery
-- [x] discovery_mode column for QueryTranslator.determine_mode()
-- [x] Upsert logic for idempotent re-runs
