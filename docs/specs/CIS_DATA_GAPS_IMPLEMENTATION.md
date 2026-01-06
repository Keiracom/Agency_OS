# CIS Data Gaps Analysis & Implementation Plan

**Date:** January 6, 2026  
**Purpose:** Document all data gaps preventing Conversion Intelligence System from learning effectively  
**Status:** Ready for Implementation

---

## Executive Summary

The Conversion Intelligence System (CIS) is built and functional, but it's learning from **incomplete data**. This document identifies all missing data points and provides implementation tasks to fill the gaps.

**Key Finding:** CIS can learn, but with ~40% of useful data missing, its learning quality is limited.

---

## Gap Analysis by CIS Detector

### 1. WHO Detector Gaps (Lead Attributes)

**Purpose:** Learn which lead attributes predict conversions

| Data Point | Current Status | Impact | Priority |
|------------|---------------|--------|----------|
| `seniority` | ❌ Not stored | Can't learn if C-suite vs Manager converts better | High |
| `company_revenue` | ❌ Not stored | Can't learn if bigger companies convert better | High |
| `company_technologies` | ❌ Not stored | Can't target "uses HubSpot" patterns | Medium |
| `person_city` | ❌ Not stored | Can't learn geographic patterns | Medium |
| `person_state` | ❌ Not stored | Can't learn geographic patterns | Medium |
| `person_country` | ❌ Not stored | Can't learn geographic patterns | Medium |
| `timezone` | ❌ Not stored | Can't optimize send times per lead | High |
| `email_status` | ❌ Not stored | Can't learn if verified vs guessed converts | High |
| `linkedin_headline` | ❌ Not stored | Missing rich personalization signal | Medium |
| `employment_history` | ❌ Not stored | Can't learn "came from competitor" patterns | Low |
| `apollo_id` | ❌ Not stored | Can't deduplicate properly | High |
| `company_description` | ❌ Not stored | Missing context for personalization | Medium |
| `company_total_funding` | ❌ Not stored | Can't learn funded vs bootstrapped patterns | Low |

**Resolution:** Phase 24 (Lead Pool) captures all these fields.

---

### 2. WHAT Detector Gaps (Content Analysis)

**Purpose:** Learn which content/messaging converts

| Data Point | Current Status | Impact | Priority |
|------------|---------------|--------|----------|
| `full_message_body` | ❌ Only preview | Can't analyze full content patterns | High |
| `template_id` | ❌ Not linked | Can't learn which templates work | High |
| `ab_variant` | ❌ No A/B tracking | Can't run proper experiments | Medium |
| `links_included` | ❌ Not tracked | Can't learn if links help/hurt | Medium |
| `attachments` | ❌ Not tracked | Can't learn if attachments help | Low |
| `personalization_fields_available` | ❌ Not tracked | Can't learn what data enables what copy | Medium |
| `ai_model_used` | ❌ Not tracked | Can't learn if GPT-4 vs Claude matters | Low |
| `prompt_version` | ❌ Not tracked | Can't iterate on prompts systematically | Medium |

**Resolution:** New schema additions needed.

---

### 3. WHEN Detector Gaps (Timing Analysis)

**Purpose:** Learn optimal timing for outreach

| Data Point | Current Status | Impact | Priority |
|------------|---------------|--------|----------|
| `email_opened_at` | ❌ Not tracked | Can't learn when leads read emails | High |
| `email_click_at` | ❌ Not tracked | Can't learn click timing patterns | High |
| `time_to_open` | ❌ Not calculated | Can't optimize for quick opens | High |
| `time_to_click` | ❌ Not calculated | Can't learn click urgency | Medium |
| `time_to_reply` | ⚠️ Must calculate | Should be stored directly | Medium |
| `lead_timezone` | ❌ Not stored | Can't send at their 10am | High |
| `lead_local_time_sent` | ❌ Not calculated | Can't learn "their time" patterns | High |
| `touch_number` | ⚠️ Must calculate | Should be stored directly | Medium |
| `days_since_last_touch` | ⚠️ Must calculate | Should be stored directly | Medium |
| `sequence_position` | ❌ Not explicit | Which step in sequence | Medium |

