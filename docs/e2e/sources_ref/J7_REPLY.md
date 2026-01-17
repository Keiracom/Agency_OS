# J7: Reply Handling Journey

**Status:** 🟡 Sub-tasks Defined (Pending CEO Approval)
**Priority:** P1 — Conversion-critical pathway
**Depends On:** J3-J6 Complete (need outreach to generate replies)
**Last Updated:** January 11, 2026
**Sub-Tasks:** 14 groups, 56 individual checks

---

## Overview

Tests inbound reply handling across all channels with AI intent classification and conversation threading.

**Key Finding from Code Review:**
- Closer engine uses Claude for intent classification (7 intent types)
- Phase 24D adds conversation threading with ThreadService
- ReplyAnalyzer provides sentiment, objection, and question extraction
- Reply recovery flow polls every 6 hours as safety net (webhooks are primary)

**User Journey:**
```
Inbound Reply → Webhook Received → Lead Matched → AI Classification → Thread Updated → Lead Status Updated → Client Notified (if hot)
```

---

## Test Recipients (TEST_MODE)

| Field | Value |
|-------|-------|
| Test Email | david.stephens@keiracom.com |
| Test Phone | +61457543392 |
| Test LinkedIn | https://www.linkedin.com/in/david-stephens-8847a636a/ |
| TEST_MODE Setting | `settings.TEST_MODE` |
| Note | Replies must match leads created during J3-J6 testing |

---

## Sub-Tasks

### J7.1 — Email Reply Webhook (Postmark)
**Purpose:** Verify email replies are received and processed via Postmark.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.1.1 | Read `webhooks.py` — verify `/webhooks/postmark/inbound` endpoint | Send test email reply |
| J7.1.2 | Verify `postmark.parse_inbound_webhook` call (line 277) | Check logs for parsing |
| J7.1.3 | Verify lead matched by email address | Check lead found |
| J7.1.4 | Verify `closer.process_reply` called (line 300) | Check activity created |
| J7.1.5 | Verify `in_reply_to` header extracted | Check thread linking |

**Webhook Endpoint (VERIFIED):**
```python
# src/api/routes/webhooks.py lines 242-340
@router.post("/postmark/inbound")
async def postmark_inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
```

**Pass Criteria:**
- [ ] Postmark webhook endpoint exists
- [ ] Payload parsed correctly
- [ ] Lead matched by email
- [ ] Reply processed via Closer engine

<!-- E2E_SESSION_BREAK: J7.1 complete. Next: J7.2 SMS Reply Webhook -->

---

### J7.2 — SMS Reply Webhook (Twilio)
**Purpose:** Verify SMS replies are received and processed via Twilio.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.2.1 | Read `webhooks.py` — verify `/webhooks/twilio/inbound` endpoint (line 474) | Send test SMS reply |
| J7.2.2 | Verify Twilio signature validation (lines 90-113) | Check validation passes |
| J7.2.3 | Verify `twilio.parse_inbound_webhook` call (line 511) | Check parsing |
| J7.2.4 | Verify lead matched by phone number | Check lead found |
| J7.2.5 | Verify `closer.process_reply` called (line 535) | Check activity created |

**Twilio Signature Validation (VERIFIED):**
```python
# src/api/routes/webhooks.py lines 90-113
def verify_twilio_signature(request: Request, url: str, params: dict) -> bool:
    # Verify Twilio webhook signature using X-Twilio-Signature header
```

**Pass Criteria:**
- [ ] Twilio inbound webhook endpoint exists
- [ ] Signature validation implemented
- [ ] Payload parsed correctly
- [ ] Lead matched by phone

<!-- E2E_SESSION_BREAK: J7.2 complete. Next: J7.3 LinkedIn Reply Webhook -->

---

### J7.3 — LinkedIn Reply Webhook (HeyReach)
**Purpose:** Verify LinkedIn replies are received and processed via HeyReach.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.3.1 | Read `webhooks.py` — verify `/webhooks/heyreach/inbound` endpoint (line 656) | Trigger test reply |
| J7.3.2 | Verify reply type check (line 687) | N/A |
| J7.3.3 | Verify lead matched by LinkedIn URL | Check lead found |
| J7.3.4 | Verify `closer.process_reply` called (line 710) | Check activity created |

