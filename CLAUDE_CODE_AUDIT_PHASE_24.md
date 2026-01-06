# Claude Code Audit Prompt: Phase 24 CIS Data Gaps Implementation

**Purpose:** Verify what was designed vs what was actually built  
**Run this after Claude Code completes Phase 24 implementation**

---

## Instructions

You are auditing the Phase 24 (CIS Data Gaps) implementation. Compare what was specified in the design documents against what actually exists in the codebase.

### Reference Documents (READ FIRST)

1. `docs/specs/CIS_DATA_GAPS_IMPLEMENTATION.md` — Full specification
2. `docs/specs/LEAD_POOL_ARCHITECTURE.md` — Lead Pool design
3. `docs/phases/PHASE_24_LEAD_POOL.md` — Task breakdown

---

## Audit Checklist

### Phase 24A: Lead Pool Architecture

#### Database Schema

Check migration exists: `supabase/migrations/024_lead_pool.sql`

| Table/Column | Specified | Exists? | Notes |
|--------------|-----------|---------|-------|
| `lead_pool` table | ✅ | ☐ | |
| `lead_pool.apollo_id` (UNIQUE) | ✅ | ☐ | |
| `lead_pool.email` (UNIQUE) | ✅ | ☐ | |
| `lead_pool.linkedin_url` (UNIQUE) | ✅ | ☐ | |
| `lead_pool.seniority` | ✅ | ☐ | |
| `lead_pool.email_status` | ✅ | ☐ | verified/guessed/unavailable |
| `lead_pool.timezone` | ✅ | ☐ | |
| `lead_pool.company_revenue` | ✅ | ☐ | |
| `lead_pool.company_technologies` | ✅ | ☐ | JSONB array |
| `lead_pool.employment_history` | ✅ | ☐ | JSONB array |
| `lead_pool.pool_status` | ✅ | ☐ | available/assigned/converted/bounced |
| `lead_pool.is_bounced` | ✅ | ☐ | Global flag |
| `lead_pool.is_unsubscribed` | ✅ | ☐ | Global flag |
| `lead_assignments` table | ✅ | ☐ | |
| `lead_assignments.lead_pool_id` (UNIQUE) | ✅ | ☐ | One lead = one client |
| `lead_assignments.client_id` | ✅ | ☐ | |
| `lead_assignments.status` | ✅ | ☐ | active/released/converted |
| `lead_assignments.channels_used` | ✅ | ☐ | Array |
| `lead_assignments.has_replied` | ✅ | ☐ | |
| `leads.lead_pool_id` FK added | ✅ | ☐ | |
| `leads.assignment_id` FK added | ✅ | ☐ | |
| RLS policies on new tables | ✅ | ☐ | |
| Indexes on queryable columns | ✅ | ☐ | |

#### Services

| File | Specified | Exists? | Key Functions |
|------|-----------|---------|---------------|
| `src/services/lead_pool_service.py` | ✅ | ☐ | create, get, update, search |
| `src/services/lead_allocator_service.py` | ✅ | ☐ | allocate, release, check_exclusivity |
| `src/services/jit_validator.py` | ✅ | ☐ | validate_before_send |

#### JIT Validator Checks

| Check | Specified | Implemented? |
|-------|-----------|--------------|
| Pool-level: is_bounced | ✅ | ☐ |
| Pool-level: is_unsubscribed | ✅ | ☐ |
| Pool-level: email_status = guessed | ✅ | ☐ |
| Assignment: not_assigned | ✅ | ☐ |
| Assignment: has_replied | ✅ | ☐ |
| Assignment: already_converted | ✅ | ☐ |
| Timing: too_recent (3 days) | ✅ | ☐ |
| Channel: cooling period (7 days) | ✅ | ☐ |
| Rate limits | ✅ | ☐ |
| Warmup check (email) | ✅ | ☐ |

#### Integrations Updated

| File | Change | Done? |
|------|--------|-------|
| `src/integrations/apollo.py` | Capture all 50+ fields | ☐ |
| `src/engines/scout.py` | Write to pool first | ☐ |
| `src/engines/scorer.py` | Read from pool | ☐ |
| `src/engines/email.py` | JIT validation before send | ☐ |
| `src/engines/sms.py` | JIT validation before send | ☐ |
| `src/engines/linkedin.py` | JIT validation before send | ☐ |
| `src/engines/voice.py` | JIT validation before send | ☐ |
| `src/engines/mail.py` | JIT validation before send | ☐ |

---

### Phase 24B: Content & Template Tracking

#### Database Schema

Check migration exists: `supabase/migrations/025_content_tracking.sql`

| Table/Column | Specified | Exists? | Notes |
|--------------|-----------|---------|-------|
| `activities.template_id` | ✅ | ☐ | FK to templates |
| `activities.ab_variant` | ✅ | ☐ | 'A', 'B', 'control' |
| `activities.ab_test_id` | ✅ | ☐ | |
| `activities.full_message_body` | ✅ | ☐ | Full content |
| `activities.links_included` | ✅ | ☐ | TEXT[] |
| `activities.personalization_fields_used` | ✅ | ☐ | TEXT[] |
| `ab_tests` table | ✅ | ☐ | |
| `ab_tests.variant_a_description` | ✅ | ☐ | |
| `ab_tests.variant_b_description` | ✅ | ☐ | |
| `ab_tests.winner` | ✅ | ☐ | |
| `ab_tests.confidence` | ✅ | ☐ | |