**Resolution:** Email tracking integration + schema additions.

---

### 4. HOW Detector Gaps (Channel Sequence Analysis)

**Purpose:** Learn which channel combinations convert

| Data Point | Current Status | Impact | Priority |
|------------|---------------|--------|----------|
| `email_opened` | ❌ Not tracked | Can't learn open → reply correlation | High |
| `email_clicked` | ❌ Not tracked | Can't learn click → reply correlation | High |
| `linkedin_profile_viewed` | ❌ Not tracked | Missing engagement signal | Medium |
| `linkedin_post_engaged` | ❌ Not tracked | Can't learn social engagement | Low |
| `sms_link_clicked` | ❌ Not tracked | Can't learn SMS engagement | Medium |
| `call_duration` | ⚠️ Partial | Should store seconds | Medium |
| `voicemail_listened` | ❌ Not tracked | Can't learn VM effectiveness | Low |
| `channel_preference_signal` | ❌ Not derived | Which channel lead engages most | Medium |

**Resolution:** Email/SMS tracking integration + schema additions.

---

### 5. Conversation & Reply Gaps

**Purpose:** Learn from the back-and-forth dialogue

| Data Point | Current Status | Impact | Priority |
|------------|---------------|--------|----------|
| `reply_content` | ✅ Stored | — | — |
| `reply_intent` | ✅ Stored | — | — |
| `objection_type` | ❌ Not categorized | Can't learn common objections | High |
| `question_asked` | ❌ Not extracted | Can't learn FAQ patterns | High |
| `sentiment_score` | ❌ Not analyzed | Can't learn tone correlation | Medium |
| `our_response` | ❌ Not linked | Can't learn what responses work | High |
| `thread_id` | ❌ Not linked | Can't see full conversation | High |
| `conversation_turns` | ❌ Not counted | Can't learn length to conversion | Medium |
| `response_time_ours` | ❌ Not tracked | Can't learn if fast replies help | Medium |
| `escalated_to_human` | ❌ Not tracked | Can't learn AI vs human effectiveness | Medium |

**Resolution:** New conversation tracking system needed.

---

### 6. Outcome & Downstream Gaps

**Purpose:** Learn full funnel, not just "meeting booked"

| Data Point | Current Status | Impact | Priority |
|------------|---------------|--------|----------|
| `lead_converted` | ✅ Stored | — | — |
| `meeting_booked` | ✅ Stored | — | — |
| `rejection_reason` | ❌ Not categorized | Can't learn WHY people say no | High |
| `meeting_showed_up` | ❌ Not tracked | Can't learn show rate patterns | High |
| `meeting_outcome` | ❌ Not tracked | Good meeting vs bad meeting | High |
| `deal_created` | ❌ Not tracked | Can't learn meeting → deal rate | Medium |
| `deal_value` | ❌ Not tracked | Can't optimize for revenue | Medium |
| `deal_closed_won` | ❌ Not tracked | Can't learn full funnel | Medium |
| `time_to_close` | ❌ Not tracked | Can't learn sales cycle | Low |
| `lost_reason` | ❌ Not tracked | Can't learn why deals fail | Medium |

**Resolution:** CRM integration or downstream tracking system.

---

## Implementation Plan

### Phase 24A: Lead Data Gaps (From Lead Pool Architecture)

Already specified in `LEAD_POOL_ARCHITECTURE.md`. Adds:
- All 30+ missing Apollo fields
- `lead_pool` table with complete data
- `lead_assignments` for ownership tracking

**Tasks:** POOL-001 to POOL-015 (43 hours)

---