**HeyReach Webhook (VERIFIED):**
```python
# src/api/routes/webhooks.py lines 656-749
@router.post("/heyreach/inbound")
async def heyreach_inbound_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
```

**Pass Criteria:**
- [ ] HeyReach webhook endpoint exists
- [ ] Reply type filtered (not connections)
- [ ] Lead matched by LinkedIn URL
- [ ] Reply processed via Closer engine

<!-- E2E_SESSION_BREAK: J7.3 complete. Next: J7.4 Closer Engine Intent Classification -->

---

### J7.4 — Closer Engine Intent Classification
**Purpose:** Verify AI-powered intent classification works correctly.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.4.1 | Read `src/engines/closer.py` — verify 7 intent types (lines 39-47) | N/A |
| J7.4.2 | Verify `anthropic.classify_intent` call (line 164) | Test classification |
| J7.4.3 | Verify confidence score returned | Check confidence > 0.7 |
| J7.4.4 | Verify reasoning captured | Check reasoning in result |
| J7.4.5 | Test all 7 intent types | Send 7 different replies |

**Intent Types (VERIFIED from closer.py lines 39-47):**
```python
INTENT_MAP = {
    "meeting_request": IntentType.MEETING_REQUEST,
    "interested": IntentType.INTERESTED,
    "question": IntentType.QUESTION,
    "not_interested": IntentType.NOT_INTERESTED,
    "unsubscribe": IntentType.UNSUBSCRIBE,
    "out_of_office": IntentType.OUT_OF_OFFICE,
    "auto_reply": IntentType.AUTO_REPLY,
}
```

**Pass Criteria:**
- [ ] All 7 intent types recognized
- [ ] Confidence scores returned
- [ ] AI reasoning captured
- [ ] Low-confidence triggers fallback

<!-- E2E_SESSION_BREAK: J7.4 complete. Next: J7.5 Reply Analyzer -->

---

### J7.5 — Reply Analyzer (Phase 24D)
**Purpose:** Verify sentiment, objection, and question analysis.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.5.1 | Read `src/services/reply_analyzer.py` — verify complete (501 lines) | N/A |
| J7.5.2 | Verify sentiment detection (positive, neutral, negative, mixed) | Test various sentiments |
| J7.5.3 | Verify objection types (timing, budget, authority, need, competitor, trust) | Test objection replies |
| J7.5.4 | Verify question extraction | Test question replies |
| J7.5.5 | Verify topic extraction | Check topics identified |
| J7.5.6 | Verify AI analysis with rule-based fallback | Disable AI, test rules |

**Objection Types (VERIFIED from reply_analyzer.py lines 31-58):**
- timing: "not now", "next quarter", etc.
- budget: "expensive", "can't afford", etc.
- authority: "not my decision", "need to ask", etc.
- need: "don't need", "already have", etc.
- competitor: "using another", "contract with", etc.
- trust: "never heard of", "is this legit", etc.

**Pass Criteria:**
- [ ] Sentiment detected correctly
- [ ] Objection types identified
- [ ] Questions extracted
- [ ] Topics identified
- [ ] Fallback rules work

<!-- E2E_SESSION_BREAK: J7.5 complete. Next: J7.6 Conversation Threading -->

---

### J7.6 — Conversation Threading (Phase 24D)
**Purpose:** Verify conversation threads are created and managed.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.6.1 | Read `src/services/thread_service.py` — verify complete | N/A |
| J7.6.2 | Verify `get_or_create_for_lead` method | Test thread creation |
| J7.6.3 | Verify thread status: active, stale, closed | Check status transitions |
| J7.6.4 | Verify `add_message` method | Test message adding |
| J7.6.5 | Verify message direction: inbound vs outbound | Check direction set |
| J7.6.6 | Verify activity linked to thread (conversation_thread_id) | Check activity.conversation_thread_id |

