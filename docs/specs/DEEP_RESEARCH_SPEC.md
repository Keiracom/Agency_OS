# DEEP_RESEARCH_SPEC.md
**Status:** APPROVED
**Purpose:** Implement "Tiered Enrichment" for Hot Leads (ALS > 85) using Apify + Claude.

## 1. DATABASE SCHEMA
**Target:** `supabase/migrations/`
**File:** `021_deep_research.sql`

```sql
-- Add Deep Research fields to Lead model
ALTER TABLE leads ADD COLUMN deep_research_data JSONB DEFAULT '{}';
ALTER TABLE leads ADD COLUMN deep_research_run_at TIMESTAMPTZ;

-- Track social posts found (Audit trail)
CREATE TABLE lead_social_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    source TEXT NOT NULL, -- 'linkedin', 'twitter', 'news'
    post_content TEXT,
    post_date DATE,
    summary_hook TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_lead_social_posts_lead ON lead_social_posts(lead_id);
```

## 2. MODEL UPDATES

**File:** `src/models/lead.py`
- Add `deep_research_data` (JSONB) and `deep_research_run_at` (DateTime) columns.
- Add relationship `social_posts` to the new `LeadSocialPost` model.

**File:** `src/models/lead_social_post.py`
- Create this new model file mapping to the `lead_social_posts` table.

## 3. ENGINE UPDATE (Scout)

**File:** `src/engines/scout.py`
- Add method `perform_deep_research(self, db, lead_id)`
- Logic: Fetch lead -> If linkedin_url exists -> Call DeepResearchSkill -> Save results to DB.

## 4. SKILL IMPLEMENTATION

**File:** `src/agents/skills/research_skills.py`
- Create `DeepResearchSkill` class.
- It should use `ApifyIntegration` to scrape last 3 LinkedIn posts.
- It should use `AnthropicIntegration` to generate a 1-sentence icebreaker hook from those posts.