### Phase 24B: Content & Template Tracking (NEW)

**Migration:** `025_content_tracking.sql`

```sql
-- 1. Add template tracking to activities
ALTER TABLE activities ADD COLUMN template_id UUID REFERENCES email_templates(id);
ALTER TABLE activities ADD COLUMN ab_variant TEXT;  -- 'A', 'B', 'control'
ALTER TABLE activities ADD COLUMN ab_test_id UUID;
ALTER TABLE activities ADD COLUMN full_message_body TEXT;  -- Full content, not just preview
ALTER TABLE activities ADD COLUMN links_included TEXT[];  -- URLs in message
ALTER TABLE activities ADD COLUMN personalization_fields_used TEXT[];  -- Which fields were available

-- 2. Create A/B test tracking
CREATE TABLE ab_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    campaign_id UUID NOT NULL REFERENCES campaigns(id),
    name TEXT NOT NULL,
    hypothesis TEXT,
    variant_a_description TEXT,
    variant_b_description TEXT,
    metric TEXT DEFAULT 'reply_rate',  -- What we're measuring
    sample_size_target INTEGER,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    winner TEXT,  -- 'A', 'B', 'no_difference'
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Expand content_snapshot JSONB structure
COMMENT ON COLUMN activities.content_snapshot IS '
{
  "subject": "string",
  "body_preview": "string (first 200 chars)",
  "body_full": "string (complete message)",
  "pain_points": ["array"],
  "cta_type": "string",
  "personalization_used": ["array"],
  "personalization_available": ["array"],
  "word_count": "integer",
  "has_question": "boolean",
  "links": ["array of URLs"],
  "template_name": "string",
  "ai_model": "string",
  "prompt_version": "string"
}';

CREATE INDEX idx_activities_template ON activities(template_id);
CREATE INDEX idx_activities_ab_test ON activities(ab_test_id);
CREATE INDEX idx_ab_tests_client ON ab_tests(client_id);
```

**Tasks:**

| ID | Task | Est |
|----|------|-----|
| CONTENT-001 | Create migration 025_content_tracking.sql | 1h |
| CONTENT-002 | Update Email Engine to store full body + template link | 2h |
| CONTENT-003 | Update SMS Engine to store full body + template link | 1h |
| CONTENT-004 | Update LinkedIn Engine to store full body | 1h |
| CONTENT-005 | Create A/B test service | 4h |
| CONTENT-006 | Update WHAT Detector to use new fields | 3h |
| CONTENT-007 | Add A/B test UI (optional) | 4h |

**Total:** 16 hours

---

### Phase 24C: Email Engagement Tracking (NEW)

**Migration:** `026_email_engagement.sql`