**ThreadService Methods (VERIFIED):**
- `create_thread()` — Create new conversation thread
- `get_by_id()` — Get thread by UUID
- `get_or_create_for_lead()` — Find existing or create new
- `add_message()` — Add message with sentiment/intent/objection
- `update_status()` — Update thread status
- `set_outcome()` — Set final outcome (meeting_booked, rejected, etc.)

**Pass Criteria:**
- [ ] Thread created on first reply
- [ ] Existing thread reused for same lead/channel
- [ ] Messages tracked with position
- [ ] Activity linked to thread

<!-- E2E_SESSION_BREAK: J7.6 complete. Next: J7.7 Lead Status Updates -->

---

### J7.7 — Lead Status Updates
**Purpose:** Verify lead status updates based on reply intent.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.7.1 | Read `_handle_intent` method (closer.py lines 413-498) | N/A |
| J7.7.2 | Verify MEETING_REQUEST → CONVERTED status | Test meeting request |
| J7.7.3 | Verify INTERESTED → stays IN_SEQUENCE | Test interested reply |
| J7.7.4 | Verify NOT_INTERESTED → pauses outreach | Test not interested |
| J7.7.5 | Verify UNSUBSCRIBE → UNSUBSCRIBED status | Test unsubscribe |
| J7.7.6 | Verify OUT_OF_OFFICE → schedules 2-week follow-up | Test OOO reply |
| J7.7.7 | Verify `last_replied_at` and `reply_count` updated | Check lead fields |

**Intent → Status Mapping (VERIFIED):**
| Intent | Status Update | Additional Action |
|--------|--------------|-------------------|
| meeting_request | CONVERTED | Created meeting task |
| interested | Stay IN_SEQUENCE | Created follow-up task |
| question | No change | Created response task |
| not_interested | Back to ENRICHED | Paused outreach |
| unsubscribe | UNSUBSCRIBED | Suppression list |
| out_of_office | No change | Schedule 2-week follow-up |
| auto_reply | No change | Ignored |

**Pass Criteria:**
- [ ] Status updates correctly per intent
- [ ] reply_count incremented
- [ ] last_replied_at updated
- [ ] Tasks created for actionable intents

<!-- E2E_SESSION_BREAK: J7.7 complete. Next: J7.8 Objection Tracking -->

---

### J7.8 — Objection Tracking (Phase 24D)
**Purpose:** Verify objections are tracked for CIS learning.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.8.1 | Read `_record_rejection` method (closer.py lines 500-538) | N/A |
| J7.8.2 | Verify rejection_reason field updated | Check lead.rejection_reason |
| J7.8.3 | Verify rejection_at timestamp set | Check lead.rejection_at |
| J7.8.4 | Read `_add_objection_to_history` method (lines 540-566) | N/A |
| J7.8.5 | Verify objections_raised array updated | Check lead.objections_raised |

**Rejection Reason Mapping (VERIFIED):**
```python
rejection_map = {
    "timing": "timing_not_now",
    "budget": "budget_constraints",
    "authority": "not_decision_maker",
    "need": "no_need",
    "competitor": "using_competitor",
    "trust": "other",
    "do_not_contact": "do_not_contact",
    "other": "not_interested_generic",
}
```

**Pass Criteria:**
- [ ] Rejection reason recorded
- [ ] Timestamp captured
- [ ] Objections added to history array
- [ ] CIS can query rejection patterns

<!-- E2E_SESSION_BREAK: J7.8 complete. Next: J7.9 Thread Outcome -->

---

### J7.9 — Thread Outcome (Phase 24D)
**Purpose:** Verify thread outcomes are set based on reply intent.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.9.1 | Read `_update_thread_outcome` method (closer.py lines 568-601) | N/A |
| J7.9.2 | Verify meeting_request → outcome="meeting_booked" | Test meeting reply |
| J7.9.3 | Verify not_interested/unsubscribe → outcome="rejected" | Test rejection |
| J7.9.4 | Verify interested/question → thread stays active | Test positive reply |

**Pass Criteria:**
- [ ] Thread outcome set correctly
- [ ] Outcome reason captured
- [ ] Positive intents keep thread active
- [ ] Negative intents close thread

