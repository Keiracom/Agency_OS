-- ============================================================================
-- 20260526_keiracom_atomization_pilot.sql
--
-- Atomization pilot Week 1 schema lock — Agency_OS-atomization-pilot-week1.
-- Per ceo:atomization_architecture_v1 (RATIFIED-CEO 2026-05-26T11:25:00Z)
-- + PR #1178 proposal doc (docs/architecture/design/
-- atomization_pilot_schema_lock_proposal.md, merged 2026-05-26T11:53Z).
--
-- Sibling migrations:
--   20260525_keiracom_tenant_metering.sql  (PR #1137)
--   20260526_keiracom_tenant_budgets.sql   (PR #1173)
--
-- Schema (atom_schema_v1) — 7 canonical fields:
--   trigger_condition  → JSONB (structured predicate; vocabulary frozen
--                        at app layer via src/keiracom_system/atomization/
--                        schema.py; rejects free-text per HARD constraint)
--   content            → TEXT
--   anti_pattern       → TEXT (nullable)
--   example            → TEXT (nullable)
--   provenance         → JSONB {source, freshness, confidence, last_validated}
--   supersession_edges → adjacency table keiracom_atom_supersession_edges
--   composition_tags   → JSONB {domain, concern, applicable_context};
--                        vocabulary frozen at app layer; 288 combinations
--                        + 7 relationship types per dispatch reference
--
-- Embeddings: VECTOR(384) — BGE-small-en-v1.5 via TEIClient (PR #1133).
--
-- Hard constraints enforced:
--   1. Tenant-prefix guard at read+write (app layer + CI guard)
--   2. Composition tag vocabulary frozen (app layer)
--   3. Relationship-type vocabulary capped single-digit V1 (app layer)
--   4. Cold archive never consumed by agents (state='cold_archive' flag;
--      explicit recall API only — not in this migration's scope)
--   5. Composer output never reaches agent reasoning input (enforced by
--      separate Composer module + future CI guard; not in this schema)
--
-- KEI-87 bypass: SET LOCAL agency_os.callsign = 'dave' required for
-- public-schema table creation; same pattern as PR #1137/1173.
-- ============================================================================

SET LOCAL agency_os.callsign = 'dave';

-- pgvector prerequisite — fail-loud if not enabled rather than silent
-- VECTOR-type creation failure on the table below.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) THEN
        RAISE EXCEPTION
            'pgvector extension NOT enabled — atomization pilot requires '
            'pgvector for VECTOR(384) embedding column. Run "CREATE EXTENSION '
            'IF NOT EXISTS vector;" before applying this migration.';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Atom Store — primary atom table
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.keiracom_atoms (
    atom_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL,

    -- atom_schema_v1 7-field core (per ceo:atomization_architecture_v1)
    trigger_condition  JSONB        NOT NULL,
    content            TEXT         NOT NULL CHECK (length(content) > 0),
    anti_pattern       TEXT,
    example            TEXT,
    provenance         JSONB        NOT NULL,
    composition_tags   JSONB        NOT NULL DEFAULT '{}'::jsonb,

    -- Embedding for retrieval (BGE-small-en-v1.5 via TEIClient PR #1133).
    -- 384 dimensions matches DEFAULT_MODEL_DIM in tei_client.py.
    content_embedding  VECTOR(384)  NOT NULL,

    -- Atom-level metadata.
    schema_version     SMALLINT     NOT NULL DEFAULT 1,
    state              TEXT         NOT NULL DEFAULT 'active'
        CHECK (state IN ('active', 'superseded', 'cold_archive')),

    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    FOREIGN KEY (tenant_id) REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE
);

-- Tenant isolation + state filter — every retrieval query hits this index.
CREATE INDEX IF NOT EXISTS idx_keiracom_atoms_tenant_active
    ON public.keiracom_atoms (tenant_id)
    WHERE state = 'active';

-- pgvector HNSW for vector similarity (cosine for BGE-small).
CREATE INDEX IF NOT EXISTS idx_keiracom_atoms_embedding_hnsw
    ON public.keiracom_atoms USING hnsw (content_embedding vector_cosine_ops);

-- Composition tag retrieval — GIN on JSONB for tag predicate queries.
CREATE INDEX IF NOT EXISTS idx_keiracom_atoms_composition_tags
    ON public.keiracom_atoms USING gin (composition_tags);

-- Trigger: refresh updated_at on UPDATE.
CREATE OR REPLACE FUNCTION public.keiracom_atoms_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_keiracom_atoms_updated_at
    ON public.keiracom_atoms;

CREATE TRIGGER trg_keiracom_atoms_updated_at
    BEFORE UPDATE ON public.keiracom_atoms
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_atoms_set_updated_at();

-- ----------------------------------------------------------------------------
-- Supersession edges (content-level only per hard constraint)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.keiracom_atom_supersession_edges (
    edge_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL,
    predecessor_atom   UUID         NOT NULL,
    successor_atom     UUID         NOT NULL,
    relationship_type  TEXT         NOT NULL,
    confidence         REAL         NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CHECK (predecessor_atom <> successor_atom),

    FOREIGN KEY (tenant_id)        REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (predecessor_atom) REFERENCES public.keiracom_atoms(atom_id)     ON DELETE CASCADE,
    FOREIGN KEY (successor_atom)   REFERENCES public.keiracom_atoms(atom_id)     ON DELETE CASCADE,

    UNIQUE (predecessor_atom, successor_atom, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_keiracom_atom_edges_predecessor
    ON public.keiracom_atom_supersession_edges (predecessor_atom);
CREATE INDEX IF NOT EXISTS idx_keiracom_atom_edges_successor
    ON public.keiracom_atom_supersession_edges (successor_atom);
CREATE INDEX IF NOT EXISTS idx_keiracom_atom_edges_tenant
    ON public.keiracom_atom_supersession_edges (tenant_id);

-- ----------------------------------------------------------------------------
-- Atomizer job log (metering + audit)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.keiracom_atomizer_jobs (
    job_id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL,
    source_ref         TEXT         NOT NULL,
    source_kind        TEXT         NOT NULL
        CHECK (source_kind IN ('skill', 'manual', 'governance_doc', 'discovery_log', 'session')),

    atomizer_model     TEXT         NOT NULL,
    atomizer_temp      REAL         NOT NULL DEFAULT 0
        CHECK (atomizer_temp >= 0 AND atomizer_temp <= 2),
    atomizer_tokens_in BIGINT       NOT NULL DEFAULT 0,
    atomizer_tokens_out BIGINT      NOT NULL DEFAULT 0,
    atomizer_latency_ms INTEGER     NOT NULL DEFAULT 0,
    atoms_produced     INTEGER      NOT NULL DEFAULT 0,

    verifier_model     TEXT,
    verifier_tokens_in BIGINT,
    verifier_tokens_out BIGINT,
    verifier_latency_ms INTEGER,
    verifier_flags     JSONB        NOT NULL DEFAULT '[]'::jsonb,

    status             TEXT         NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'atomizer_done', 'verifier_done', 'ratified', 'failed')),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    FOREIGN KEY (tenant_id) REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_keiracom_atomizer_jobs_tenant_status
    ON public.keiracom_atomizer_jobs (tenant_id, status);

CREATE INDEX IF NOT EXISTS idx_keiracom_atomizer_jobs_source
    ON public.keiracom_atomizer_jobs (source_ref);

CREATE OR REPLACE FUNCTION public.keiracom_atomizer_jobs_set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_keiracom_atomizer_jobs_updated_at
    ON public.keiracom_atomizer_jobs;

CREATE TRIGGER trg_keiracom_atomizer_jobs_updated_at
    BEFORE UPDATE ON public.keiracom_atomizer_jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.keiracom_atomizer_jobs_set_updated_at();
