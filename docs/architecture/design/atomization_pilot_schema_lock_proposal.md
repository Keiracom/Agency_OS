# Atomization Pilot — Schema Lock Proposal (Week 1)

**Owner:** Orion (per Elliot dispatch 2026-05-26)
**Phase:** Atomization pilot Week 1
**Status:** DESIGN PROPOSAL — awaiting (1) Elliot 48-hour design report on grain policy + controlled vocabulary + schema versioning semantics; (2) Gemini key in Vault at `secret/keiracom/gemini/api_key`
**Date:** 2026-05-26
**Filed under:** Agency_OS-atomization-pilot-week1
**bd:** issues filed separately for each Week 1 acceptance criterion (this doc covers acceptance criterion 1: schema lock)

## Canonical anchor (verbatim per audit-dispatch checklist)

`ceo:atomization_architecture_v1` (queried 2026-05-26 ~11:39 UTC, RATIFIED-CEO 2026-05-26T11:25:00Z, CONCUR-Full Elliot + Viktor + Dave-author-exclusion):

```
atom_schema_v1.fields = [
  "trigger_condition",
  "content",
  "anti_pattern",
  "example",
  "provenance (source/freshness/confidence/last_validated)",
  "supersession_edges",
  "composition_tags (domain/concern/applicable_context)"
]
hard_constraints = [
  "Composer output never reaches agent reasoning input",
  "Tenant-prefix guard on atom-store read AND write paths (mirrors cache-discipline guard pattern)",
  "Composition tag vocabulary frozen at pilot scope; extensions require ratification",
  "Relationship-type vocabulary capped single-digit count v1",
  "Cold archive never consumed by agents during reasoning"
]
```

Five-component architecture (per canonical):
1. **Atomizer** (LLM service — Gemini Flash for Dave pilot)
2. **Atom Store** (Postgres+pgvector via Hindsight substrate)
3. **MAL Retriever**
4. **Composer** (endpoints only)
5. **Endpoint Translator**

## §1 Scope + non-goals

