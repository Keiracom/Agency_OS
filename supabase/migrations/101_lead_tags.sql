-- Migration: 101_lead_tags.sql
-- Purpose: Wave 1 Dave-knowledge capture — append-only lead rejection tags
-- Append-only: multiple rows per domain allowed; latest wins via ORDER BY tagged_at DESC LIMIT 1

CREATE TABLE IF NOT EXISTS public.lead_tags (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  domain           text NOT NULL,
  business_name    text,                             -- snapshot at tag time
  stage            text NOT NULL,                    -- stage1_discovery..stage11_card | manual
  reason_category  text NOT NULL,                    -- enum enforced at app layer
  detail           text NOT NULL,                    -- free-form
  criteria         jsonb,                            -- optional structured (nullable)
  tagged_at        timestamptz NOT NULL DEFAULT now(),
  tagged_by        text NOT NULL DEFAULT 'dave'
);

CREATE INDEX IF NOT EXISTS lead_tags_domain_idx  ON public.lead_tags (domain);
CREATE INDEX IF NOT EXISTS lead_tags_stage_idx   ON public.lead_tags (stage);
CREATE INDEX IF NOT EXISTS lead_tags_reason_idx  ON public.lead_tags (reason_category);
CREATE INDEX IF NOT EXISTS lead_tags_tagged_idx  ON public.lead_tags (tagged_at DESC);