<!-- E2E_SESSION_BREAK: J7.9 complete. Next: J7.10 Activity Logging -->

---

### J7.10 — Activity Logging
**Purpose:** Verify all replies create comprehensive activity records.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.10.1 | Read `_log_reply_activity` method (closer.py lines 356-411) | N/A |
| J7.10.2 | Verify action="replied" | Check activity.action |
| J7.10.3 | Verify intent and intent_confidence stored | Check activity fields |
| J7.10.4 | Verify content_preview stored (500 chars) | Check preview |
| J7.10.5 | Verify conversation_thread_id linked | Check thread link |
| J7.10.6 | Verify provider_message_id stored | Check dedup field |

**Activity Fields (VERIFIED):**
- action = "replied"
- channel (email, sms, linkedin)
- intent, intent_confidence
- provider_message_id, in_reply_to
- content_preview (500 chars)
- conversation_thread_id (Phase 24D)
- metadata: message_preview, message_length

**Pass Criteria:**
- [ ] Activity created for every reply
- [ ] Intent classification recorded
- [ ] Thread linked
- [ ] Deduplication by provider_message_id

<!-- E2E_SESSION_BREAK: J7.10 complete. Next: J7.11 Reply Recovery Flow -->

---

### J7.11 — Reply Recovery Flow (Safety Net)
**Purpose:** Verify 6-hourly polling catches missed webhook replies.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.11.1 | Read `src/orchestration/flows/reply_recovery_flow.py` (548 lines) | N/A |
| J7.11.2 | Verify `poll_email_replies_task` polls Postmark | Check logs |
| J7.11.3 | Verify `poll_sms_replies_task` polls Twilio | Check logs |
| J7.11.4 | Verify `poll_linkedin_replies_task` polls HeyReach | Check logs |
| J7.11.5 | Verify deduplication check (lines 255-287) | Simulate duplicate |
| J7.11.6 | Verify `process_missed_reply_task` calls Closer | Check processing |
| J7.11.7 | Trigger flow manually in Prefect | Check recovery runs |

**Flow Tasks (VERIFIED):**
- poll_email_replies_task (Postmark)
- poll_sms_replies_task (Twilio)
- poll_linkedin_replies_task (HeyReach)
- find_lead_by_contact_task
- check_if_reply_processed_task
- process_missed_reply_task

**Pass Criteria:**
- [ ] Polls all 3 channels
- [ ] Deduplication prevents double processing
- [ ] Missed replies processed correctly
- [ ] Flow runs on 6-hour schedule (PAUSED by default)

<!-- E2E_SESSION_BREAK: J7.11 complete. Next: J7.12 Email Event Webhooks -->

---

### J7.12 — Email Event Webhooks (Opens/Clicks/Bounces)
**Purpose:** Verify email engagement events are tracked.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.12.1 | Read `/webhooks/postmark/bounce` endpoint (line 340) | N/A |
| J7.12.2 | Read `/webhooks/postmark/spam` endpoint (line 410) | N/A |
| J7.12.3 | Read `/webhooks/email/resend` endpoint (line 1169) | N/A |
| J7.12.4 | Read `/webhooks/salesforge/events` endpoint (line 1003) | N/A |
| J7.12.5 | Verify bounce updates lead status | Test bounce event |
| J7.12.6 | Verify spam complaint triggers unsubscribe | Test spam event |

**Event Types Tracked:**
- sent, delivered
- opened (first and repeat)
- clicked (with URL)
- bounced (hard/soft)
- complained, unsubscribed

**Pass Criteria:**
- [ ] Bounce webhook updates lead
- [ ] Spam complaint triggers unsubscribe
- [ ] Opens/clicks tracked in activity

<!-- E2E_SESSION_BREAK: J7.12 complete. J7 JOURNEY COMPLETE. Next: J8 Meeting & Deals -->

---

### J7.13 — Error Handling
**Purpose:** Verify graceful error handling for reply processing.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.13.1 | Verify try/catch in closer.py `process_reply` (lines 139-249) | Test invalid lead |
| J7.13.2 | Verify EngineResult.fail returned on error | Check return structure |
| J7.13.3 | Verify webhook returns 200 even on processing error | Check webhook response |
| J7.13.4 | Verify retries on flow tasks (3x) | Check task decorator |
| J7.13.5 | Verify unknown lead doesn't crash webhook | Test unknown sender |

