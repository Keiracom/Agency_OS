# J8: Meeting & Deals Journey

**Status:** 🟢 Ready for Testing
**Priority:** P1 — Revenue attribution pathway
**Depends On:** J7 Complete (need replies to generate meetings)
**Last Updated:** January 11, 2026
**Sub-Tasks:** 14 groups, 58 individual checks

---

## Overview

Tests meeting booking, deal creation, CRM integration, and downstream revenue attribution.

**Key Finding from Code Review:**
- MeetingService is comprehensive (839 lines)
- DealService is comprehensive (867 lines)
- CRM push supports HubSpot, Pipedrive, Close
- Both Calendly and Cal.com webhook handlers implemented
- Revenue attribution with first_touch, last_touch, linear, time_decay models

**✅ RESOLVED (January 11, 2026):**
Cal.com webhook handler has been implemented:
- `_handle_calcom_webhook` in `webhooks.py` (lines 1589-1722)
- Handles BOOKING_CREATED, BOOKING_CANCELLED, BOOKING_RESCHEDULED events
- Lead matching by attendee email
- Duration calculated from start/end times
- Meeting type detection from event type slug

**User Journey:**
```
Meeting Request → Calendly/Cal.com Booking → Webhook → Meeting Created → CRM Pushed → Meeting Outcome → Deal Created → Pipeline Stages → Closed Won/Lost → Revenue Attribution
```

---

## Test Recipients (TEST_MODE)

| Field | Value |
|-------|-------|
| Test Email | david.stephens@keiracom.com |
| Note | Meetings are created from converted leads |

---

## Sub-Tasks

### J8.1 — Meeting Webhook (Calendly)
**Purpose:** Verify Calendly webhooks create meetings.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.1.1 | Read `webhooks.py` — verify `/webhooks/crm/meeting` endpoint (line 1365) | Send test webhook |
| J8.1.2 | Read `_handle_calendly_webhook` (lines 1493-1559) | N/A |
| J8.1.3 | Verify lead matched by email | Check lead lookup |
| J8.1.4 | Verify meeting created via MeetingService | Check meeting record |
| J8.1.5 | Verify calendar_event_id stored | Check deduplication |

**Calendly Webhook Handler (VERIFIED):**
```python
# src/api/routes/webhooks.py lines 1493-1559
async def _handle_calendly_webhook(db, payload: dict, meeting_service) -> dict:
    # Handles: invitee.created, invitee.canceled
```

**Pass Criteria:**
- [ ] Calendly webhook endpoint exists
- [ ] Meeting created on invitee.created event
- [ ] Meeting cancelled on invitee.canceled event
- [ ] Lead linked correctly

<!-- E2E_SESSION_BREAK: J8.1 complete. Next: J8.2 Meeting Webhook (Cal.com) -->

---

### J8.2 — Meeting Webhook (Cal.com)
**Purpose:** Verify Cal.com webhooks create meetings.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.2.1 | Read `_handle_calcom_webhook` (lines 1562-1566) | N/A |
| J8.2.2 | ⚠️ **VERIFY:** Cal.com handler NOT fully implemented | Check response |

**⚠️ ISSUE FOUND:**
```python
# src/api/routes/webhooks.py line 1566
return {"status": "ignored", "reason": "calcom_not_fully_implemented"}
```

**Pass Criteria:**
- [ ] ⚠️ **Cal.com handler is NOT implemented** — returns "ignored"
- [ ] CEO Decision: Implement Cal.com or use Calendly only?

<!-- E2E_SESSION_BREAK: J8.2 complete. Next: J8.3 MeetingService Implementation -->

---

### J8.3 — MeetingService Implementation
**Purpose:** Verify MeetingService is complete.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.3.1 | Read `src/services/meeting_service.py` (839 lines) | N/A |
| J8.3.2 | Verify `create` method with all fields | Test meeting creation |
| J8.3.3 | Verify `confirm` method | Test confirmation |
| J8.3.4 | Verify `send_reminder` method | Test reminder marking |
| J8.3.5 | Verify `record_show` method | Test show/no-show |
| J8.3.6 | Verify `record_outcome` method | Test outcome recording |
| J8.3.7 | Verify `reschedule` method | Test reschedule |
| J8.3.8 | Verify `cancel` method | Test cancellation |

**Meeting Types (VERIFIED from meeting_service.py lines 31-38):**
- discovery
- demo
- follow_up
- close
- onboarding
- other

**Meeting Outcomes (VERIFIED from meeting_service.py lines 41-48):**
- good
- bad
- rescheduled
- no_show
- cancelled
- pending