### In scope (Week 1)
- Postgres schema `keiracom_atom_store` + supporting tables (this doc)
- Migration script (sibling to `20260525_keiracom_tenant_metering.sql` + `20260526_keiracom_tenant_budgets.sql` I shipped earlier this session)
- Tenant-prefix guard at read + write paths (Python module, mirrors `ValkeyClient._enforce_tenant_prefix` from PR #1173)
- CI guard `scripts/ci/check_no_raw_atom_store_outside_module.sh` (mirrors A7 CB-10 cache-discipline pattern)
- Atomizer service skeleton (Gemini Flash; structured output; rejects free-text triggers) — behind `KEIRACOM_ATOMIZER_ENABLED=on` feature flag
- Verifier hook (Gemini Pro spot-check on factual claims) — same feature flag
- Composition metering instrumentation (token count + cost + latency + cache-hit + compositions-per-task to Better Stack from day 1; reuse `make_better_stack_emitter` from `src/keiracom_system/cache/metrics.py` PR #1173)

### Out of scope (Week 1 — separate bd issues)
- MAL Retriever (Week 2)
- Composer endpoint rendering (Week 2)
- Endpoint Translator (Week 2-3)
- Full skills-directory atomization (Week 2)
- Dave-facing endpoint switchover (Week 3)
- Cold archive Postgres role on Vultr — separate infra dispatch (architect-0 + Elliot)

### Hard blockers (this PR cannot complete without)
- **B1:** Elliot 48-hour design report — controlled vocabulary specifics (288 composition tag combinations + 7 relationship types per dispatch reference) — the schema reserves columns but DEFAULTs + CHECK constraints need the vocabulary
- **B2:** Gemini API key in Vault — atomizer service can scaffold without it but cannot run end-to-end smoke test

## §2 Postgres schema (Atom Store)

Sibling to `keiracom_tenant_metering` (PR #1137) + `keiracom_tenant_budgets` (PR #1173). Lives in public schema with tenant_id FK to `keiracom_tenants` + ON DELETE CASCADE.

### Primary table: `keiracom_atoms`

```sql
CREATE TABLE public.keiracom_atoms (
    atom_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL
        REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE,

    -- atom_schema_v1 7-field core
    trigger_condition  JSONB        NOT NULL,
        -- structured predicate (NOT free-text); shape: {kind, params} per controlled vocabulary
        -- kinds frozen at pilot scope (B1 dependency for exact list)
    content            TEXT         NOT NULL,
    anti_pattern       TEXT,
        -- nullable: not every atom has an anti-pattern
    example            TEXT,
        -- nullable: example block when relevant
    provenance         JSONB        NOT NULL,
        -- shape: {source, freshness (timestamptz), confidence (0..1), last_validated (timestamptz)}
    composition_tags   JSONB        NOT NULL DEFAULT '{}'::jsonb,
        -- shape: {domain, concern, applicable_context}; vocabulary frozen (B1)

    -- embedding for retrieval
    content_embedding  VECTOR(384)  NOT NULL,
        -- BGE-small-en-v1.5 via TEIClient (PR #1133); 384-dim already canonical

    -- atom-level metadata
    schema_version     SMALLINT     NOT NULL DEFAULT 1,
    state              TEXT         NOT NULL DEFAULT 'active'
        CHECK (state IN ('active', 'superseded', 'cold_archive')),

    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Tenant isolation: every query filters by tenant_id.
CREATE INDEX idx_keiracom_atoms_tenant_state
    ON public.keiracom_atoms (tenant_id, state)
    WHERE state = 'active';

-- pgvector HNSW for retrieval (cosine similarity per BGE-small-en convention).
CREATE INDEX idx_keiracom_atoms_embedding_hnsw
    ON public.keiracom_atoms USING hnsw (content_embedding vector_cosine_ops);

-- Composition tag retrieval — GIN on JSONB for tag predicate queries.
CREATE INDEX idx_keiracom_atoms_composition_tags
    ON public.keiracom_atoms USING gin (composition_tags);
```

### Supersession edges: `keiracom_atom_supersession_edges`

Content-level supersession only (per hard constraint: schema migration triggers re-atomization, NOT edge rewrite).

```sql
CREATE TABLE public.keiracom_atom_supersession_edges (
    edge_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL
        REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE,
    predecessor_atom   UUID         NOT NULL
        REFERENCES public.keiracom_atoms(atom_id) ON DELETE CASCADE,
    successor_atom     UUID         NOT NULL
        REFERENCES public.keiracom_atoms(atom_id) ON DELETE CASCADE,
    relationship_type  TEXT         NOT NULL,
        -- vocabulary capped single-digit count V1 — exact list pending B1
        -- (e.g. supersedes, refines, contradicts, scopes, extends, deprecates, ...)
    confidence         REAL         NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CHECK (predecessor_atom <> successor_atom),
    -- one tenant cannot reference another tenant's atoms — enforced by app-layer
    -- + tenant_prefix_guard.py (read+write paths)
    UNIQUE (predecessor_atom, successor_atom, relationship_type)
);

CREATE INDEX idx_keiracom_atom_edges_predecessor
    ON public.keiracom_atom_supersession_edges (predecessor_atom);
CREATE INDEX idx_keiracom_atom_edges_successor
    ON public.keiracom_atom_supersession_edges (successor_atom);
```

### Composition tag vocabulary lock: `keiracom_atom_composition_tag_vocabulary`

The 288 combinations + 7 relationship types from the dispatch reference are CODE-LEVEL frozen rather than DB-level — a Python `frozenset` in `src/keiracom_system/atomization/vocabulary.py`. The DB stores tags as JSONB but app-layer validates against the vocabulary at write time.

Reason: 288 combinations as a CHECK constraint is opaque; a Python frozen vocabulary is grep-able and review-friendly. Migration adds a comment block citing the canonical key + vocabulary module.

### Atomizer job log: `keiracom_atomizer_jobs`

Tracks each atomization pass for metering + audit.

```sql
CREATE TABLE public.keiracom_atomizer_jobs (
    job_id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID         NOT NULL
        REFERENCES public.keiracom_tenants(tenant_id) ON DELETE CASCADE,
    source_ref         TEXT         NOT NULL,
        -- e.g. "skills/v1/keiramail.md@<commit-sha>"
    source_kind        TEXT         NOT NULL
        CHECK (source_kind IN ('skill', 'manual', 'governance_doc', 'discovery_log', 'session')),

    -- atomizer pass
    atomizer_model     TEXT         NOT NULL,    -- e.g. "google/gemini-2.5-flash"
    atomizer_temp      REAL         NOT NULL DEFAULT 0,
    atomizer_tokens_in BIGINT       NOT NULL DEFAULT 0,
    atomizer_tokens_out BIGINT      NOT NULL DEFAULT 0,
    atomizer_latency_ms INTEGER     NOT NULL DEFAULT 0,
    atoms_produced     INTEGER      NOT NULL DEFAULT 0,

    -- verifier pass
    verifier_model     TEXT,
    verifier_tokens_in BIGINT,
    verifier_tokens_out BIGINT,
    verifier_latency_ms INTEGER,
    verifier_flags     JSONB        NOT NULL DEFAULT '[]'::jsonb,
        -- shape: list of {atom_id, severity, message}

    status             TEXT         NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'atomizer_done', 'verifier_done', 'ratified', 'failed')),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
```

## §3 Tenant-prefix guard pattern

Mirrors `ValkeyClient._enforce_tenant_prefix` from PR #1173 (cache-discipline). Lives in `src/keiracom_system/atomization/atom_store.py`:

```python
class AtomStore:
    def __init__(self, *, db: _DBProtocol, tenant_id: str, embedder: TEIClient, ...):
        if not tenant_id:
            raise AtomStoreError("tenant_id required (cross-tenant isolation invariant)")
        self._db = db
        self._tenant_id = tenant_id
        self._embedder = embedder

    def _enforce_tenant_read(self, query_tenant_id: str) -> None:
        if query_tenant_id != self._tenant_id:
            raise AtomStoreError(
                f"read attempted for tenant {query_tenant_id!r} "
                f"from store bound to {self._tenant_id!r}"
            )

    def insert_atom(self, atom: AtomV1) -> UUID:
        # All inserts get self._tenant_id; no caller override possible
        ...

    def retrieve_by_embedding(self, query_text: str, top_k: int) -> list[AtomV1]:
        # WHERE tenant_id = self._tenant_id ALWAYS appended
        ...
```

Defence-in-depth: app-layer `AtomStore` enforces; CI guard
`scripts/ci/check_no_raw_atom_store_outside_module.sh` rejects direct SQL on
`keiracom_atoms` outside `src/keiracom_system/atomization/`.

## §4 Atomizer service shape (Week 1 skeleton)

`src/keiracom_system/atomization/atomizer.py`:
- Input: `(tenant_id, source_ref, source_text, source_kind)`
- LiteLLM call to `google/gemini-2.5-flash` at temperature=0, structured output schema-constrained
- Rejects free-text trigger_condition: response validation requires `trigger_condition: {kind: <vocab>, params: dict}`
- Writes job row to `keiracom_atomizer_jobs` BEFORE LLM call (idempotency)
- Each produced atom inserted via `AtomStore.insert_atom`
- Verifier (Gemini Pro) runs AFTER atomizer in a separate pass; flags non-blocking → human review queue per Failure-Mode-Mitigations dispatch directive

Feature flag: `KEIRACOM_ATOMIZER_ENABLED=on` env var. Default OFF so this PR can land without runtime impact until ops explicitly enables.

## §5 Composition metering (live from day 1 per dispatch)

Hook in `atomizer.py` after LLM call:
- `keiracom.atomization.atomizer.tokens{tenant_id, model, type=in|out}`
- `keiracom.atomization.atomizer.latency_ms{tenant_id, model}`
- `keiracom.atomization.atoms_produced{tenant_id, source_kind}`
- `keiracom.atomization.verifier.flags{tenant_id, severity}`

Composition-per-task curve (Week 2 retrieval surface) — pre-wire metric name now, no-op until Composer ships:
- `keiracom.atomization.compositions_per_task{tenant_id, endpoint}`

Reuses `make_better_stack_emitter` factory from `src/keiracom_system/cache/metrics.py` (my PR #1173) — no new dependency.

## §6 CI guard: `check_no_raw_atom_store_outside_module.sh`

Mirrors A7 cache-discipline guard (PR #1173 CB-10). Pattern:

```bash
PATTERN='\b(INSERT INTO keiracom_atoms|UPDATE keiracom_atoms|DELETE FROM keiracom_atoms|SELECT.*FROM keiracom_atoms)'
SCOPE='src/keiracom_system'
EXEMPT='src/keiracom_system/atomization/'
```

Wired into `.github/workflows/ci.yml` as a new step in the existing `cache-discipline-guards` job (renamed to `module-discipline-guards`) OR as a new sibling job.

## §7 Migration file shape

Single migration at `supabase/migrations/20260526_keiracom_atomization_pilot.sql`:
- Creates 3 tables (atoms, supersession_edges, atomizer_jobs)
- Creates indexes (HNSW + GIN + composite)
- Adds CHECK constraints (state enum, source_kind enum, status enum)
- `SET LOCAL agency_os.callsign = 'dave'` per KEI-87 bypass (same as PR #1137/1173 metering+budgets pattern)
- pgvector extension assumed already enabled (Hindsight substrate prerequisite)

Verification path: pgvector extension check at migration head — fail loudly if not enabled rather than silent VECTOR-type creation failure.

## §8 Open questions for Elliot's design report (B1)

These are explicitly deferred to the 48-hour deliverable but I need them BEFORE the migration goes from PROPOSAL to PR-merge-ready:

1. **Trigger condition controlled vocabulary** — exact `kind` enum (e.g. `tenant_attribute`, `time_window`, `request_shape`, ...). Affects atomizer's structured output schema.
2. **Composition tag 288 combinations** — exact `domain × concern × applicable_context` enumeration. Could store as either:
   - (a) Single JSONB column + vocabulary check at app layer (my current proposal)
   - (b) 3 columns (`domain TEXT CHECK (... IN (...))`, `concern TEXT CHECK (...)`, `applicable_context TEXT CHECK (...)`) — query plan friendlier
3. **Relationship types** — the single-digit count (5 / 6 / 7 / 8?) and exact names.
4. **Schema versioning semantics** — confirm "schema migration triggers re-atomization not edge rewrite" mechanism: do we keep old atoms with schema_version=N and atomize-fresh into N+1, or do we rewrite content_embedding in-place?
5. **Provenance freshness lag SLA** — at what staleness does an atom flip to `cold_archive`? Per-domain or global?

## §9 Acceptance criteria for the Week 1 schema-lock PR (post-Elliot-report)

1. Migration runs cleanly against a fresh Postgres + pgvector container
2. `AtomStore` Python module with tenant-prefix guard at read+write paths (5 unit tests minimum: prefix guard + insert+retrieve roundtrip + cross-tenant rejection + supersession edge insertion + cold-archive state transition)
3. CI guard `check_no_raw_atom_store_outside_module.sh` self-passes on diff + negative-path test fires (per `feedback_negative_path_test_before_approve`)
4. Atomizer service skeleton compiles + can be imported but feature-flagged OFF
5. One synthetic-skill atomization E2E (run only when Gemini key in Vault):
   - Atomizer Flash → produces atoms
   - Verifier Pro → spot-checks
   - Atoms land in `keiracom_atoms` with tenant_id=Dave
   - Job row in `keiracom_atomizer_jobs` with metering data
6. Better Stack emits at least 1 of each metric name (verifiable via the metric-emitter test pattern from PR #1173)

## §10 Risks + non-blocking observations

1. **Pgvector extension provisioning** — Hindsight runs the substrate per inventory `mem.engine`. Need to confirm pgvector is installed on the Postgres Hindsight is using. If it's a separate Postgres, the atomization migration needs to know which.
2. **288 vocabulary as code** — `frozenset` is grep-able but a CHECK constraint catches DB-direct violations. Recommend BOTH: app-layer frozenset + comment block in migration pointing to the vocabulary module.
3. **Composer endpoints** — out of scope this week. The hard constraint "Composer output never reaches agent reasoning input" needs an ENFORCEMENT mechanism (separate CI guard analogous to BMV1) — file as Week 2 bd.
4. **Cold archive Postgres role** — separate infra dispatch (architect-0 territory: provision Postgres on Vultr). Week 1 schema uses `state='cold_archive'` flag but doesn't physically move atoms.

## §11 References

- `ceo:atomization_architecture_v1` (canonical, version 1, RATIFIED-CEO 2026-05-26T11:25:00Z)
- `ceo:directive_10029_complete` (completion marker)
- Elliot dispatch 2026-05-26 ~11:39 UTC (Agency_OS-atomization-pilot-week1)
- PR #1133 — TEI sidecar (BGE-small embeddings — substrate)
- PR #1137 — keiracom_tenant_metering (sibling migration pattern)
- PR #1173 — Phase A7 cache build (ValkeyClient tenant-prefix-guard pattern + Better Stack emitter factory + CB-10 CI guard pattern)
- PR #1174 — Sessions hand-migration (orchestrator parity test discipline — analog for write+read parity)
- Failure modes 1-12 enumerated in `ceo:atomization_architecture_v1.failure_modes_acknowledged`

---

**Next steps in this session (after Elliot replies):**
1. Update §8 open questions with answers
2. Open Week 1 schema-lock PR with migration + AtomStore module + CI guard + 5 unit tests
3. File bd issues for Week 1 acceptance criteria items 4-6 (atomizer service + E2E smoke + metering)

**Next session pickup (fresh Orion):**
- Continue Week 1 implementation per PR
- Week 2 MAL Retriever + Composer dispatch