```sql
-- 1. Create email engagement events table
CREATE TABLE email_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id UUID NOT NULL REFERENCES activities(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    client_id UUID NOT NULL REFERENCES clients(id),
    
    event_type TEXT NOT NULL,  -- 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained'
    event_at TIMESTAMPTZ NOT NULL,
    
    -- Open tracking
    open_count INTEGER DEFAULT 0,
    first_opened_at TIMESTAMPTZ,
    last_opened_at TIMESTAMPTZ,
    
    -- Click tracking
    clicked_url TEXT,
    click_count INTEGER DEFAULT 0,
    first_clicked_at TIMESTAMPTZ,
    
    -- Device info (if available)
    device_type TEXT,  -- 'desktop', 'mobile', 'tablet'
    email_client TEXT,  -- 'gmail', 'outlook', 'apple_mail'
    
    -- Geo (if available from IP)
    open_city TEXT,
    open_country TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_event_type CHECK (event_type IN ('sent', 'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed'))
);

-- 2. Add summary fields to activities for quick access
ALTER TABLE activities ADD COLUMN email_opened BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN email_opened_at TIMESTAMPTZ;
ALTER TABLE activities ADD COLUMN email_open_count INTEGER DEFAULT 0;
ALTER TABLE activities ADD COLUMN email_clicked BOOLEAN DEFAULT FALSE;
ALTER TABLE activities ADD COLUMN email_clicked_at TIMESTAMPTZ;
ALTER TABLE activities ADD COLUMN email_click_count INTEGER DEFAULT 0;
ALTER TABLE activities ADD COLUMN time_to_open_minutes INTEGER;  -- Calculated
ALTER TABLE activities ADD COLUMN time_to_click_minutes INTEGER;  -- Calculated

-- 3. Add touch metadata
ALTER TABLE activities ADD COLUMN touch_number INTEGER;  -- 1st, 2nd, 3rd touch
ALTER TABLE activities ADD COLUMN days_since_last_touch INTEGER;
ALTER TABLE activities ADD COLUMN sequence_step INTEGER;  -- Position in sequence
ALTER TABLE activities ADD COLUMN lead_local_time TIME;  -- What time was it for the lead?
ALTER TABLE activities ADD COLUMN lead_timezone TEXT;

-- Indexes
CREATE INDEX idx_email_events_activity ON email_events(activity_id);
CREATE INDEX idx_email_events_lead ON email_events(lead_id);
CREATE INDEX idx_email_events_type ON email_events(event_type);
CREATE INDEX idx_email_events_time ON email_events(event_at);
CREATE INDEX idx_activities_opened ON activities(email_opened) WHERE email_opened = TRUE;
CREATE INDEX idx_activities_clicked ON activities(email_clicked) WHERE email_clicked = TRUE;

-- Trigger to update activity when email_events received
CREATE OR REPLACE FUNCTION update_activity_email_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.event_type = 'opened' THEN
        UPDATE activities SET
            email_opened = TRUE,
            email_opened_at = COALESCE(email_opened_at, NEW.event_at),
            email_open_count = email_open_count + 1,
            time_to_open_minutes = EXTRACT(EPOCH FROM (NEW.event_at - created_at)) / 60
        WHERE id = NEW.activity_id;
    ELSIF NEW.event_type = 'clicked' THEN
        UPDATE activities SET
            email_clicked = TRUE,
            email_clicked_at = COALESCE(email_clicked_at, NEW.event_at),
            email_click_count = email_click_count + 1,
            time_to_click_minutes = EXTRACT(EPOCH FROM (NEW.event_at - created_at)) / 60
        WHERE id = NEW.activity_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_email_event
    AFTER INSERT ON email_events
    FOR EACH ROW
    EXECUTE FUNCTION update_activity_email_stats();
```

**Tasks:**

| ID | Task | Est |
|----|------|-----|
| ENGAGE-001 | Create migration 026_email_engagement.sql | 2h |
| ENGAGE-002 | Integrate Smartlead/Salesforge webhooks for open/click | 4h |
| ENGAGE-003 | Create email_events ingestion service | 3h |
| ENGAGE-004 | Update activity creation to set touch_number, days_since_last | 2h |
| ENGAGE-005 | Add timezone lookup (from lead location) | 2h |
| ENGAGE-006 | Update WHEN Detector to use engagement timing | 3h |
| ENGAGE-007 | Update HOW Detector to use open/click correlation | 3h |

**Total:** 19 hours

---

### Phase 24D: Conversation Threading (NEW)

**Migration:** `027_conversation_threads.sql`