**Pass Criteria:**
- [ ] All CRUD methods implemented
- [ ] Meeting types validated
- [ ] Outcomes validated
- [ ] Lead updated with meeting info

<!-- E2E_SESSION_BREAK: J8.3 complete. Next: J8.4 Meeting Tracking Fields -->

---

### J8.4 — Meeting Tracking Fields
**Purpose:** Verify meeting analytics fields are captured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.4.1 | Verify `touches_before_booking` calculated | Check field |
| J8.4.2 | Verify `days_to_booking` calculated | Check field |
| J8.4.3 | Verify `converting_activity_id` stored | Check attribution |
| J8.4.4 | Verify `converting_channel` stored | Check attribution |
| J8.4.5 | Verify `original_scheduled_at` preserved on reschedule | Check field |

**Meeting Analytics Fields (VERIFIED):**
- touches_before_booking (count of activities before meeting)
- days_to_booking (days from first touch to booking)
- converting_activity_id (which activity led to booking)
- converting_channel (which channel converted)
- rescheduled_count (how many times rescheduled)

**Pass Criteria:**
- [ ] Touches calculated correctly
- [ ] Days to booking accurate
- [ ] Attribution fields populated
- [ ] Reschedule tracking works

<!-- E2E_SESSION_BREAK: J8.4 complete. Next: J8.5 Meeting Reminder System -->

---

### J8.5 — Meeting Reminder System
**Purpose:** Verify meeting reminders work.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.5.1 | Read `list_needing_reminder` method | N/A |
| J8.5.2 | Verify 24-hour reminder window | Check query |
| J8.5.3 | Verify `reminder_sent` flag updated | Check field |
| J8.5.4 | Verify `reminder_sent_at` timestamp | Check field |

**Pass Criteria:**
- [ ] Reminder query returns correct meetings
- [ ] Reminder sent tracking works
- [ ] 24-hour window configurable

<!-- E2E_SESSION_BREAK: J8.5 complete. Next: J8.6 Show Rate Tracking -->

---

### J8.6 — Show Rate Tracking
**Purpose:** Verify show/no-show tracking for CIS learning.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.6.1 | Read `record_show` method (lines 316-362) | Test show recording |
| J8.6.2 | Verify `showed_up` field | Check boolean |
| J8.6.3 | Verify `showed_up_confirmed_by` field | Check source |
| J8.6.4 | Verify `no_show_reason` field | Check reason |
| J8.6.5 | Read `get_show_rate_analysis` method | Check analytics |

**Pass Criteria:**
- [ ] Show/no-show recorded
- [ ] Confirmation method tracked
- [ ] Show rate analytics available

<!-- E2E_SESSION_BREAK: J8.6 complete. Next: J8.7 DealService Implementation -->

---

### J8.7 — DealService Implementation
**Purpose:** Verify DealService is complete.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.7.1 | Read `src/services/deal_service.py` (867 lines) | N/A |
| J8.7.2 | Verify `create` method | Test deal creation |
| J8.7.3 | Verify `update_stage` method | Test stage changes |
| J8.7.4 | Verify `close_won` method | Test winning deal |
| J8.7.5 | Verify `close_lost` method | Test losing deal |
| J8.7.6 | Verify `update_value` method | Test value updates |

**Deal Stages (VERIFIED from deal_service.py lines 27-35):**
- qualification (20% probability)
- proposal (40%)
- negotiation (60%)
- verbal_commit (80%)
- contract_sent (90%)
- closed_won (100%)
- closed_lost (0%)

**Lost Reasons (VERIFIED from deal_service.py lines 38-49):**
- price_too_high
- chose_competitor
- no_budget
- timing_not_right
- no_decision
- champion_left
- project_cancelled
- went_silent
- bad_fit
- other

**Pass Criteria:**
- [ ] All CRUD methods implemented
- [ ] Stage validation works
- [ ] Probability auto-assigned per stage
- [ ] Lost reason validation works

<!-- E2E_SESSION_BREAK: J8.7 complete. Next: J8.8 Deal Pipeline -->

---

### J8.8 — Deal Pipeline
**Purpose:** Verify deal pipeline tracking.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.8.1 | Read `get_pipeline` method (lines 529-584) | Test pipeline query |
| J8.8.2 | Verify stage counts returned | Check counts |
| J8.8.3 | Verify stage values returned | Check totals |
| J8.8.4 | Verify weighted_value calculated | Check math |
| J8.8.5 | Read `get_stage_history` method | Check audit trail |

