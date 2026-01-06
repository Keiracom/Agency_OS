# Claude Code Implementation Prompt: CIS Data Gaps

## Context

You are implementing data capture improvements for Agency OS to enable the Conversion Intelligence System (CIS) to learn effectively. Currently, CIS is learning from incomplete data (~40% of useful data is missing).

## Reference Documents

READ THESE FIRST:
1. `docs/specs/CIS_DATA_GAPS_IMPLEMENTATION.md` — Full gap analysis and implementation plan
2. `docs/specs/LEAD_POOL_ARCHITECTURE.md` — Lead Pool architecture (Phase 24A)
3. `docs/specs/phase16/PHASE_16_CONVERSION_INTELLIGENCE_SPEC.md` — How CIS works
4. `docs/specs/database/SCHEMA_OVERVIEW.md` — Current database schema

## Implementation Order

### Step 1: Phase 24A — Lead Pool (POOL-001 to POOL-015)

Create the lead pool architecture as specified in `LEAD_POOL_ARCHITECTURE.md`.

Key deliverables:
- Migration `024_lead_pool.sql` with `lead_pool` and `lead_assignments` tables
- `src/services/lead_pool_service.py` — CRUD for pool leads
- `src/services/lead_allocator_service.py` — Exclusive assignment logic
- `src/services/jit_validator.py` — Pre-send validation
- Update `src/integrations/apollo.py` to capture ALL 50+ fields
- Update `src/engines/scout.py` to write to pool first
- Update existing engines to use pool data

### Step 2: Phase 24B — Content & Template Tracking (CONTENT-001 to CONTENT-007)

Create content tracking for WHAT detector.

Key deliverables:
- Migration `025_content_tracking.sql`
- Add `template_id`, `ab_variant`, `full_message_body` to activities
- Create `ab_tests` table
- `src/services/ab_test_service.py`
- Update Email/SMS/LinkedIn engines to store full content
- Update WHAT detector to use new fields

### Step 3: Phase 24C — Email Engagement Tracking (ENGAGE-001 to ENGAGE-007)

Create email engagement tracking for WHEN/HOW detectors.

Key deliverables:
- Migration `026_email_engagement.sql`
- Create `email_events` table (opens, clicks, bounces)
- Add `email_opened`, `email_clicked`, `time_to_open_minutes`, `touch_number` to activities
- `src/services/email_events_service.py` — Webhook ingestion from Salesforge/Smartlead
- Create trigger to update activity stats on email events
- Update WHEN detector to use open/click timing
- Update HOW detector to use engagement correlation

### Step 4: Phase 24D — Conversation Threading (THREAD-001 to THREAD-008)

Create conversation tracking for reply analysis.

Key deliverables:
- Migration `027_conversation_threads.sql`
- Create `conversation_threads` and `thread_messages` tables
- Add `thread_id`, `objection_type`, `sentiment` to replies
- Add `rejection_reason` to leads
- `src/services/thread_service.py`
- `src/services/reply_analyzer.py` — Extract sentiment, objections, questions
- Update Closer Engine to manage threads
- Create new `src/algorithms/conversation_detector.py` for CIS

### Step 5: Phase 24E — Downstream Outcomes (OUTCOME-001 to OUTCOME-007)

Create deal/outcome tracking for full funnel learning.

Key deliverables:
- Migration `028_downstream_outcomes.sql`
- Add `showed_up`, `meeting_outcome` to meetings
- Create `deals` and `deal_stage_history` tables
- `src/services/deal_service.py`
- Create new `src/algorithms/funnel_detector.py` for CIS
- Add deal analytics

## Critical Rules

1. **Follow existing patterns** — Look at existing migrations, services, and engines for style
2. **Maintain backwards compatibility** — Don't break existing functionality
3. **Add indexes** — All new queryable fields need indexes
4. **Add RLS policies** — All new tables need row-level security
5. **Update tests** — Add tests for all new services
6. **Update CIS detectors** — Each phase should update relevant detectors to use new data

## Database Conventions

- UUIDs for all primary keys: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
- Timestamps: `created_at TIMESTAMPTZ DEFAULT NOW()`
- Soft deletes where appropriate: `deleted_at TIMESTAMPTZ`
- Foreign keys with ON DELETE CASCADE where appropriate
- Check constraints for enums
- Composite indexes for common query patterns

## File Locations

- Migrations: `supabase/migrations/`
- Services: `src/services/`
- Engines: `src/engines/`
- Algorithms (CIS): `src/algorithms/`
- Integrations: `src/integrations/`
- Tests: `tests/`

## Verification

After each phase:
1. Run migrations: `supabase db push`
2. Run tests: `pytest tests/`
3. Verify no regressions in existing functionality
4. Update `PROGRESS.md` with completed tasks

## Questions to Ask Dave

Before implementation:
1. Which email provider webhooks to integrate? (Salesforge, Smartlead, or both?)
2. Should reply analysis use AI (Claude) or rule-based extraction?
3. Should deal tracking integrate with external CRM or be standalone?
4. Priority order if time-constrained?

## Start Here

Begin with Phase 24A (Lead Pool) as it's the foundation. The spec is complete in `LEAD_POOL_ARCHITECTURE.md`.

```bash
# First, read the specs
cat docs/specs/LEAD_POOL_ARCHITECTURE.md
cat docs/specs/CIS_DATA_GAPS_IMPLEMENTATION.md

# Then start with the migration
# Create supabase/migrations/024_lead_pool.sql
```

Good luck!
