-- KEI-68 — Living governance layer: rules in Supabase, not static markdown.
--
-- Establishes the durable primitive. Agents + enforcer query this table on
-- session start (follow-up KEIs ship the consumers — this PR ships the
-- table + seed + read API only).
--
-- Rules are append-only-ish: deprecated rules stay in the table with
-- deprecated_at + deprecated_reason set, active flipped to FALSE. History
-- preserved; active set queryable.

CREATE TABLE IF NOT EXISTS public.governance_rules (
    id                 TEXT PRIMARY KEY,
    category           TEXT NOT NULL,
    rule               TEXT NOT NULL,
    active             BOOLEAN NOT NULL DEFAULT TRUE,
    deprecated_at      TIMESTAMPTZ,
    deprecated_reason  TEXT,
    deprecated_by      TEXT,
    source_doc         TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_governance_rules_active_category
    ON public.governance_rules (category) WHERE active = TRUE;

-- Prevent duplicate rule statements within the same category (case-insensitive).
CREATE UNIQUE INDEX IF NOT EXISTS uq_governance_rules_category_rule
    ON public.governance_rules (category, lower(rule));

COMMENT ON TABLE public.governance_rules IS
    'KEI-68 — single source of truth for living governance rules. Agents/enforcer query active rows on session start.';