**Pipeline Summary (VERIFIED):**
- Per stage: count, total_value, avg_probability
- Total: total_count, total_value, weighted_value

**Pass Criteria:**
- [ ] Pipeline summary accurate
- [ ] Stage history tracked
- [ ] Weighted value correct

<!-- E2E_SESSION_BREAK: J8.8 complete. Next: J8.9 Deal Auto-Creation from Meeting -->

---

### J8.9 — Deal Auto-Creation from Meeting
**Purpose:** Verify deals auto-created from positive meeting outcomes.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.9.1 | Read `record_outcome` method (lines 364-460) | N/A |
| J8.9.2 | Verify `create_deal=True` parameter | Test auto-creation |
| J8.9.3 | Verify deal linked to meeting | Check deal.meeting_id |
| J8.9.4 | Verify meeting.deal_id updated | Check meeting record |
| J8.9.5 | Verify attribution carried forward | Check deal fields |

**Auto-Creation Logic (VERIFIED):**
```python
# src/services/meeting_service.py lines 432-458
if create_deal and outcome == "good":
    deal = await deal_service.create(
        client_id=meeting["client_id"],
        lead_id=meeting["lead_id"],
        name=deal_name or f"Deal from meeting {meeting_id}",
        value=deal_value,
        meeting_id=meeting_id,
        converting_activity_id=meeting.get("converting_activity_id"),
        converting_channel=meeting.get("converting_channel"),
    )
```

**Pass Criteria:**
- [ ] Deal created on good outcome
- [ ] Meeting and deal linked
- [ ] Attribution preserved

<!-- E2E_SESSION_BREAK: J8.9 complete. Next: J8.10 Revenue Attribution -->

---

### J8.10 — Revenue Attribution
**Purpose:** Verify revenue attributed to channels and activities.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.10.1 | Read `calculate_attribution` method (lines 610-630) | N/A |
| J8.10.2 | Verify first_touch model | Test attribution |
| J8.10.3 | Read `get_channel_attribution` method | Test channel breakdown |
| J8.10.4 | Read `get_funnel_analytics` method | Test funnel |

**Attribution Models (VERIFIED):**
- first_touch — 100% credit to first channel
- last_touch — 100% credit to converting channel
- linear — Equal split across all touches
- time_decay — More credit to recent touches

**Pass Criteria:**
- [ ] Attribution calculated on close_won
- [ ] Multiple models supported
- [ ] Channel breakdown available
- [ ] Funnel analytics work

<!-- E2E_SESSION_BREAK: J8.10 complete. Next: J8.11 CRM Push Service -->

---

