# J3: Email Outreach Journey

**Status:** 🟢 Ready for Testing
**Priority:** P1 — Primary outreach channel
**Depends On:** J2 Complete + TEST_MODE Verified
**Last Updated:** January 11, 2026
**Sub-Tasks:** 12 groups, 48 individual checks

---

## Overview

Tests the complete email outreach flow via Salesforge integration with TEST_MODE protection.

**Key Finding from Code Review:**
- **Primary sender is SALESFORGE** (Warmforge mailbox compatibility)
- `src/integrations/salesforge.py` (402 lines) - full implementation
- Rate limit: 50 emails/day/domain (Rule 17)
- Threading: In-Reply-To + References headers (Rule 18)

**✅ RESOLVED (January 11, 2026):**
Salesforge integration has been implemented:
- `src/integrations/salesforge.py` created with full API client
- `src/engines/email.py` updated to use SalesforgeClient
- Webhooks updated to use Salesforge event service
- Preserves Warmforge mailbox warmup progress

**User Journey:**
```
Campaign Active → Lead Ready → JIT Validation → Content Generation → Send via Salesforge → Activity Logged → Events Tracked
```

---

## Test Recipients (TEST_MODE)

| Field | Value |
|-------|-------|
| Test Email | david.stephens@keiracom.com |
| TEST_MODE Setting | `settings.TEST_MODE` |
| Redirect Variable | `settings.TEST_EMAIL_RECIPIENT` |

---

## Sub-Tasks

### J3.1 — TEST_MODE Verification
**Purpose:** Ensure TEST_MODE redirects all emails to test recipient.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.1.1 | Read `src/config/settings.py` — verify `TEST_MODE` and `TEST_EMAIL_RECIPIENT` | Check Railway env var |
| J3.1.2 | Read `src/engines/email.py` lines 143-147 — verify redirect logic | N/A |
| J3.1.3 | Verify redirect happens BEFORE send (not after) | Trigger send, check logs |
| J3.1.4 | Verify original email preserved in logs/activity | Check activity record |

**Code Verified:**
```python
# src/engines/email.py lines 143-147
if settings.TEST_MODE:
    lead.email = settings.TEST_EMAIL_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting email {original_email} → {lead.email}")
```

**Pass Criteria:**
- [ ] TEST_MODE setting exists and is `true` in Railway
- [ ] TEST_EMAIL_RECIPIENT configured
- [ ] Redirect happens before send
- [ ] Original email logged for reference

<!-- E2E_SESSION_BREAK: J3.1 complete. Next: J3.2 Resend Integration -->

---

### J3.2 — Resend Integration
**Purpose:** Verify Resend is the primary email sender.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.2.1 | Read `src/integrations/resend.py` — verify complete implementation | N/A |
| J3.2.2 | Verify `RESEND_API_KEY` env var in Railway | Check Railway vars |
| J3.2.3 | Verify API key format validation | N/A |
| J3.2.4 | Verify `send_email` method complete | Call API with test data |
| J3.2.5 | Verify batch sending support | Test `send_batch` method |
| J3.2.6 | Verify tags sent (campaign_id, lead_id, client_id) | Check Resend dashboard |

**Resend Client Methods (VERIFIED):**
- `send_email()` — Single email with threading
- `send_batch()` — Batch emails
- `get_email()` — Get email details by ID

**Pass Criteria:**
- [ ] Resend integration is complete (218 lines verified)
- [ ] API key configured in Railway
- [ ] Emails send successfully via Resend
- [ ] Tags attached for tracking

<!-- E2E_SESSION_BREAK: J3.2 complete. Next: J3.3 Salesforge Integration (Webhooks Only) -->

---

### J3.3 — Salesforge Integration (Webhooks Only)
**Purpose:** Verify Salesforge is for inbound events only.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.3.1 | Confirm NO `src/integrations/salesforge.py` file | File should not exist |
| J3.3.2 | Read `src/services/email_events_service.py` — verify `parse_salesforge_webhook` | N/A |
| J3.3.3 | Read `src/api/routes/webhooks.py` — verify Salesforge webhook endpoint | Test webhook |
| J3.3.4 | Verify Salesforge events: opens, clicks, bounces | Simulate webhook payload |