#### Services

| File | Specified | Exists? | Key Functions |
|------|-----------|---------|---------------|
| `src/services/ab_test_service.py` | ✅ | ☐ | create_test, assign_variant, record_outcome, determine_winner |

#### Engines Updated

| File | Change | Done? |
|------|--------|-------|
| `src/engines/email.py` | Store full body + template link | ☐ |
| `src/engines/sms.py` | Store full body + template link | ☐ |
| `src/engines/linkedin.py` | Store full body | ☐ |

#### CIS Detector Updated

| File | Change | Done? |
|------|--------|-------|
| `src/detectors/what_detector.py` | Use template_id, ab_variant, full_body | ☐ |

---

### Phase 24C: Email Engagement Tracking

#### Database Schema

Check migration exists: `supabase/migrations/026_email_engagement.sql`

| Table/Column | Specified | Exists? | Notes |
|--------------|-----------|---------|-------|
| `email_events` table | ✅ | ☐ | |
| `email_events.event_type` | ✅ | ☐ | sent/delivered/opened/clicked/bounced/complained |
| `email_events.first_opened_at` | ✅ | ☐ | |
| `email_events.clicked_url` | ✅ | ☐ | |
| `email_events.device_type` | ✅ | ☐ | |
| `email_events.email_client` | ✅ | ☐ | |
| `activities.email_opened` | ✅ | ☐ | |
| `activities.email_opened_at` | ✅ | ☐ | |
| `activities.email_open_count` | ✅ | ☐ | |
| `activities.email_clicked` | ✅ | ☐ | |
| `activities.email_clicked_at` | ✅ | ☐ | |
| `activities.time_to_open_minutes` | ✅ | ☐ | |
| `activities.time_to_click_minutes` | ✅ | ☐ | |
| `activities.touch_number` | ✅ | ☐ | |
| `activities.days_since_last_touch` | ✅ | ☐ | |
| `activities.lead_local_time` | ✅ | ☐ | |
| `activities.lead_timezone` | ✅ | ☐ | |
| Trigger: update_activity_email_stats | ✅ | ☐ | |

#### Services

| File | Specified | Exists? | Key Functions |
|------|-----------|---------|---------------|
| `src/services/email_events_service.py` | ✅ | ☐ | ingest_webhook, process_event |

#### Integrations

| File | Change | Done? |
|------|--------|-------|
| Salesforge webhook handler | Ingest open/click/bounce events | ☐ |
| `src/api/routes/webhooks.py` | Salesforge webhook endpoint | ☐ |

#### CIS Detectors Updated

| File | Change | Done? |
|------|--------|-------|
| `src/detectors/when_detector.py` | Use open/click timing | ☐ |
| `src/detectors/how_detector.py` | Use engagement correlation | ☐ |

---

### Phase 24D: Conversation Threading

#### Database Schema

Check migration exists: `supabase/migrations/027_conversation_threads.sql`

| Table/Column | Specified | Exists? | Notes |
|--------------|-----------|---------|-------|
| `conversation_threads` table | ✅ | ☐ | |
| `conversation_threads.message_count` | ✅ | ☐ | |
| `conversation_threads.our_message_count` | ✅ | ☐ | |
| `conversation_threads.their_message_count` | ✅ | ☐ | |
| `conversation_threads.outcome` | ✅ | ☐ | |
| `thread_messages` table | ✅ | ☐ | |
| `thread_messages.direction` | ✅ | ☐ | outbound/inbound |
| `thread_messages.sentiment` | ✅ | ☐ | |
| `thread_messages.sentiment_score` | ✅ | ☐ | |
| `thread_messages.objection_type` | ✅ | ☐ | |
| `thread_messages.question_extracted` | ✅ | ☐ | |
| `thread_messages.response_time_minutes` | ✅ | ☐ | |
| `activities.thread_id` FK | ✅ | ☐ | |
| `replies.thread_id` FK | ✅ | ☐ | |
| `replies.objection_type` | ✅ | ☐ | |
| `replies.sentiment` | ✅ | ☐ | |
| `leads.rejection_reason` | ✅ | ☐ | ENUM type |
| `leads.rejection_notes` | ✅ | ☐ | |
| Trigger: update_thread_stats | ✅ | ☐ | |

#### Services

| File | Specified | Exists? | Key Functions |
|------|-----------|---------|---------------|
| `src/services/thread_service.py` | ✅ | ☐ | create_thread, add_message, close_thread |
| `src/services/reply_analyzer.py` | ✅ | ☐ | analyze_sentiment, extract_objection, extract_question |

#### CIS Detector

| File | Specified | Exists? | Notes |
|------|-----------|---------|-------|
| `src/algorithms/conversation_detector.py` | ✅ | ☐ | New detector for conversation patterns |

