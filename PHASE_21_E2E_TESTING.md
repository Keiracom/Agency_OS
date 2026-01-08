# PHASE 21: End-to-End Testing Specification

**Status:** 🟡 Ready to Execute
**Estimate:** 16 hours
**Priority:** P0 - Critical Path
**Dependencies:** Phase 24H (LinkedIn), TEST Mode

---

## Overview

Phase 21 validates the complete Agency OS user journey with real infrastructure. This is "dogfooding" - using Agency OS to test Agency OS before selling it to real customers.

**Philosophy:** We're not testing "does page load" checkboxes. We're testing the actual user journey that a paying customer would experience.

---

## Test Configuration

### Test Agency Profile

| Field | Value |
|-------|-------|
| **Agency Name** | Umped |
| **Website** | https://umped.com.au/ |
| **ICP Target** | Australian marketing agencies |
| **Test User Email** | david.stephens@keiracom.com |
| **Test User Phone** | +61457543392 |
| **Test LinkedIn** | https://www.linkedin.com/in/david-stephens-8847a636a/ |

### Test Mode Configuration

All outbound communications redirect to test recipients when `TEST_MODE=true`:

```bash
# Environment Variables
TEST_MODE=true
TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
TEST_SMS_RECIPIENT=+61457543392
TEST_VOICE_RECIPIENT=+61457543392
TEST_LINKEDIN_RECIPIENT=https://www.linkedin.com/in/david-stephens-8847a636a/
TEST_DAILY_EMAIL_LIMIT=15  # Protect mailbox warmup
```

### Test Volumes

| Resource | Volume | Rationale |
|----------|--------|-----------|
| **Leads** | 100 | Enough for ALS distribution validation |
| **Emails sent** | 10-15 max | Protect mailbox warmup (14-day period) |
| **SMS sent** | 3-5 max | Cost control + validation |
| **LinkedIn messages** | 10-20 max | HeyReach free trial (~100/day limit) |
| **Voice calls** | 1-2 max | Validate Vapi works |

### Expected ALS Distribution (100 Leads)

| Tier | ALS Range | Expected Count | What Happens |
|------|-----------|----------------|--------------|
| **Hot** | 85-100 | ~10-15 leads | Deep research triggers, priority outreach |
| **Warm** | 60-84 | ~30-40 leads | Standard sequences |
| **Cool** | 0-59 | ~45-55 leads | Nurture, lower priority |

---

## Test Journeys

### Journey 1: Signup & Onboarding (30 min)

**Goal:** Validate new user can sign up and complete onboarding.

#### Onboarding Flow

```
STEP 1: Signup (email/password)
    └── Create account with david.stephens@keiracom.com
    └── Verify confirmation email received
    └── Complete email verification

STEP 2: Connect CRM (optional)
    └── HubSpot/Pipedrive OAuth OR Skip
    └── If connected: Profile pre-fills, customers imported

STEP 3: Confirm Sender Profile
    └── Name, title, company pre-filled (if CRM connected)
    └── LinkedIn URL: Manual entry required
    └── Verify data displays correctly

STEP 4: Import Customers (optional)
    └── Pull from CRM OR Upload CSV OR Skip
    └── Customers auto-added to suppression list

STEP 5: Website URL → ICP Extraction
    └── Enter: https://umped.com.au/
    └── Watch 5-tier scraper waterfall work
    └── Review extracted ICP data
    └── Confirm ICP

STEP 6: Connect LinkedIn (optional)
    └── Enter LinkedIn credentials
    └── Handle 2FA verification
    └── OR Skip for now

STEP 7: Webhook URL (optional)
    └── For meeting booking push
    └── Skip for testing

DASHBOARD
    └── Verify redirect to dashboard
    └── Verify client record in Supabase
```

#### Verification Checklist - Journey 1

| Check | Expected | Status |
|-------|----------|--------|
| Auth callback works | Redirect to onboarding | ⬜ |
| ICP extraction completes | Services, clients, pain points extracted | ⬜ |
| Scraper waterfall logs | Show which tier succeeded | ⬜ |
| Client record in `clients` table | All fields populated | ⬜ |
| ICP record in `client_icp_profiles` | Matches displayed data | ⬜ |
| Dashboard loads | No console errors | ⬜ |

---

### Journey 2: Campaign & Leads (45 min)

**Goal:** Validate lead sourcing, scoring, and campaign setup.

#### Flow

