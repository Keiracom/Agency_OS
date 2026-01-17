# J6: LinkedIn Outreach Journey

**Status:** 🟡 Sub-tasks Defined (Pending CEO Approval)
**Priority:** P1 — High-trust B2B channel
**Depends On:** J2 Complete + TEST_MODE Verified + LinkedIn Credentials
**Last Updated:** January 11, 2026
**Sub-Tasks:** 13 groups, 52 individual checks

---

## Overview

Tests the complete LinkedIn outreach flow via HeyReach integration.

**Key Finding from Code Review:**
- Rate limit: **17/day/seat** (Rule 17) — very conservative for account safety
- Connection message limit: 300 characters
- Supports both connection requests and direct messages
- TEST_MODE redirects to TEST_LINKEDIN_RECIPIENT

**User Journey:**
```
Lead with LinkedIn URL → JIT Validation → TEST_MODE Redirect → Rate Limit Check → HeyReach API → Connection/Message Sent → Activity Logged
```

---

## Test Recipients (TEST_MODE)

| Field | Value |
|-------|-------|
| Test LinkedIn | https://www.linkedin.com/in/david-stephens-8847a636a/ |
| TEST_MODE Setting | `settings.TEST_MODE` |
| Redirect Variable | `settings.TEST_LINKEDIN_RECIPIENT` |
| Note | All connection requests and messages go to this profile |

---

## Sub-Tasks

### J6.1 — TEST_MODE Verification
**Purpose:** Ensure TEST_MODE redirects all LinkedIn actions to test recipient.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.1.1 | Read `src/config/settings.py` — verify `TEST_LINKEDIN_RECIPIENT` | Check Railway env var |
| J6.1.2 | Read `src/engines/linkedin.py` lines 144-148 — verify redirect logic | N/A |
| J6.1.3 | Verify redirect happens BEFORE API call | Trigger action, check logs |
| J6.1.4 | Verify original LinkedIn URL preserved in logs | Check activity record |

**Code Verified:**
```python
# src/engines/linkedin.py lines 144-148
if settings.TEST_MODE:
    lead.linkedin_url = settings.TEST_LINKEDIN_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting LinkedIn {original_linkedin} → {lead.linkedin_url}")
```

**Pass Criteria:**
- [ ] TEST_MODE setting exists
- [ ] TEST_LINKEDIN_RECIPIENT configured
- [ ] Redirect happens before HeyReach API call

<!-- E2E_SESSION_BREAK: J6.1 complete. Next: J6.2 HeyReach Integration -->

---

### J6.2 — HeyReach Integration
**Purpose:** Verify HeyReach client is properly configured.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.2.1 | Read `src/integrations/heyreach.py` — verify complete implementation | N/A |
| J6.2.2 | Verify `HEYREACH_API_KEY` env var in Railway | Check Railway vars |
| J6.2.3 | Verify `send_connection_request` method | Test API call |
| J6.2.4 | Verify `send_message` method | Test API call |
| J6.2.5 | Verify `get_seats` method | Test API call |
| J6.2.6 | Verify `get_new_replies` method | Test API call |

**HeyReach Client Methods (VERIFIED):**
- `get_seats()` — List available seats
- `send_connection_request()` — Send connection with note (300 char limit)
- `send_message()` — Send direct message
- `get_conversations()` — Get conversations
- `get_new_replies()` — Get unread messages
- `get_profile()` — Lookup profile data
- `check_seat_limit()` — Check daily capacity
- `add_linkedin_account()` — Add account (Phase 24H)
- `verify_2fa()` — Complete 2FA verification
- `remove_sender()` — Remove account

**Pass Criteria:**
- [ ] HeyReach integration is complete (482 lines verified)
- [ ] API key configured
- [ ] All methods functional

<!-- E2E_SESSION_BREAK: J6.2 complete. Next: J6.3 LinkedIn Engine Implementation -->

---

### J6.3 — LinkedIn Engine Implementation
**Purpose:** Verify LinkedIn engine is fully implemented.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.3.1 | Read `src/engines/linkedin.py` — verify `send` method | N/A |
| J6.3.2 | Verify no TODO/FIXME/pass in linkedin.py | Run grep |
| J6.3.3 | Verify `send_connection_request` convenience method | N/A |
| J6.3.4 | Verify `send_message` convenience method | N/A |
| J6.3.5 | Verify `send_batch` method | N/A |
| J6.3.6 | Verify `get_seat_status` method | N/A |
| J6.3.7 | Verify OutreachEngine base class extended | Check class definition |

**LinkedIn Engine Features (VERIFIED from linkedin.py 573 lines):**
- Connection request sending
- Direct message sending
- Batch actions
- Seat status checking
- New replies retrieval
- Activity logging with content_snapshot
- TEST_MODE redirect
- A/B test tracking (Phase 24B)