#### Integrations Updated

| File | Change | Done? |
|------|--------|-------|
| `src/engines/closer.py` | Create/manage threads | ☐ |

---

### Phase 24E: Downstream Outcomes

#### Database Schema

Check migration exists: `supabase/migrations/028_downstream_outcomes.sql`

| Table/Column | Specified | Exists? | Notes |
|--------------|-----------|---------|-------|
| `meetings.showed_up` | ✅ | ☐ | |
| `meetings.meeting_outcome` | ✅ | ☐ | good/bad/rescheduled/no_show |
| `meetings.deal_created` | ✅ | ☐ | |
| `deals` table | ✅ | ☐ | |
| `deals.value` | ✅ | ☐ | |
| `deals.stage` | ✅ | ☐ | |
| `deals.won` | ✅ | ☐ | |
| `deals.lost_reason` | ✅ | ☐ | |
| `deals.days_to_close` | ✅ | ☐ | |
| `deal_stage_history` table | ✅ | ☐ | |
| Trigger: track_deal_stage_change | ✅ | ☐ | |

#### Services

| File | Specified | Exists? | Key Functions |
|------|-----------|---------|---------------|
| `src/services/deal_service.py` | ✅ | ☐ | create_deal, update_stage, close_deal |

#### CIS Detector

| File | Specified | Exists? | Notes |
|------|-----------|---------|-------|
| `src/algorithms/funnel_detector.py` | ✅ | ☐ | New detector for funnel patterns |

#### Webhook

| Endpoint | Specified | Exists? | Notes |
|----------|-----------|---------|-------|
| Generic CRM webhook | ✅ | ☐ | For external CRM integration |

---

## Summary Template

After completing the audit, fill in this summary:

### Overall Status

| Phase | Tasks Specified | Tasks Complete | % |
|-------|-----------------|----------------|---|
| 24A (Lead Pool) | 15 | ☐ | |
| 24B (Content Tracking) | 7 | ☐ | |
| 24C (Email Engagement) | 7 | ☐ | |
| 24D (Conversation Threading) | 8 | ☐ | |
| 24E (Downstream Outcomes) | 7 | ☐ | |
| **TOTAL** | **44** | ☐ | |

### Migrations Created

| Migration | Exists? | Applied? |
|-----------|---------|----------|
| 024_lead_pool.sql | ☐ | ☐ |
| 025_content_tracking.sql | ☐ | ☐ |
| 026_email_engagement.sql | ☐ | ☐ |
| 027_conversation_threads.sql | ☐ | ☐ |
| 028_downstream_outcomes.sql | ☐ | ☐ |

### Services Created

| Service | Exists? | Has Tests? |
|---------|---------|------------|
| lead_pool_service.py | ☐ | ☐ |
| lead_allocator_service.py | ☐ | ☐ |
| jit_validator.py | ☐ | ☐ |
| ab_test_service.py | ☐ | ☐ |
| email_events_service.py | ☐ | ☐ |
| thread_service.py | ☐ | ☐ |
| reply_analyzer.py | ☐ | ☐ |
| deal_service.py | ☐ | ☐ |

### CIS Detectors Updated/Created

| Detector | Updated/Created? | Uses New Data? |
|----------|------------------|----------------|
| who_detector.py | ☐ | ☐ |
| what_detector.py | ☐ | ☐ |
| when_detector.py | ☐ | ☐ |
| how_detector.py | ☐ | ☐ |
| conversation_detector.py (NEW) | ☐ | ☐ |
| funnel_detector.py (NEW) | ☐ | ☐ |

### Gaps Found

List anything that was specified but not implemented:

1. 
2. 
3. 

### Extra Items Built

List anything that was built but not in the original spec:

1. 
2. 
3. 

### Recommendations

Based on the audit, what should be done next?

1. 
2. 
3. 

---

## Verification Commands

Run these to verify implementation:

```bash
# Check migrations exist
ls -la supabase/migrations/024*.sql
ls -la supabase/migrations/025*.sql
ls -la supabase/migrations/026*.sql
ls -la supabase/migrations/027*.sql
ls -la supabase/migrations/028*.sql

# Check services exist
ls -la src/services/lead_pool*.py
ls -la src/services/jit_validator.py
ls -la src/services/ab_test*.py
ls -la src/services/email_events*.py
ls -la src/services/thread*.py
ls -la src/services/reply_analyzer.py
ls -la src/services/deal*.py

# Check new detectors exist
ls -la src/algorithms/conversation_detector.py
ls -la src/algorithms/funnel_detector.py

# Check tests exist
ls -la tests/test_lead_pool*.py
ls -la tests/test_jit_validator*.py
ls -la tests/test_ab_test*.py

# Run tests
pytest tests/ -v --tb=short

# Check if migrations can be applied (dry run)
supabase db push --dry-run
```

---

## End of Audit

Once complete, update:
- `PROGRESS.md` — Mark completed tasks
- `docs/phases/PHASE_INDEX.md` — Update phase status
- Create issues for any gaps found