**Retry Configuration:**
```python
@task(name="process_missed_reply", retries=3, retry_delay_seconds=10)
```

**Pass Criteria:**
- [ ] Errors don't crash webhook
- [ ] Retries attempted
- [ ] Unknown senders logged but don't crash
- [ ] EngineResult.fail returned on error

---

### J7.14 — Live Reply Test (All Channels)
**Purpose:** Verify real replies work end-to-end.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J7.14.1 | N/A | Send email reply to outreach message |
| J7.14.2 | N/A | Reply to SMS message |
| J7.14.3 | N/A | Reply to LinkedIn connection/message |
| J7.14.4 | N/A | Verify intent classified correctly |
| J7.14.5 | N/A | Verify thread created |
| J7.14.6 | N/A | Verify lead status updated |
| J7.14.7 | N/A | Verify activity logged |

**Pass Criteria:**
- [ ] Email reply processed successfully
- [ ] SMS reply processed successfully
- [ ] LinkedIn reply processed successfully
- [ ] Intent classification accurate
- [ ] Conversation thread created
- [ ] Lead status updated per intent

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Closer Engine | `src/engines/closer.py` | 647 | ✅ VERIFIED |
| Webhook Routes | `src/api/routes/webhooks.py` | 1600+ | ✅ VERIFIED |
| Reply Recovery Flow | `src/orchestration/flows/reply_recovery_flow.py` | 548 | ✅ VERIFIED |
| Thread Service | `src/services/thread_service.py` | 200+ | ✅ VERIFIED |
| Reply Analyzer | `src/services/reply_analyzer.py` | 501 | ✅ VERIFIED |
| Postmark Integration | `src/integrations/postmark.py` | - | Parse webhooks |
| Twilio Integration | `src/integrations/twilio.py` | - | Parse webhooks |
| HeyReach Integration | `src/integrations/heyreach.py` | - | Parse webhooks |

---

## Completion Criteria

All checks must pass:

- [ ] **J7.1** Email reply webhook works (Postmark)
- [ ] **J7.2** SMS reply webhook works (Twilio)
- [ ] **J7.3** LinkedIn reply webhook works (HeyReach)
- [ ] **J7.4** Intent classification works (7 types)
- [ ] **J7.5** Reply analyzer works (sentiment, objections)
- [ ] **J7.6** Conversation threading works
- [ ] **J7.7** Lead status updates per intent
- [ ] **J7.8** Objection tracking works
- [ ] **J7.9** Thread outcomes set correctly
- [ ] **J7.10** Activities logged with all fields
- [ ] **J7.11** Reply recovery flow runs
- [ ] **J7.12** Email events tracked
- [ ] **J7.13** Errors handled gracefully
- [ ] **J7.14** **Live reply test passes all channels**

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Closer engine is comprehensive (647 lines)
2. ✅ 7 intent types with AI classification
3. ✅ Phase 24D conversation threading implemented
4. ✅ Reply analyzer with sentiment + objection detection
5. ✅ Webhooks for all 3 channels (email, SMS, LinkedIn)
6. ✅ Reply recovery flow as safety net (6-hourly)
7. ✅ Objection/rejection tracking for CIS learning
8. ✅ Activity logging with thread linking

**No Issues Found** - Reply handling is well-implemented.

---

## Notes

**Intent Classification AI:**
Claude is used for intent classification with ~$0.01-0.02 per classification. This adds up with high reply volume - consider caching common patterns or using rule-based fallback for obvious intents.

**Webhook-First Architecture (Rule 20):**
Webhooks are the PRIMARY mechanism for reply handling. The reply recovery flow is a SAFETY NET that runs every 6 hours to catch any missed webhooks. Don't rely on polling as primary.

**Testing Replies:**
To test live replies, you must first send outreach via J3-J6. The lead must exist in the database with matching email/phone/LinkedIn for the webhook to find and process the reply.