**⚠️ IMPORTANT:**
Salesforge is NOT used for sending emails. It's only for receiving engagement webhooks. Primary sender is **Resend**.

**Pass Criteria:**
- [ ] No salesforge.py integration file exists
- [ ] Salesforge webhooks parse correctly
- [ ] Events recorded in email_events table

<!-- E2E_SESSION_BREAK: J3.3 complete. Next: J3.4 Email Engine Implementation -->

---

### J3.4 — Email Engine Implementation
**Purpose:** Verify email engine is fully implemented.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.4.1 | Read `src/engines/email.py` — verify `send` method | N/A |
| J3.4.2 | Verify no TODO/FIXME/pass in email.py | `grep -n "TODO\|FIXME\|pass" src/engines/email.py` |
| J3.4.3 | Verify `send_batch` method for bulk sends | N/A |
| J3.4.4 | Verify subject and from_email validation | Test with missing fields |
| J3.4.5 | Verify OutreachEngine base class extended | Check class definition |

**Email Engine Features (VERIFIED from email.py 540 lines):**
- Single send with threading
- Batch send
- Rate limiting (50/day/domain)
- Activity logging with content_snapshot
- TEST_MODE redirect
- A/B test tracking (Phase 24B)

**Pass Criteria:**
- [ ] No incomplete implementations
- [ ] All methods have implementations
- [ ] Validation for required fields
- [ ] Extends OutreachEngine correctly

<!-- E2E_SESSION_BREAK: J3.4 complete. Next: J3.5 Email Threading (Rule 18) -->

---

### J3.5 — Email Threading (Rule 18)
**Purpose:** Verify email threading works for follow-ups.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.5.1 | Read `_get_thread_info` method in email.py | N/A |
| J3.5.2 | Verify In-Reply-To header set for follow-ups | Check sent email headers |
| J3.5.3 | Verify References header includes all thread messages | Check headers |
| J3.5.4 | Verify thread_id stored in activity | Check activity record |
| J3.5.5 | Verify `is_followup` flag triggers threading | Send follow-up email |

**Threading Implementation (VERIFIED):**
```python
# src/engines/email.py lines 173-182
if kwargs.get("is_followup"):
    thread_info = await self._get_thread_info(db, lead_id, campaign_id)
    in_reply_to = thread_info.get("in_reply_to")
    references = thread_info.get("references", [])
    thread_id = thread_info.get("thread_id")
```

**Pass Criteria:**
- [ ] In-Reply-To header set on follow-ups
- [ ] References header contains thread history
- [ ] Emails appear threaded in inbox
- [ ] Thread ID tracked in database

<!-- E2E_SESSION_BREAK: J3.5 complete. Next: J3.6 Rate Limiting (Rule 17) -->

---

### J3.6 — Rate Limiting (Rule 17)
**Purpose:** Verify 50/day/domain limit is enforced.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.6.1 | Read `EMAIL_DAILY_LIMIT_PER_DOMAIN` constant | Verify = 50 |
| J3.6.2 | Verify `rate_limiter.check_and_increment` call | Check email.py |
| J3.6.3 | Verify domain extraction from from_email | Test various formats |
| J3.6.4 | Verify Redis used for rate limiting | Check redis.py |
| J3.6.5 | Test hitting limit | Send 51 emails, verify 51st blocked |

**Rate Limit Logic (VERIFIED):**
```python
# src/engines/email.py lines 53 and 158-171
EMAIL_DAILY_LIMIT_PER_DOMAIN = 50

allowed, current_count = await rate_limiter.check_and_increment(
    resource_type="email",
    resource_id=domain,
    limit=EMAIL_DAILY_LIMIT_PER_DOMAIN,
)
```

**Pass Criteria:**
- [ ] Limit is 50/day/domain
- [ ] Redis tracks counts
- [ ] 51st email blocked with ResourceRateLimitError
- [ ] Remaining quota returned in response

<!-- E2E_SESSION_BREAK: J3.6 complete. Next: J3.7 JIT Validation (Pre-Send) -->