**Pass Criteria:**
- [ ] No incomplete implementations
- [ ] All methods functional
- [ ] Extends OutreachEngine correctly

<!-- E2E_SESSION_BREAK: J6.3 complete. Next: J6.4 Rate Limiting (Rule 17) -->

---

### J6.4 — Rate Limiting (Rule 17)
**Purpose:** Verify 17/day/seat limit is enforced.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.4.1 | Read `LINKEDIN_DAILY_LIMIT_PER_SEAT` constant | Verify = 17 |
| J6.4.2 | Verify `rate_limiter.check_and_increment` call | Check linkedin.py |
| J6.4.3 | Verify limit keyed by `seat_id` | Check resource_id |
| J6.4.4 | Verify Redis used for tracking | Check redis.py |
| J6.4.5 | Test hitting limit | Send 18 actions, verify 18th blocked |

**Rate Limit Logic (VERIFIED):**
```python
# src/engines/linkedin.py lines 50-51
LINKEDIN_DAILY_LIMIT_PER_SEAT = 17
```

**Pass Criteria:**
- [ ] Limit is 17/day/seat
- [ ] Redis tracks counts per seat
- [ ] 18th action blocked

<!-- E2E_SESSION_BREAK: J6.4 complete. Next: J6.5 LinkedIn URL Validation -->

---

