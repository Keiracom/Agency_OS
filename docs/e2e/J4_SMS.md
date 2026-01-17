# J4: SMS Outreach Journey

**Status:** 🟢 Ready for Testing
**Priority:** P1 — High-touch channel for warm leads
**Depends On:** J2 Complete + TEST_MODE Verified
**Last Updated:** January 11, 2026
**Sub-Tasks:** 12 groups, 46 individual checks

---

## Overview

Tests the complete SMS outreach flow via Twilio integration with DNCR compliance.

**✅ RESOLVED (January 11, 2026):**
DNCR integration has been implemented:
- `src/integrations/dncr.py` created (320 lines) - full ACMA DNCR API client
- `src/integrations/twilio.py` updated to use DNCRClient
- Settings added: `dncr_api_key`, `dncr_api_url`, `dncr_account_id`, `dncr_cache_ttl_hours`
- Redis caching for DNCR results (default 24 hours)
- Graceful fallback if DNCR API unavailable

**User Journey:**
```
ALS >= 85 → Lead Ready → JIT Validation → DNCR Check → Content Generation → Send via Twilio → Activity Logged → Delivery Status Tracked
```

---

## Test Recipients (TEST_MODE)

| Field | Value |
|-------|-------|
| Test Phone | +61457543392 |
| TEST_MODE Setting | `settings.TEST_MODE` |
| Redirect Variable | `settings.TEST_SMS_RECIPIENT` |
| Format | E.164 international format |

---

## Sub-Tasks

### J4.1 — TEST_MODE Verification
**Purpose:** Ensure TEST_MODE redirects all SMS to test recipient.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.1.1 | Read `src/config/settings.py` — verify `TEST_SMS_RECIPIENT` | Check Railway env var |
| J4.1.2 | Read `src/engines/sms.py` lines 137-141 — verify redirect logic | N/A |
| J4.1.3 | Verify redirect happens BEFORE send (not after) | Trigger send, check logs |
| J4.1.4 | Verify original phone preserved in logs/activity | Check activity record |

**Code Verified:**
```python
# src/engines/sms.py lines 137-141
if settings.TEST_MODE:
    lead.phone = settings.TEST_SMS_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting SMS {original_phone} → {lead.phone}")
```

**Pass Criteria:**
- [ ] TEST_MODE setting exists
- [ ] TEST_SMS_RECIPIENT configured
- [ ] Redirect happens before send
- [ ] Original phone logged for reference

<!-- E2E_SESSION_BREAK: J4.1 complete. Next: J4.2 Twilio Integration -->

---

### J4.2 — Twilio Integration
**Purpose:** Verify Twilio client is properly configured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.2.1 | Read `src/integrations/twilio.py` — verify complete implementation | N/A |
| J4.2.2 | Verify `TWILIO_ACCOUNT_SID` env var in Railway | Check Railway vars |
| J4.2.3 | Verify `TWILIO_AUTH_TOKEN` env var in Railway | Check Railway vars |
| J4.2.4 | Verify `TWILIO_PHONE_NUMBER` env var in Railway | Check Railway vars |
| J4.2.5 | Verify `send_sms` method complete | Call API with test data |
| J4.2.6 | Verify `parse_inbound_webhook` for replies | Test webhook parsing |

**Twilio Client Methods (VERIFIED):**
- `send_sms()` — Single SMS with DNCR check
- `check_dncr()` — Check DNCR (⚠️ MOCKED)
- `parse_inbound_webhook()` — Parse reply webhooks
- `parse_status_webhook()` — Parse delivery status
- `get_message()` — Get message by SID
- `lookup_phone()` — Phone number lookup

**Pass Criteria:**
- [ ] Twilio integration is complete (250 lines verified)
- [ ] All 3 Twilio credentials configured
- [ ] SMS sends successfully via Twilio
- [ ] Webhooks parse correctly

<!-- E2E_SESSION_BREAK: J4.2 complete. Next: J4.3 SMS Engine Implementation -->

---