```
CREATE CAMPAIGN
    └── Name: "Test Campaign - Umped"
    └── Target: 100 leads
    └── Channels: Email, SMS, LinkedIn, Voice
    └── ICP: Auto-populated from onboarding

LEAD SOURCING
    └── Apollo enriches 100 leads matching ICP
    └── Leads added to lead_pool
    └── Leads assigned to client (lead_assignments)

ALS SCORING
    └── All 100 leads scored
    └── Distribution: Hot/Warm/Cool tiers
    └── Verify distribution matches expectations

DEEP RESEARCH (Hot Leads)
    └── Triggered automatically for ALS >= 85
    └── LinkedIn posts scraped
    └── Company news scraped
    └── Icebreakers generated

CONTENT GENERATION
    └── Email sequences generated
    └── SMS templates generated
    └── LinkedIn messages generated
    └── Voice scripts generated
```

#### Verification Checklist - Journey 2

| Check | Expected | Status |
|-------|----------|--------|
| `lead_pool` has 100 records | All Apollo fields populated | ⬜ |
| `lead_assignments` links leads to client | Status = 'assigned' | ⬜ |
| ALS scores calculated | Scores in 0-100 range | ⬜ |
| Hot leads count | ~10-15 with ALS >= 85 | ⬜ |
| Deep research triggered | `research_status` = 'complete' for Hot | ⬜ |
| Content Engine generates emails | Full message body stored | ⬜ |
| Dashboard shows campaign | Stats updating | ⬜ |

---

### Journey 3: Outreach Execution (60 min)

**Goal:** Validate all outreach channels work end-to-end.

**CRITICAL:** TEST_MODE must be ON. All messages redirect to test recipient.

#### Flow

```
CAMPAIGN ACTIVATION
    └── Start campaign
    └── JIT Validator runs pre-send checks
    └── Passes: Not suppressed, not blocked, rate limits OK

EMAIL OUTREACH
    └── Content Engine generates personalized email
    └── Email Engine sends via Salesforge
    └── Redirects to: david.stephens@keiracom.com
    └── Verify: Receive 10-15 personalized emails

SMS OUTREACH
    └── Content Engine generates SMS
    └── SMS Engine sends via Twilio
    └── Redirects to: +61457543392
    └── Verify: Receive 3-5 SMS messages

LINKEDIN OUTREACH
    └── Content Engine generates connection request
    └── LinkedIn Engine sends via HeyReach
    └── Redirects to: test LinkedIn profile
    └── Verify: Receive connection requests

VOICE OUTREACH
    └── Content Engine generates voice script
    └── Voice Engine calls via Vapi
    └── Redirects to: +61457543392
    └── Verify: Receive 1-2 AI phone calls
```

#### Verification Checklist - Journey 3

| Check | Expected | Status |
|-------|----------|--------|
| JIT validation passes | No blocked/suppressed errors | ⬜ |
| Emails received | 10-15 personalized emails in inbox | ⬜ |
| Email personalization | Lead name, company, icebreakers | ⬜ |
| SMS received | 3-5 messages on phone | ⬜ |
| LinkedIn requests | Connection requests visible | ⬜ |
| Voice calls | 1-2 AI calls received | ⬜ |
| `activities` table | All sends logged with channel | ⬜ |
| Dashboard updates | Activity feed shows sends | ⬜ |

---

### Journey 4: Reply & Meeting Booking (30 min)

**Goal:** Validate reply handling, intent classification, and meeting flow.

#### Flow

```
REPLY TO EMAIL
    └── Send reply: "Yes, I'm interested in learning more"
    └── Reply webhook fires
    └── Intent classified: "interested"
    └── Thread created in conversation_threads

INTENT CLASSIFICATION
    └── Closer Engine analyzes reply
    └── Detects: Positive sentiment, no objections
    └── Lead status updated: "replied"

MEETING BOOKING
    └── Calendar link sent (or auto-scheduled)
    └── Book meeting via Calendly/Cal.com
    └── Meeting webhook fires
    └── Meeting recorded in meetings table

DEAL CREATION
    └── Meeting triggers deal creation
    └── Pipeline stage: "Meeting Scheduled"
    └── Dashboard updates with meeting count
```

#### Verification Checklist - Journey 4

| Check | Expected | Status |
|-------|----------|--------|
| Reply webhook received | Payload logged | ⬜ |
| Intent classification | "interested" detected | ⬜ |
| `conversation_threads` record | Thread created | ⬜ |
| `thread_messages` record | Reply with sentiment | ⬜ |
| Lead status updated | status = 'replied' | ⬜ |
| Meeting booked | `meetings` table record | ⬜ |
| Deal created | `deals` table record | ⬜ |
| Dashboard metrics | Meeting count increments | ⬜ |