```sql
-- 1. Create conversation threads table
CREATE TABLE conversation_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    campaign_id UUID REFERENCES campaigns(id),
    
    -- Thread status
    status TEXT DEFAULT 'active',  -- 'active', 'resolved', 'stale'
    channel channel_type NOT NULL,
    
    -- Thread metrics
    message_count INTEGER DEFAULT 0,
    our_message_count INTEGER DEFAULT 0,
    their_message_count INTEGER DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    last_our_message_at TIMESTAMPTZ,
    last_their_message_at TIMESTAMPTZ,
    
    -- Outcome
    outcome TEXT,  -- 'converted', 'rejected', 'no_response', 'ongoing'
    outcome_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create thread messages table
CREATE TABLE thread_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id),
    activity_id UUID REFERENCES activities(id),  -- NULL if it's their reply
    reply_id UUID REFERENCES replies(id),  -- NULL if it's our message
    
    direction TEXT NOT NULL,  -- 'outbound' (us) or 'inbound' (them)
    content TEXT NOT NULL,
    content_preview TEXT,  -- First 200 chars
    
    -- Analysis (populated by AI or rules)
    sentiment TEXT,  -- 'positive', 'neutral', 'negative'
    sentiment_score FLOAT,  -- -1 to 1
    intent TEXT,  -- 'interested', 'question', 'objection', 'not_interested', etc.
    objection_type TEXT,  -- 'timing', 'budget', 'authority', 'need', 'competitor'
    question_extracted TEXT,  -- The actual question they asked
    
    -- Timing
    sent_at TIMESTAMPTZ NOT NULL,
    response_time_minutes INTEGER,  -- How long until this message (if reply)
    
    position INTEGER NOT NULL,  -- 1, 2, 3... in thread
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Add thread reference to activities and replies
ALTER TABLE activities ADD COLUMN thread_id UUID REFERENCES conversation_threads(id);
ALTER TABLE replies ADD COLUMN thread_id UUID REFERENCES conversation_threads(id);
ALTER TABLE replies ADD COLUMN objection_type TEXT;
ALTER TABLE replies ADD COLUMN question_extracted TEXT;
ALTER TABLE replies ADD COLUMN sentiment TEXT;
ALTER TABLE replies ADD COLUMN sentiment_score FLOAT;

-- 4. Create rejection reasons enum and field
CREATE TYPE rejection_reason_type AS ENUM (
    'timing_not_now',
    'budget_constraints',
    'using_competitor',
    'not_decision_maker',
    'no_need',
    'bad_experience',
    'too_busy',
    'not_interested_generic',
    'do_not_contact',
    'other'
);

ALTER TABLE leads ADD COLUMN rejection_reason rejection_reason_type;
ALTER TABLE leads ADD COLUMN rejection_notes TEXT;

-- Indexes
CREATE INDEX idx_threads_client ON conversation_threads(client_id);
CREATE INDEX idx_threads_lead ON conversation_threads(lead_id);
CREATE INDEX idx_threads_status ON conversation_threads(status);
CREATE INDEX idx_thread_messages_thread ON thread_messages(thread_id);
CREATE INDEX idx_thread_messages_direction ON thread_messages(direction);
CREATE INDEX idx_thread_messages_sentiment ON thread_messages(sentiment);
CREATE INDEX idx_thread_messages_objection ON thread_messages(objection_type);

-- Trigger to update thread stats
CREATE OR REPLACE FUNCTION update_thread_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversation_threads SET
        message_count = message_count + 1,
        our_message_count = our_message_count + CASE WHEN NEW.direction = 'outbound' THEN 1 ELSE 0 END,
        their_message_count = their_message_count + CASE WHEN NEW.direction = 'inbound' THEN 1 ELSE 0 END,
        last_message_at = NEW.sent_at,
        last_our_message_at = CASE WHEN NEW.direction = 'outbound' THEN NEW.sent_at ELSE last_our_message_at END,
        last_their_message_at = CASE WHEN NEW.direction = 'inbound' THEN NEW.sent_at ELSE last_their_message_at END,
        updated_at = NOW()
    WHERE id = NEW.thread_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_thread_message
    AFTER INSERT ON thread_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_thread_stats();
```

**Tasks:**

