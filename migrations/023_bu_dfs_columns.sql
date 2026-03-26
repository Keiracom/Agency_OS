-- Migration 023: Add DFS intelligence columns to business_universe
-- Directive #257

-- ── Group A: DFS Domains by Technology (S1 discovery) ──────────────────────
ALTER TABLE business_universe
    ADD COLUMN IF NOT EXISTS dfs_technologies jsonb,
    ADD COLUMN IF NOT EXISTS dfs_discovery_sources text[],
    ADD COLUMN IF NOT EXISTS dfs_technology_detected_at timestamptz;

-- ── Group B: DFS Domain Rank Overview (S3) ─────────────────────────────────
ALTER TABLE business_universe
    ADD COLUMN IF NOT EXISTS dfs_organic_etv numeric,
    ADD COLUMN IF NOT EXISTS dfs_paid_etv numeric,
    ADD COLUMN IF NOT EXISTS dfs_organic_keywords integer,
    ADD COLUMN IF NOT EXISTS dfs_paid_keywords integer,
    ADD COLUMN IF NOT EXISTS dfs_organic_pos_1 integer,
    ADD COLUMN IF NOT EXISTS dfs_organic_pos_2_3 integer,
    ADD COLUMN IF NOT EXISTS dfs_organic_pos_4_10 integer,
    ADD COLUMN IF NOT EXISTS dfs_organic_pos_11_20 integer,
    ADD COLUMN IF NOT EXISTS dfs_rank_fetched_at timestamptz;

-- ── Group C: DFS Domain Technologies (S3) ──────────────────────────────────
ALTER TABLE business_universe
    ADD COLUMN IF NOT EXISTS tech_stack text[],
    ADD COLUMN IF NOT EXISTS tech_categories jsonb,
    ADD COLUMN IF NOT EXISTS tech_stack_depth integer,
    ADD COLUMN IF NOT EXISTS tech_gaps text[],
    ADD COLUMN IF NOT EXISTS dfs_tech_fetched_at timestamptz;

-- ── Group D: Stage 4 Scoring sub-scores (v5 budget/pain/gap/fit) ───────────
ALTER TABLE business_universe
    ADD COLUMN IF NOT EXISTS score_budget integer,
    ADD COLUMN IF NOT EXISTS score_pain integer,
    ADD COLUMN IF NOT EXISTS score_gap integer,
    ADD COLUMN IF NOT EXISTS score_fit integer;

-- ── Group E: Pipeline + cost meta ──────────────────────────────────────────
ALTER TABLE business_universe
    ADD COLUMN IF NOT EXISTS pipeline_updated_at timestamptz,
    ADD COLUMN IF NOT EXISTS enrichment_cost_usd numeric;

-- ── Indexes ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_bu_dfs_paid_etv ON business_universe(dfs_paid_etv);
CREATE INDEX IF NOT EXISTS idx_bu_dfs_organic_etv ON business_universe(dfs_organic_etv);
CREATE INDEX IF NOT EXISTS idx_bu_tech_stack_depth ON business_universe(tech_stack_depth);
CREATE INDEX IF NOT EXISTS idx_bu_score_budget ON business_universe(score_budget);
CREATE INDEX IF NOT EXISTS idx_bu_score_pain ON business_universe(score_pain);
CREATE INDEX IF NOT EXISTS idx_bu_score_gap ON business_universe(score_gap);
CREATE INDEX IF NOT EXISTS idx_bu_score_fit ON business_universe(score_fit);