---

### Journey 5: Dashboard Validation (15 min)

**Goal:** Validate dashboard shows accurate real-time data.

#### Metrics to Verify

| Metric | Expected Source | Display Location |
|--------|-----------------|------------------|
| Total Leads | `lead_assignments` count | Overview card |
| Hot Leads | ALS >= 85 count | Pipeline chart |
| Emails Sent | `activities` WHERE channel='email' | Activity chart |
| Open Rate | `email_events` opens / sends | Engagement metrics |
| Reply Rate | Replied leads / contacted leads | Engagement metrics |
| Meetings Booked | `meetings` count | Conversion funnel |
| Pipeline Value | `deals` SUM(value) | Revenue card |

#### Verification Checklist - Journey 5

| Check | Expected | Status |
|-------|----------|--------|
| Overview metrics match DB | Query validation | ⬜ |
| Activity feed real-time | New sends appear | ⬜ |
| Charts render correctly | No blank charts | ⬜ |
| Filter by date works | Counts change | ⬜ |
| Export works | CSV downloads | ⬜ |

---

### Journey 6: Admin Dashboard (15 min)

**Goal:** Validate admin panel shows platform-wide metrics.

#### Admin Views to Test

| View | What to Check |
|------|---------------|
| **Command Center** | Platform-wide stats, all clients summary |
| **Clients** | List of clients with usage metrics |
| **Lead Pool** | Pool stats, utilization, distributions |
| **Activity** | Platform-wide activity log |
| **Health** | Integration health checks |

#### Verification Checklist - Journey 6

| Check | Expected | Status |
|-------|----------|--------|
| Admin auth works | Only admin can access | ⬜ |
| Client list shows test client | Umped visible | ⬜ |
| Pool stats accurate | Match DB queries | ⬜ |
| Activity log shows all sends | All channels visible | ⬜ |
| Health checks pass | All integrations green | ⬜ |

---

## What We're NOT Testing (Removed Items)

Based on discussions, these are explicitly removed from test scope:

| Item | Why Removed |
|------|-------------|
| **Suppression test CSV** | Suppression list populated from CRM import or CSV upload. For testing, skip or add 1-2 dummy companies manually. |
| **Webhook test URL** | Webhook is for pushing meeting bookings to client's systems. For testing, verify webhook fires via logs - no actual endpoint needed. |
| **Voice script content** | Content Engine generates ALL outgoing communication. Vapi speaks whatever Content Engine writes. We just verify it works. |

---

## Integration Health Pre-Flight

Before running E2E tests, verify all integrations are healthy:

| Integration | Endpoint | Expected |
|-------------|----------|----------|
| Backend | `GET /api/v1/health` | 200 OK |
| Supabase | Query `clients` table | Returns data |
| Resend | `POST /emails/test` | Email delivered |
| Anthropic | `POST /completions` | Response received |
| Apollo | `POST /people/search` | Leads returned |
| Apify | `POST /scrape` | HTML returned |
| Twilio | `POST /messages` | SMS delivered |
| Vapi | `POST /call` | Call initiated |
| HeyReach | `GET /senders` | Senders listed |
| Salesforge | `GET /mailboxes` | Mailboxes listed |

---

## HeyReach Free Trial Setup

For LinkedIn testing, use HeyReach 14-day free trial:

1. **Start trial** at https://app.heyreach.io (no CC required)
2. **Free tier includes:** 3 LinkedIn accounts, all features
3. **Connect LinkedIn** via credential method in HeyReach dashboard
4. **Daily limits:** ~100-150 connections/day per account
5. **For testing:** Send 10-20 messages (well under limit)

---

## Test Mode Implementation

All engines check `TEST_MODE` before sending:

```python
# Email Engine
if settings.TEST_MODE:
    recipient = settings.TEST_EMAIL_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting to {recipient}")

# SMS Engine  
if settings.TEST_MODE:
    phone = settings.TEST_SMS_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting to {phone}")

# Voice Engine
if settings.TEST_MODE:
    phone = settings.TEST_VOICE_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting to {phone}")

# LinkedIn Engine
if settings.TEST_MODE:
    profile = settings.TEST_LINKEDIN_RECIPIENT
    logger.info(f"TEST_MODE: Redirecting to {profile}")
```

### Daily Send Limit Safeguard