| ID | Task | Est |
|----|------|-----|
| THREAD-001 | Create migration 027_conversation_threads.sql | 2h |
| THREAD-002 | Create ThreadService (create, add message, close) | 4h |
| THREAD-003 | Update Closer Engine to create/manage threads | 3h |
| THREAD-004 | Integrate reply analysis (sentiment, objection, question) | 4h |
| THREAD-005 | Create rejection reason classifier | 3h |
| THREAD-006 | Update activities/replies to link to threads | 2h |
| THREAD-007 | Create conversation analytics queries | 2h |
| THREAD-008 | Update CIS to learn from conversation patterns | 4h |

**Total:** 24 hours

---

### Phase 24E: Downstream Outcome Tracking (NEW)

**Migration:** `028_downstream_outcomes.sql`

```sql
-- 1. Expand meetings table
ALTER TABLE meetings ADD COLUMN showed_up BOOLEAN;
ALTER TABLE meetings ADD COLUMN showed_up_confirmed_at TIMESTAMPTZ;
ALTER TABLE meetings ADD COLUMN meeting_outcome TEXT;  -- 'good', 'bad', 'rescheduled', 'no_show'
ALTER TABLE meetings ADD COLUMN meeting_notes TEXT;
ALTER TABLE meetings ADD COLUMN next_steps TEXT;
ALTER TABLE meetings ADD COLUMN deal_created BOOLEAN DEFAULT FALSE;

-- 2. Create deals table (lightweight CRM)
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID NOT NULL REFERENCES clients(id),
    lead_id UUID NOT NULL REFERENCES leads(id),
    meeting_id UUID REFERENCES meetings(id),
    
    -- Deal info
    name TEXT NOT NULL,
    value DECIMAL(12,2),
    currency TEXT DEFAULT 'AUD',
    
    -- Stage tracking
    stage TEXT DEFAULT 'qualification',  -- 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'
    stage_changed_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Outcome
    closed_at TIMESTAMPTZ,
    won BOOLEAN,
    lost_reason TEXT,
    
    -- Timing
    days_to_close INTEGER,  -- Calculated when closed
    
    -- Attribution
    converting_activity_id UUID REFERENCES activities(id),
    converting_channel channel_type,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create deal stage history
CREATE TABLE deal_stage_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deal_id UUID NOT NULL REFERENCES deals(id),
    from_stage TEXT,
    to_stage TEXT NOT NULL,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    changed_by TEXT  -- 'system', 'user', 'webhook'
);

-- Indexes
CREATE INDEX idx_deals_client ON deals(client_id);
CREATE INDEX idx_deals_lead ON deals(lead_id);
CREATE INDEX idx_deals_stage ON deals(stage);
CREATE INDEX idx_deals_won ON deals(won) WHERE won IS NOT NULL;
CREATE INDEX idx_deal_history_deal ON deal_stage_history(deal_id);

-- Trigger to track stage changes
CREATE OR REPLACE FUNCTION track_deal_stage_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.stage IS DISTINCT FROM NEW.stage THEN
        INSERT INTO deal_stage_history (deal_id, from_stage, to_stage, changed_by)
        VALUES (NEW.id, OLD.stage, NEW.stage, 'system');
        
        NEW.stage_changed_at = NOW();
        
        -- Calculate days to close if closed
        IF NEW.stage IN ('closed_won', 'closed_lost') AND NEW.closed_at IS NULL THEN
            NEW.closed_at = NOW();
            NEW.days_to_close = EXTRACT(DAY FROM (NOW() - NEW.created_at));
            NEW.won = (NEW.stage = 'closed_won');
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER on_deal_stage_change
    BEFORE UPDATE ON deals
    FOR EACH ROW
    EXECUTE FUNCTION track_deal_stage_change();
```

**Tasks:**