### J4.3 — SMS Engine Implementation
**Purpose:** Verify SMS engine is fully implemented.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.3.1 | Read `src/engines/sms.py` — verify `send` method | N/A |
| J4.3.2 | Verify no TODO/FIXME/pass in sms.py | `grep -n "TODO\|FIXME\|pass" src/engines/sms.py` |
| J4.3.3 | Verify `send_batch` method for bulk sends | N/A |
| J4.3.4 | Verify `check_dncr` method exposed | N/A |
| J4.3.5 | Verify OutreachEngine base class extended | Check class definition |

**SMS Engine Features (VERIFIED from sms.py 479 lines):**
- Single send with DNCR check
- Batch send with categorized results
- Rate limiting (100/day/number)
- DNCR rejection logging
- Activity logging with content_snapshot
- TEST_MODE redirect
- A/B test tracking (Phase 24B)

**Pass Criteria:**
- [ ] No incomplete implementations
- [ ] All methods have implementations
- [ ] Validation for required fields
- [ ] Extends OutreachEngine correctly

<!-- E2E_SESSION_BREAK: J4.3 complete. Next: J4.4 DNCR Compliance (Australia) -->

---

### J4.4 — DNCR Compliance (Australia)
**Purpose:** Verify Australian Do Not Call Register compliance.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.4.1 | Read `twilio.py` `check_dncr` method | N/A |
| J4.4.2 | ⚠️ **CRITICAL:** Verify DNCR check NOT mocked in production | Check `return False` on line 118 |
| J4.4.3 | Verify `_is_australian_number` checks for +61 prefix | N/A |
| J4.4.4 | Verify DNCR check happens before send | Trace code path |
| J4.4.5 | Verify DNCRError raised when blocked | Check exception handling |
| J4.4.6 | Verify DNCR rejection logged as `rejected_dncr` action | Check activity |

**⚠️ CRITICAL ISSUE:**
```python
# src/integrations/twilio.py lines 105-118
async def check_dncr(self, phone_number: str) -> bool:
    # In production, integrate with actual DNCR API
    # For now, return False (not on list)
    return False  # <-- MOCKED!
```

**Pass Criteria:**
- [ ] **DNCR integration required for production** (FIX NEEDED)
- [ ] Australian numbers (+61) identified
- [ ] Blocked numbers rejected before send
- [ ] DNCR rejection logged properly

<!-- E2E_SESSION_BREAK: J4.4 complete. Next: J4.5 Rate Limiting (Rule 17) -->

---

### J4.5 — Rate Limiting (Rule 17)
**Purpose:** Verify 100/day/number limit is enforced.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.5.1 | Read `SMS_DAILY_LIMIT_PER_NUMBER` constant | Verify = 100 |
| J4.5.2 | Verify `rate_limiter.check_and_increment` call | Check sms.py |
| J4.5.3 | Verify Redis used for rate limiting | Check redis.py |
| J4.5.4 | Test hitting limit | Send 101 SMS, verify 101st blocked |

**Rate Limit Logic (VERIFIED):**
```python
# src/engines/sms.py lines 51-52 and 143-157
SMS_DAILY_LIMIT_PER_NUMBER = 100

allowed, current_count = await rate_limiter.check_and_increment(
    resource_type="sms",
    resource_id=from_number,
    limit=SMS_DAILY_LIMIT_PER_NUMBER,
)
```

**Pass Criteria:**
- [ ] Limit is 100/day/number
- [ ] Redis tracks counts
- [ ] 101st SMS blocked with ResourceRateLimitError
- [ ] Remaining quota returned in response

<!-- E2E_SESSION_BREAK: J4.5 complete. Next: J4.6 Phone Number Validation -->

---

### J4.6 — Phone Number Validation
**Purpose:** Verify phone numbers are validated before send.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.6.1 | Verify lead phone check before send (lines 131-135) | N/A |
| J4.6.2 | Verify E.164 format expected | Check Twilio docs |
| J4.6.3 | Verify `lookup_phone` method for validation | Test lookup |
| J4.6.4 | Test invalid phone number handling | Send to invalid number |