Protect mailbox warmup with hard limit:

```python
# Before any email send
today_count = await get_today_email_count(client_id)
if today_count >= settings.TEST_DAILY_EMAIL_LIMIT:
    raise DailySendLimitExceeded(f"Limit: {settings.TEST_DAILY_EMAIL_LIMIT}")
```

---

## Success Criteria

Phase 21 is complete when ALL of the following are true:

### ✅ Functional Requirements

- [ ] Signup → Onboarding → Dashboard flow works
- [ ] ICP extraction successfully scrapes Umped website
- [ ] 100 leads sourced and scored with proper distribution
- [ ] Deep research triggers for Hot leads (ALS >= 85)
- [ ] Content Engine generates personalized content
- [ ] Email, SMS, Voice all deliver to test recipients
- [ ] LinkedIn messages send via HeyReach
- [ ] Reply handling classifies intent correctly
- [ ] Meeting booking creates deal record
- [ ] Dashboard displays accurate metrics
- [ ] Admin panel shows platform-wide data

### ✅ Data Integrity

- [ ] `clients` table has complete record
- [ ] `lead_pool` has 100 leads with all Apollo fields
- [ ] `lead_assignments` links leads to client
- [ ] `activities` logs all outreach
- [ ] `email_events` tracks opens/clicks
- [ ] `conversation_threads` stores conversations
- [ ] `meetings` records bookings
- [ ] `deals` tracks pipeline

### ✅ Performance

- [ ] ICP extraction < 60 seconds
- [ ] Lead scoring < 30 seconds for 100 leads
- [ ] Dashboard loads < 3 seconds
- [ ] No timeout errors

---

## Task Breakdown

| ID | Task | Est | Dependencies |
|----|------|-----|--------------|
| E2E-001 | Pre-flight integration health checks | 1h | — |
| E2E-002 | Journey 1: Signup & Onboarding | 2h | E2E-001 |
| E2E-003 | Journey 2: Campaign & Leads | 3h | E2E-002 |
| E2E-004 | Journey 3: Email Outreach | 2h | E2E-003 |
| E2E-005 | Journey 3: SMS Outreach | 1h | E2E-003 |
| E2E-006 | Journey 3: Voice Outreach | 1h | E2E-003 |
| E2E-007 | Journey 3: LinkedIn Outreach | 2h | E2E-003, HeyReach setup |
| E2E-008 | Journey 4: Reply & Meeting | 2h | E2E-004 |
| E2E-009 | Journey 5: Dashboard Validation | 1h | E2E-008 |
| E2E-010 | Journey 6: Admin Dashboard | 1h | E2E-009 |

**Total: 16 hours**

---

## Files Created/Modified

### Test Mode Tasks

- `src/config/settings.py` - Add TEST_MODE env vars
- `src/engines/email.py` - Add redirect logic
- `src/engines/sms.py` - Add redirect logic
- `src/engines/voice.py` - Add redirect logic
- `src/engines/linkedin.py` - Add redirect logic
- `src/services/send_limiter.py` - Daily limit safeguard

### Test Scripts

- `tests/e2e/test_journey_1_onboarding.py`
- `tests/e2e/test_journey_2_campaign.py`
- `tests/e2e/test_journey_3_outreach.py`
- `tests/e2e/test_journey_4_reply.py`
- `tests/e2e/test_journey_5_dashboard.py`
- `tests/e2e/test_journey_6_admin.py`

---

## Rollback Plan

If E2E testing reveals critical issues:

1. **Stop all outreach** - Disable campaigns immediately
2. **Document issue** - Log exact failure point and error
3. **Rollback database** - Use Supabase point-in-time recovery if needed
4. **Fix and re-test** - Isolated unit tests before full E2E retry

---

## Post-Testing Cleanup

After successful E2E testing:

1. **Reset test data** - Clear Umped test client and leads
2. **Disable TEST_MODE** - Set `TEST_MODE=false` for production
3. **Document learnings** - Note any issues and fixes
4. **Prepare for launch** - Create first real client onboarding checklist

---

## Quick Reference

### You Are The...

| Role | What It Means |
|------|---------------|
| **Client** | You sign up as Umped, go through onboarding |
| **Lead** | You receive all redirected outreach |
| **Responder** | You reply to test reply handling |
| **Tester** | You verify everything works |

### Key Principle

**"I am just the output."** - Everything else is automated. The Content Engine creates all messages. You just receive and verify them.

---

*Last Updated: January 7, 2026*
*Version: 1.0*