| ID | Task | Est |
|----|------|-----|
| OUTCOME-001 | Create migration 028_downstream_outcomes.sql | 2h |
| OUTCOME-002 | Create DealService (create, update stage, close) | 3h |
| OUTCOME-003 | Add meeting outcome tracking to Closer Engine | 2h |
| OUTCOME-004 | Create webhook endpoint for CRM integration | 3h |
| OUTCOME-005 | Update CIS to learn from deal outcomes | 4h |
| OUTCOME-006 | Add deal analytics (conversion rate, avg value, cycle time) | 3h |
| OUTCOME-007 | Add show rate tracking | 2h |

**Total:** 19 hours

---

## Summary: All Implementation Tasks

| Phase | Focus | Tasks | Hours |
|-------|-------|-------|-------|
| **24A** | Lead Pool (Lead Data Gaps) | POOL-001 to POOL-015 | 43h |
| **24B** | Content & Template Tracking | CONTENT-001 to CONTENT-007 | 16h |
| **24C** | Email Engagement Tracking | ENGAGE-001 to ENGAGE-007 | 19h |
| **24D** | Conversation Threading | THREAD-001 to THREAD-008 | 24h |
| **24E** | Downstream Outcomes | OUTCOME-001 to OUTCOME-007 | 19h |
| **TOTAL** | | **51 tasks** | **121 hours** |

---

## CIS Detector Updates Required

After implementing above, update CIS detectors:

| Detector | Updates Needed |
|----------|----------------|
| **WHO** | Use new lead fields (seniority, revenue, tech stack, location) |
| **WHAT** | Use template linking, A/B test results, full message body |
| **WHEN** | Use email open/click times, lead timezone, touch metadata |
| **HOW** | Use email engagement correlation, channel preference signals |
| **NEW: CONVERSATION** | Learn from objection types, sentiment, thread patterns |
| **NEW: FUNNEL** | Learn from show rate, deal conversion, lost reasons |

---

## Priority Order

### Must Have (Before Launch)
1. **Phase 24A** — Lead Pool (fixes data foundation)
2. **Phase 24C** — Email Engagement (critical for learning)

### Should Have (Shortly After Launch)
3. **Phase 24B** — Content Tracking (enables A/B testing)
4. **Phase 24D** — Conversation Threading (learns from replies)

### Nice to Have (Growth Phase)
5. **Phase 24E** — Downstream Outcomes (full funnel learning)

---

## Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/025_content_tracking.sql` | Content & A/B schema |
| `supabase/migrations/026_email_engagement.sql` | Email events schema |
| `supabase/migrations/027_conversation_threads.sql` | Thread tracking schema |
| `supabase/migrations/028_downstream_outcomes.sql` | Deals & outcomes schema |
| `src/services/ab_test_service.py` | A/B test management |
| `src/services/email_events_service.py` | Email engagement ingestion |
| `src/services/thread_service.py` | Conversation threading |
| `src/services/deal_service.py` | Deal tracking |
| `src/services/reply_analyzer.py` | Sentiment, objection, question extraction |
| `src/algorithms/conversation_detector.py` | New CIS detector for conversations |
| `src/algorithms/funnel_detector.py` | New CIS detector for downstream outcomes |

---

## Success Criteria

After implementation, CIS should be able to answer:

| Question | Currently | After |
|----------|-----------|-------|
| Which seniority level converts best? | ❌ Can't answer | ✅ Yes |
| Which email subject lines get opened? | ❌ Can't answer | ✅ Yes |
| What time do our leads read emails? | ❌ Can't answer | ✅ Yes |
| What objections do we hear most? | ❌ Can't answer | ✅ Yes |
| Which A/B variant won? | ❌ Can't answer | ✅ Yes |
| What's our show rate? | ❌ Can't answer | ✅ Yes |
| Which leads become deals? | ❌ Can't answer | ✅ Yes |
| What's our average deal value? | ❌ Can't answer | ✅ Yes |

---

## Sign-Off

| Role | Name | Date | Approved |
|------|------|------|----------|
| CEO | Dave | | |
| Technical Review | Claude | January 6, 2026 | ✅ |