### J8.11 — CRM Push Service
**Purpose:** Verify meetings pushed to client CRM.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.11.1 | Read `src/services/crm_push_service.py` | N/A |
| J8.11.2 | Verify HubSpot push (OAuth) | Test push |
| J8.11.3 | Verify Pipedrive push (API key) | Test push |
| J8.11.4 | Verify Close push (API key) | Test push |
| J8.11.5 | Verify non-blocking (failure doesn't stop meeting) | Test error handling |

**Supported CRMs (VERIFIED):**
- HubSpot (OAuth authentication)
- Pipedrive (API key authentication)
- Close (API key authentication)

**CRM Push Result (VERIFIED):**
```python
class CRMPushResult(BaseModel):
    success: bool = False
    skipped: bool = False
    reason: Optional[str] = None
    crm_contact_id: Optional[str] = None
    crm_deal_id: Optional[str] = None
    crm_org_id: Optional[str] = None
    error: Optional[str] = None
```

**Pass Criteria:**
- [ ] CRM push triggered on meeting creation
- [ ] Contact created/found in CRM
- [ ] Deal created in CRM
- [ ] Push failure doesn't break meeting creation

<!-- E2E_SESSION_BREAK: J8.11 complete. Next: J8.12 External CRM Sync -->

---

### J8.12 — External CRM Sync
**Purpose:** Verify deals can sync from external CRM.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.12.1 | Read `sync_from_external` method (lines 727-847) | N/A |
| J8.12.2 | Verify stage mapping from HubSpot | Check mapping |
| J8.12.3 | Verify stage mapping from Salesforce | Check mapping |
| J8.12.4 | Verify stage mapping from Pipedrive | Check mapping |
| J8.12.5 | Verify upsert logic (create or update) | Test both |

**External Stage Mapping (VERIFIED from deal_service.py lines 752-777):**
- HubSpot: appointmentscheduled → qualification, closedwon → closed_won
- Salesforce: prospecting → qualification, closed won → closed_won
- Pipedrive: lead in → qualification, negotiations started → negotiation

**Pass Criteria:**
- [ ] External stages map correctly
- [ ] Existing deals updated
- [ ] New deals created
- [ ] Lead matched by email

<!-- E2E_SESSION_BREAK: J8.12 complete. Next: J8.13 Lost Deal Analysis -->

---

### J8.13 — Lost Deal Analysis
**Purpose:** Verify lost deal analytics for CIS learning.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.13.1 | Read `get_lost_analysis` method (lines 700-725) | Test query |
| J8.13.2 | Verify lost_reason breakdown | Check grouping |
| J8.13.3 | Verify lost_notes captured | Check field |

**Pass Criteria:**
- [ ] Lost reasons analyzed
- [ ] Patterns identifiable
- [ ] CIS can learn from losses

<!-- E2E_SESSION_BREAK: J8.13 complete. Next: J8.14 End-to-End Meeting-to-Deal Test -->

---

### J8.14 — End-to-End Meeting-to-Deal Test
**Purpose:** Verify full meeting-to-deal flow works.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J8.14.1 | N/A | Send Calendly webhook for new booking |
| J8.14.2 | N/A | Verify meeting created |
| J8.14.3 | N/A | Verify lead status updated to meeting_booked |
| J8.14.4 | N/A | Record meeting outcome as "good" |
| J8.14.5 | N/A | Verify deal auto-created |
| J8.14.6 | N/A | Progress deal through stages |
| J8.14.7 | N/A | Close deal as won |
| J8.14.8 | N/A | Verify revenue attribution calculated |
| J8.14.9 | N/A | Verify CRM push (if configured) |

**Pass Criteria:**
- [ ] Full flow completes without errors
- [ ] Meeting created correctly
- [ ] Deal created from meeting
- [ ] Attribution calculated
- [ ] Lead marked as converted

<!-- E2E_SESSION_BREAK: J8 JOURNEY COMPLETE. Next: J9 Dashboard -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Meeting Service | `src/services/meeting_service.py` | 839 | ✅ VERIFIED |
| Deal Service | `src/services/deal_service.py` | 867 | ✅ VERIFIED |
| CRM Push Service | `src/services/crm_push_service.py` | 500+ | ✅ VERIFIED |
| Webhook Routes | `src/api/routes/webhooks.py` | 1600+ | ✅ Calendly OK, ⚠️ Cal.com stubbed |
| Closer Engine | `src/engines/closer.py` | 647 | Meeting tasks created |

---

## Completion Criteria

All checks must pass:

- [ ] **J8.1** Calendly webhook creates meetings
- [ ] **J8.2** ⚠️ Cal.com NOT implemented (CEO decision required)
- [ ] **J8.3** MeetingService fully implemented
- [ ] **J8.4** Meeting analytics fields captured
- [ ] **J8.5** Meeting reminders work
- [ ] **J8.6** Show rate tracking works
- [ ] **J8.7** DealService fully implemented
- [ ] **J8.8** Deal pipeline tracking works
- [ ] **J8.9** Deal auto-created from meeting
- [ ] **J8.10** Revenue attribution works
- [ ] **J8.11** CRM push works (HubSpot, Pipedrive, Close)
- [ ] **J8.12** External CRM sync works
- [ ] **J8.13** Lost deal analysis works
- [ ] **J8.14** **End-to-end flow passes**

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ MeetingService is comprehensive (839 lines)
2. ✅ DealService is comprehensive (867 lines)
3. ✅ CRM push supports 3 CRMs (HubSpot, Pipedrive, Close)
4. ✅ Calendly webhook handler implemented
5. ⚠️ **Cal.com handler NOT implemented** — returns "ignored"
6. ✅ Revenue attribution with 4 models
7. ✅ Lost deal analysis for CIS learning
8. ✅ External CRM sync with stage mapping

**Issues Found:**
1. ⚠️ Cal.com webhook returns `{"status": "ignored", "reason": "calcom_not_fully_implemented"}`

**CEO Decision Required:**
- Implement Cal.com webhook handler OR
- Use Calendly as the only supported calendar

---

## Notes

**Calendly vs Cal.com:**
The Calendly handler is fully implemented. Cal.com handler exists but returns "ignored". If clients use Cal.com, this needs implementation.

**CRM Push Non-Blocking:**
CRM push failures are logged but don't prevent meeting creation. This is intentional to ensure meeting booking always succeeds even if CRM is down.

**Revenue Attribution:**
Attribution is calculated on `close_won`. The model (first_touch, last_touch, linear, time_decay) can be selected per calculation. This enables CIS to understand which channels drive revenue.