---

### J3.7 — JIT Validation (Pre-Send)
**Purpose:** Verify JIT validation runs before every send.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.7.1 | Read `outreach_flow.py` — verify `jit_validate_outreach_task` | N/A |
| J3.7.2 | Verify client subscription status checked | Test with churned client |
| J3.7.3 | Verify campaign status checked | Test with paused campaign |
| J3.7.4 | Verify lead status checked (not unsubscribed/bounced) | Test with bounced lead |
| J3.7.5 | Verify credits remaining checked | Test with 0 credits |
| J3.7.6 | Verify permission mode checked (manual = blocked) | Test manual mode |

**JIT Validations (from outreach_flow.py):**
1. Client subscription_status in [ACTIVE, TRIALING]
2. Client credits_remaining > 0
3. Campaign status = ACTIVE
4. Lead status NOT in [UNSUBSCRIBED, BOUNCED, CONVERTED]
5. Permission mode != MANUAL

**Pass Criteria:**
- [ ] All 5 validations run before send
- [ ] Blocked sends logged with reason
- [ ] No emails sent to invalid targets

<!-- E2E_SESSION_BREAK: J3.7 complete. Next: J3.8 Content Generation -->

---

### J3.8 — Content Generation
**Purpose:** Verify AI generates email content.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.8.1 | Read `content.py` — verify `generate_email` method | N/A |
| J3.8.2 | Verify subject generated (< 50 chars) | Generate and measure |
| J3.8.3 | Verify body generated (< 150 words) | Generate and count |
| J3.8.4 | Verify personalization uses lead data | Check first_name, company in output |
| J3.8.5 | Verify AI spend tracked | Check cost_aud in metadata |
| J3.8.6 | Verify JSON response parsing (subject + body) | Check parsing logic |

**Pass Criteria:**
- [ ] Subject and body both generated
- [ ] Personalization variables replaced
- [ ] AI cost tracked
- [ ] JSON parsing handles markdown code blocks

<!-- E2E_SESSION_BREAK: J3.8 complete. Next: J3.9 Activity Logging -->

---

### J3.9 — Activity Logging
**Purpose:** Verify all sends create activity records.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.9.1 | Read `_log_activity` method in email.py | N/A |
| J3.9.2 | Verify all fields populated | Check activity schema |
| J3.9.3 | Verify content_snapshot stored (Phase 16) | Check snapshot structure |
| J3.9.4 | Verify template_id stored (Phase 24B) | Check field |
| J3.9.5 | Verify full_message_body stored | Check field |
| J3.9.6 | Verify links_included extracted | Check parsed links |

**Activity Fields (VERIFIED from email.py):**
- provider_message_id, thread_id, in_reply_to
- sequence_step, subject, content_preview
- content_snapshot (Phase 16)
- template_id, ab_test_id, ab_variant (Phase 24B)
- full_message_body, links_included
- personalization_fields_used, ai_model_used, prompt_version

**Pass Criteria:**
- [ ] Activity created on every send
- [ ] All Phase 16/24B fields populated
- [ ] Content snapshot captures for CIS learning

<!-- E2E_SESSION_BREAK: J3.9 complete. Next: J3.10 Email Events Tracking -->

---

### J3.10 — Email Events Tracking
**Purpose:** Verify opens/clicks/bounces are tracked.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.10.1 | Read `src/services/email_events_service.py` | N/A |
| J3.10.2 | Verify webhook endpoint `/webhooks/email/resend` | Check webhooks.py |
| J3.10.3 | Verify `record_event` method | Trace code path |
| J3.10.4 | Verify duplicate event handling (provider_event_id) | Test same event twice |
| J3.10.5 | Verify activity summary updated via trigger | Check database trigger |

**Event Types Tracked:**
- sent, delivered
- opened (first and repeat)
- clicked (with URL)
- bounced (hard/soft)
- complained, unsubscribed

**Pass Criteria:**
- [ ] Email events service complete
- [ ] Webhook endpoints receive events
- [ ] Duplicates handled gracefully
- [ ] Activity record updated with event counts