### J6.5 — LinkedIn URL Validation
**Purpose:** Verify LinkedIn URLs are validated before actions.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.5.1 | Verify lead linkedin_url check (lines 137-142) | N/A |
| J6.5.2 | Verify URL format expected | linkedin.com/in/* |
| J6.5.3 | Test missing LinkedIn URL | Verify error returned |

**Pass Criteria:**
- [ ] Missing LinkedIn URL rejected
- [ ] Invalid URLs handled gracefully

<!-- E2E_SESSION_BREAK: J6.5 complete. Next: J6.6 Connection Requests -->

---

### J6.6 — Connection Requests
**Purpose:** Verify connection request functionality.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.6.1 | Verify `action="connection"` flow | Check code path |
| J6.6.2 | Verify message limit (300 chars) enforced | Check HeyReach |
| J6.6.3 | Verify activity logged as `connection_sent` | Check action |
| J6.6.4 | Send test connection request | Verify sent via HeyReach |

**Pass Criteria:**
- [ ] Connection requests work
- [ ] 300 character limit respected
- [ ] Activity logged correctly

<!-- E2E_SESSION_BREAK: J6.6 complete. Next: J6.7 Direct Messages -->

---

### J6.7 — Direct Messages
**Purpose:** Verify direct message functionality.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.7.1 | Verify `action="message"` flow | Check code path |
| J6.7.2 | Verify activity logged as `message_sent` | Check action |
| J6.7.3 | Send test direct message | Verify sent via HeyReach |

**Pass Criteria:**
- [ ] Direct messages work
- [ ] Activity logged correctly

<!-- E2E_SESSION_BREAK: J6.7 complete. Next: J6.8 LinkedIn Account Management -->

---

### J6.8 — LinkedIn Account Management
**Purpose:** Verify LinkedIn account connection via HeyReach.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.8.1 | Read `add_linkedin_account` method | N/A |
| J6.8.2 | Read `verify_2fa` method | N/A |
| J6.8.3 | Read `remove_sender` method | N/A |
| J6.8.4 | Read `get_sender` method | N/A |

**Pass Criteria:**
- [ ] Account connection methods exist
- [ ] 2FA verification supported
- [ ] Account removal works

<!-- E2E_SESSION_BREAK: J6.8 complete. Next: J6.9 Activity Logging -->

---

### J6.9 — Activity Logging
**Purpose:** Verify all actions create activity records.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.9.1 | Read `_log_activity` method in linkedin.py | N/A |
| J6.9.2 | Verify all fields populated | Check activity schema |
| J6.9.3 | Verify content_snapshot stored (Phase 16) | Check snapshot |
| J6.9.4 | Verify template_id stored (Phase 24B) | Check field |
| J6.9.5 | Verify message_type tracked | connection vs message |

**Activity Fields (VERIFIED):**
- provider_message_id, sequence_step, content_preview
- content_snapshot (Phase 16)
- template_id, ab_test_id, ab_variant (Phase 24B)
- full_message_body, links_included
- provider="heyreach"

**Pass Criteria:**
- [ ] Activity created on every action
- [ ] Connection vs message distinguished
- [ ] All fields populated

<!-- E2E_SESSION_BREAK: J6.9 complete. Next: J6.10 Reply Detection -->

---

### J6.10 — Reply Detection
**Purpose:** Verify LinkedIn replies are detected.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.10.1 | Verify `get_new_replies` method in engine | N/A |
| J6.10.2 | Verify HeyReach API returns unread messages | Check implementation |
| J6.10.3 | Test reply detection | Check HeyReach dashboard |

**Pass Criteria:**
- [ ] New replies detected
- [ ] Reply data captured correctly

<!-- E2E_SESSION_BREAK: J6.10 complete. Next: J6.11 Seat Management -->

---

### J6.11 — Seat Management
**Purpose:** Verify seat status and quota tracking.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.11.1 | Verify `get_seat_status` method | N/A |
| J6.11.2 | Verify `check_seat_limit` in HeyReach | N/A |
| J6.11.3 | Verify remaining quota returned | Check response |

**Pass Criteria:**
- [ ] Seat status retrievable
- [ ] Remaining quota accurate

<!-- E2E_SESSION_BREAK: J6.11 complete. Next: J6.12 Error Handling -->

---

### J6.12 — Error Handling
**Purpose:** Verify graceful error handling.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.12.1 | Verify HeyReach errors caught | Check exception handling |
| J6.12.2 | Verify EngineResult.fail returned on error | Check return |
| J6.12.3 | Verify retry logic in HeyReach client (tenacity) | Check decorator |
| J6.12.4 | Verify missing seat_id handled | Test without seat_id |

**Retry Logic (VERIFIED):**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
```

**Pass Criteria:**
- [ ] Errors don't crash the flow
- [ ] Retries attempted (3x)
- [ ] Required fields validated

<!-- E2E_SESSION_BREAK: J6.12 complete. Next: J6.13 Live LinkedIn Test -->

---

### J6.13 — Live LinkedIn Test
**Purpose:** Verify real LinkedIn actions work.

| Check | Part A: Wiring Verification | Part B: Live Test |
|-------|----------------------------|-------------------|
| J6.13.1 | Verify test seat available | Check HeyReach dashboard |
| J6.13.2 | N/A | Send test connection request |
| J6.13.3 | N/A | Verify in HeyReach dashboard |
| J6.13.4 | N/A | Check activity logged |

**Pass Criteria:**
- [ ] LinkedIn action sent successfully
- [ ] Appears in HeyReach dashboard
- [ ] Activity logged in database

<!-- E2E_SESSION_BREAK: J6 JOURNEY COMPLETE. Next: J7 Reply Handling -->

---

## Key Files Reference

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| LinkedIn Engine | `src/engines/linkedin.py` | 573 | ✅ VERIFIED |
| HeyReach Integration | `src/integrations/heyreach.py` | 482 | ✅ VERIFIED |
| Outreach Flow | `src/orchestration/flows/outreach_flow.py` | 686 | ✅ VERIFIED |
| Settings | `src/config/settings.py` | - | TEST_MODE config |
| Redis Rate Limiter | `src/integrations/redis.py` | - | Rate limiting |

---

## Completion Criteria

All checks must pass:

- [ ] **J6.1** TEST_MODE redirects all actions
- [ ] **J6.2** HeyReach integration complete
- [ ] **J6.3** LinkedIn engine fully implemented
- [ ] **J6.4** Rate limit 17/day/seat enforced
- [ ] **J6.5** LinkedIn URL validation works
- [ ] **J6.6** Connection requests work
- [ ] **J6.7** Direct messages work
- [ ] **J6.8** Account management works
- [ ] **J6.9** Activities logged
- [ ] **J6.10** Replies detected
- [ ] **J6.11** Seat management works
- [ ] **J6.12** Errors handled gracefully
- [ ] **J6.13** Live LinkedIn test passes

---

## CTO Verification Notes

**Code Review Completed:** January 11, 2026

**Key Findings:**
1. ✅ LinkedIn engine is comprehensive (573 lines)
2. ✅ HeyReach integration complete (482 lines)
3. ✅ Rate limiting conservative (17/day/seat) for account safety
4. ✅ TEST_MODE redirect implemented
5. ✅ Activity logging with Phase 16/24B fields
6. ✅ Retry logic with exponential backoff (3 attempts)
7. ✅ Account management with 2FA support (Phase 24H)

**No Issues Found** - LinkedIn engine is well-implemented.

---

## Notes

**CRITICAL:** LinkedIn rate limiting is essential. LinkedIn will ban accounts that exceed limits. The rate limiter must be thoroughly tested before any production use.

**Rate Limit Rationale:**
The 17/day/seat limit is conservative to:
- Protect account from suspension
- Mimic human behavior patterns
- Stay well below LinkedIn's detection thresholds