**Phone Validation (VERIFIED):**
```python
# src/engines/sms.py lines 131-135
if not lead.phone:
    return EngineResult.fail(
        error="Lead has no phone number",
        metadata={"lead_id": str(lead_id)},
    )
```

**Pass Criteria:**
- [ ] Missing phone rejected
- [ ] E.164 format expected
- [ ] Invalid numbers handled gracefully

<!-- E2E_SESSION_BREAK: J4.6 complete. Next: J4.7 Content Generation -->

---

### J4.7 — Content Generation
**Purpose:** Verify AI generates SMS content with length limits.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.7.1 | Read `content.py` — verify `generate_sms` method | N/A |
| J4.7.2 | Verify 160 character limit (GSM-7) | Check prompt constraints |
| J4.7.3 | Verify personalization uses lead data | Check first_name, company |
| J4.7.4 | Verify AI spend tracked | Check cost_aud in metadata |

**Character Limits:**
- GSM-7: 160 characters
- Unicode: 70 characters
- Multi-part: 153/67 chars per segment

**Pass Criteria:**
- [ ] SMS content generated
- [ ] Character limit respected
- [ ] Personalization variables replaced
- [ ] AI cost tracked

<!-- E2E_SESSION_BREAK: J4.7 complete. Next: J4.8 JIT Validation (Pre-Send) -->

---

### J4.8 — JIT Validation (Pre-Send)
**Purpose:** Verify JIT validation runs before every send.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.8.1 | Read `outreach_flow.py` — verify SMS uses JIT validation | Check send_sms_outreach_task |
| J4.8.2 | Verify ALS >= 85 required for SMS | Check allocator rules |
| J4.8.3 | Verify client/campaign/lead status validated | Test with invalid states |

**Pass Criteria:**
- [ ] JIT validation runs before SMS send
- [ ] SMS only for hot leads (ALS >= 85)
- [ ] Invalid states blocked

<!-- E2E_SESSION_BREAK: J4.8 complete. Next: J4.9 Activity Logging -->

---

### J4.9 — Activity Logging
**Purpose:** Verify all sends create activity records.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.9.1 | Read `_log_activity` method in sms.py | N/A |
| J4.9.2 | Verify all fields populated | Check activity schema |
| J4.9.3 | Verify content_snapshot stored (Phase 16) | Check snapshot structure |
| J4.9.4 | Verify template_id stored (Phase 24B) | Check field |
| J4.9.5 | Verify full_message_body stored | Check field |
| J4.9.6 | Verify links_included extracted | Check parsed links |

**Activity Fields (VERIFIED from sms.py):**
- provider_message_id, sequence_step, content_preview
- content_snapshot (Phase 16)
- template_id, ab_test_id, ab_variant (Phase 24B)
- full_message_body, links_included
- personalization_fields_used, ai_model_used, prompt_version
- provider="twilio"

**Pass Criteria:**
- [ ] Activity created on every send
- [ ] DNCR rejections logged as `rejected_dncr` action
- [ ] All Phase 16/24B fields populated

<!-- E2E_SESSION_BREAK: J4.9 complete. Next: J4.10 Delivery Status Tracking -->

---

### J4.10 — Delivery Status Tracking
**Purpose:** Verify SMS delivery status is tracked via webhooks.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.10.1 | Read `parse_status_webhook` method | N/A |
| J4.10.2 | Verify webhook endpoint `/webhooks/sms/twilio` | Check webhooks.py |
| J4.10.3 | Verify status callback URL configured in Twilio | Check Twilio console |
| J4.10.4 | Verify statuses tracked: delivered, failed, undelivered | Test delivery |

**Status Webhook Fields:**
- message_sid, message_status, to_number
- error_code, error_message

**Pass Criteria:**
- [ ] Delivery status webhook configured
- [ ] Status updates processed
- [ ] Failed deliveries logged