<!-- E2E_SESSION_BREAK: J3.10 complete. Next: J3.11 Error Handling -->

---

### J3.11 — Error Handling
**Purpose:** Verify graceful error handling.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.11.1 | Verify Resend errors caught and logged | Check exception handling |
| J3.11.2 | Verify Sentry capture on failures | Check sentry_sdk calls |
| J3.11.3 | Verify EngineResult.fail returned on error | Check return structure |
| J3.11.4 | Verify retry logic in outreach_flow | Check @task decorator |

**Retry Configuration:**
```python
@task(name="send_email_outreach", retries=2, retry_delay_seconds=10)
```

**Pass Criteria:**
- [ ] Errors don't crash the flow
- [ ] Sentry captures exceptions
- [ ] Failed sends logged with reason
- [ ] Retries attempted (2x)

<!-- E2E_SESSION_BREAK: J3.11 complete. Next: J3.12 Inbox Delivery Test -->

---

### J3.12 — Inbox Delivery Test
**Purpose:** Verify emails land in inbox (not spam).

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J3.12.1 | Verify sender domain has SPF/DKIM/DMARC | Check DNS records |
| J3.12.2 | Verify from_email is valid | Check sender setup |
| J3.12.3 | N/A | Send real email via TEST_MODE |
| J3.12.4 | N/A | Check inbox (not spam folder) |
| J3.12.5 | N/A | Verify content, personalization, formatting |
| J3.12.6 | N/A | Verify threading works in inbox view |

**Pass Criteria:**
- [ ] Email lands in inbox (not spam)
- [ ] Subject displays correctly
- [ ] Body renders properly (HTML)
- [ ] Personalization fields replaced
- [ ] Threading displays correctly

<!-- E2E_SESSION_BREAK: J3 JOURNEY COMPLETE. Next: J4 SMS Outreach -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| Email Engine | `src/engines/email.py` | 540 | ✅ VERIFIED |
| Resend Integration | `src/integrations/resend.py` | 218 | ✅ VERIFIED |
| Outreach Flow | `src/orchestration/flows/outreach_flow.py` | 686 | ✅ VERIFIED |
| Content Engine | `src/engines/content.py` | 200+ | ✅ VERIFIED |
| Email Events Service | `src/services/email_events_service.py` | 100+ | ✅ VERIFIED |
| Webhooks | `src/api/routes/webhooks.py` | 200+ | ✅ VERIFIED |
| Settings | `src/config/settings.py` | - | TEST_MODE config |
| Redis Rate Limiter | `src/integrations/redis.py` | - | Rate limiting |

---

## Completion Criteria

All checks must pass:

- [ ] **J3.1** TEST_MODE redirects all emails
- [ ] **J3.2** Resend integration complete and working
- [ ] **J3.3** Salesforge webhooks work (events only)
- [ ] **J3.4** Email engine fully implemented
- [ ] **J3.5** Threading works (In-Reply-To + References)
- [ ] **J3.6** Rate limit 50/day/domain enforced
- [ ] **J3.7** JIT validation runs before every send
- [ ] **J3.8** AI content generation works
- [ ] **J3.9** Activities logged with all fields
- [ ] **J3.10** Email events tracked
- [ ] **J3.11** Errors handled gracefully
- [ ] **J3.12** Test email lands in inbox

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ Primary sender is **Resend** (not Salesforge)
2. ✅ Salesforge is webhooks-only (no sending)
3. ✅ Rate limiting properly configured (50/day/domain)
4. ✅ Email threading implemented with In-Reply-To + References
5. ✅ TEST_MODE redirect works
6. ✅ Comprehensive activity logging with Phase 16/24B fields
7. ✅ JIT validation before every send (Rule 13)

**No Issues Found** - Email engine is well-implemented.

---

## Notes

**Why Resend over Salesforge:**
Salesforge is for cold email at scale. Resend is a transactional email service. The codebase uses Resend for all sending, which may need review based on use case (transactional vs cold outreach).

**Warmup Consideration:**
The 50/day/domain limit helps protect domain reputation during warmup. For higher volumes, additional warmup strategy may be needed.