<!-- E2E_SESSION_BREAK: J4.10 complete. Next: J4.11 Error Handling -->

---

### J4.11 — Error Handling
**Purpose:** Verify graceful error handling.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.11.1 | Verify Twilio errors caught (TwilioRestException) | Check exception handling |
| J4.11.2 | Verify DNCR errors caught (DNCRError) | Check exception handling |
| J4.11.3 | Verify EngineResult.fail returned on error | Check return structure |
| J4.11.4 | Verify retry logic in outreach_flow | Check @task decorator |

**Retry Configuration:**
```python
@task(name="send_sms_outreach", retries=2, retry_delay_seconds=10)
```

**Pass Criteria:**
- [ ] Errors don't crash the flow
- [ ] DNCR rejections handled gracefully
- [ ] Failed sends logged with reason
- [ ] Retries attempted (2x)

<!-- E2E_SESSION_BREAK: J4.11 complete. Next: J4.12 Live SMS Delivery Test -->

---

### J4.12 — Live SMS Delivery Test
**Purpose:** Verify SMS arrives on test phone.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J4.12.1 | Verify sender ID configured | Check Twilio number |
| J4.12.2 | N/A | Send real SMS via TEST_MODE |
| J4.12.3 | N/A | Receive on test phone |
| J4.12.4 | N/A | Verify content, personalization |
| J4.12.5 | N/A | Verify sender ID displays correctly |

**Pass Criteria:**
- [ ] SMS received on test phone
- [ ] Content displays correctly
- [ ] Personalization fields replaced
- [ ] Sender ID correct

<!-- E2E_SESSION_BREAK: J4 JOURNEY COMPLETE. Next: J5 Voice Outreach -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| SMS Engine | `src/engines/sms.py` | 479 | ✅ VERIFIED |
| Twilio Integration | `src/integrations/twilio.py` | 250 | ⚠️ DNCR MOCKED |
| Outreach Flow | `src/orchestration/flows/outreach_flow.py` | 686 | ✅ VERIFIED |
| Content Engine | `src/engines/content.py` | 200+ | ✅ VERIFIED |
| Webhooks | `src/api/routes/webhooks.py` | 200+ | ✅ VERIFIED |
| Settings | `src/config/settings.py` | - | TEST_MODE config |
| Redis Rate Limiter | `src/integrations/redis.py` | - | Rate limiting |

---

## Completion Criteria

All checks must pass:

- [ ] **J4.1** TEST_MODE redirects all SMS
- [ ] **J4.2** Twilio integration complete and working
- [ ] **J4.3** SMS engine fully implemented
- [ ] **J4.4** DNCR compliance working **(REQUIRES FIX)**
- [ ] **J4.5** Rate limit 100/day/number enforced
- [ ] **J4.6** Phone validation works
- [ ] **J4.7** AI content generation works
- [ ] **J4.8** JIT validation runs before send
- [ ] **J4.9** Activities logged with all fields
- [ ] **J4.10** Delivery status tracked
- [ ] **J4.11** Errors handled gracefully
- [ ] **J4.12** Test SMS received on phone

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ SMS engine is comprehensive (479 lines)
2. ✅ Twilio integration complete (250 lines)
3. ✅ Rate limiting properly configured (100/day/number)
4. ✅ TEST_MODE redirect works
5. ⚠️ **DNCR check is MOCKED — MUST INTEGRATE for production**
6. ✅ Activity logging with Phase 16/24B fields
7. ✅ JIT validation via outreach_flow

**Pre-requisite Fix Before Production:**
The DNCR check (`src/integrations/twilio.py` line 118) currently returns `False` always. This MUST be integrated with the actual Australian DNCR API before sending SMS to production leads.

---

## Notes

**DNCR Compliance:**
Australian businesses MUST check the Do Not Call Register before making telemarketing calls or sending SMS. Penalties for non-compliance can be significant. Current mock implementation is NOT production-ready.

**DNCR API Integration:**
- URL: https://api.dncr.gov.au
- Requires registration with ACMA
- Must integrate before production SMS
