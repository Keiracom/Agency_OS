# 2026-02-03 Channel Infrastructure Deep Dive

**Session Context:** Dave asked me to audit E2E test readiness and align on distribution channels. This evolved into a comprehensive infrastructure review covering SMS, Voice AI, and LinkedIn data scraping.

---

## Part 1: E2E Test Readiness Audit

### Initial Blockers Found

| Component | Status | Issue |
|-----------|--------|-------|
| TEST_MODE | ❌ Not set | Env vars missing |
| Unipile (LinkedIn) | ❌ 401 auth | Needs payment |
| Vapi | ⚠️ Partial | Missing VAPI_PHONE_NUMBER_ID |
| Warmforge | ⚠️ Limited | Only 2 mailboxes warming (free tier limit) |

### Fixes Applied During Session

1. **TEST_MODE** — Added to `~/.config/agency-os/.env`:
   ```
   TEST_MODE=true
   TEST_EMAIL_RECIPIENT=david.stephens@keiracom.com
   TEST_SMS_RECIPIENT=+61457543392
   TEST_VOICE_RECIPIENT=+61457543392
   TEST_DAILY_EMAIL_LIMIT=15
   ```

2. **Vapi Phone Number** — Imported Twilio landline (+61240126220) to Vapi:
   ```
   VAPI_PHONE_NUMBER_ID=b38d6460-d82a-4794-9e40-5c31315151cd
   ```
   Note: This is a landline, not mobile. See Voice AI section for mobile solution.

### Warmforge Mailbox Status

| Mailbox | Heat Score | Status |
|---------|------------|--------|
| david@agencyxos-reach.com | 90 | ✅ WARM (production ready) |
| alex@agencyxos-growth.com | 47 | 🔄 Warming (8 days left) |
| alex@agencyxos-leads.com | 47 | 🔄 Warming (8 days left) |
| alex@agencyxos-reach.com | 47 | ❌ Disabled (free tier limit) |
| david@agencyxos-growth.com | 47 | ❌ Disabled (free tier limit) |
| david@agencyxos-leads.com | 47 | ❌ Disabled (free tier limit) |

**Finding:** Warmforge free tier limits to 2 concurrent warmups. Need to upgrade or rotate.

---

## Part 2: SMS Infrastructure Decision

### Provider Comparison

| Feature | ClickSend | Twilio |
|---------|-----------|--------|
| AU Mobile Numbers | ❌ Landline only | ❌ Not allowed for AU |
| SMS Cost | $0.072 AUD | $0.08 USD |
| HQ | Perth, AU | US |
| Vapi Integration | ❌ No | ✅ Yes (voice only) |
| Current Usage | ✅ Active | Voice only |

**Decision:** Keep ClickSend for SMS. They're Perth-based, have direct AU carrier routes, and we're already integrated.

### Number Strategy

**Decision:** 1 dedicated number per client

**Rationale:**
- Cost: $19 AUD/mo per client (absorbed into $2,500 subscription)
- Recipients can reply (2-way SMS)
- Consistent sender = trust
- ACMA compliant with registration

**Volume Analysis (Ignition Tier):**
- Total leads: 1,250
- SMS eligible (ALS 60+): ~500-690 leads (Hot + Warm)
- SMS per lead: 3-4 touches
- Total SMS: ~1,500-2,760
- Daily rate: ~17-30/day

One number per client handles this easily. No rotation needed at Ignition volume.

### 2-Way SMS — New Capability

**Discovery:** Dedicated numbers enable reply handling. This opens conversational SMS.

**Content Strategy Shift:**
- Old (one-way): Statements, CTAs, links
- New (two-way): Open-ended questions for engagement

**Example:**
```
Generic: "Hi Dave, we help agencies book more meetings. See how: {link}"

Personalized: "Dave — saw Keiracom expanded to QLD. How's lead gen going for the new territory?"
```

**Implementation Needed:**
1. ClickSend inbound webhook handler
2. SMS → Lead matching (by phone number)
3. Intent classification (extend Closer Engine for SMS)
4. Conversation thread storage (add SMS as channel type)
5. AI SMS responder (Content Engine + send)
6. STOP handling (immediate unsubscribe)

**Estimate:** 2-3 days to implement.

### SMS Eligibility Change

**Current Blueprint:**
- Hot (85-100): Email, SMS, LinkedIn, Voice, Mail
- Warm (60-84): Email, LinkedIn, Voice (NO SMS)

**Decision:** Extend SMS to Warm tier

**Rationale:**
- SMS reply rates >> email
- Volume stays manageable (~30/day)
- Warm leads are still qualified (passed 60 threshold)
- Different personalization depth:
  - Hot: Deep research SMS (full icebreakers)
  - Warm: Light personalization (name, company, title only)

---

## Part 3: LinkedIn Data Scraping (for ALS Scoring)

### The Problem

Current ALS scores based on **static firmographic data** (Apollo):
- Title, company size, industry

Missing **dynamic intent signals**:
- Recent LinkedIn posts
- Engagement levels
- Hiring signals
- Profile activity

A lead at ALS 70 might have strong intent signals we never see because Deep Research only runs at 85+.

### Solution: Two-Stage Scoring

**New Flow:**
```
1. Apollo enriches lead (basic data)
            ↓
2. Lightweight LinkedIn scan (ALL leads)
   - Post count last 30 days
   - Engagement level
   - Profile completeness
   - Company hiring signals
            ↓
3. ALS scores WITH social signals
   - New component: Social Activity (0-10 points)
            ↓
4. IF ALS >= 85 → Deep Research (full content scrape)
            ↓
5. Content Engine generates outreach
```

### New ALS Component: Social Activity (0-10 points)

| Signal | Points |
|--------|--------|
| Posted on LinkedIn last 7 days | +3 |
| Posted last 30 days | +2 |
| High engagement on posts | +2 |
| Company hiring (from LinkedIn) | +2 |
| Profile completeness >80% | +1 |
| **Max Social Score** | **10** |

This can push a 75 → 85, making them Hot and triggering deep research.

### Provider Decision: Proxycurl (Nubela)

**Comparison:**

| Factor | Proxycurl | Coresignal | Our Scrapers |
|--------|-----------|------------|--------------|
| Activity data | ✅ Yes | ✅ Yes | ⚠️ Manual |
| Data freshness | Real-time | Monthly | On-demand |
| Cost/credit | $0.012 | $0.080 | Proxy costs |
| 1,250 leads cost | ~$15 | ~$100 | Variable |
| Reliability | ✅ High | ✅ High | ⚠️ Rate limits |

**Decision:** Proxycurl (Nubela) Growth plan

**Pricing:**
- $299/mo = 25,000 credits
- 1 credit = 1 profile lookup
- 1,250 leads = 1,250 credits
- **Covers 20 Ignition clients per month**
- **Cost per client: ~$15**

**Why Proxycurl over Coresignal:**
- 6-7x cheaper at our volume
- Real-time data (fresher)
- Same activity data we need
- Simpler API

**Data Fields Available:**
- Recent posts with timestamps
- Engagement counts (likes, comments)
- Profile completeness
- Current company headcount changes
- Recent job changes

---

## Part 4: Voice AI Infrastructure

### The Problem

Current setup uses Twilio landline (+61240126220):
- +612 = NSW landline
- Looks less trustworthy than mobile for cold calls
- Twilio doesn't offer AU mobile numbers

### Provider Research

**Vapi-Compatible Providers:**
- Twilio ✅ (current, but no AU mobile)
- Vonage ✅ (native Vapi)
- Telnyx ✅ (native Vapi, has AU mobile)
- Plivo ⚠️ (SIP only, more complex)
- ClickSend ❌ (no SIP, won't work with Vapi)

**Decision:** Add Telnyx for Australian mobile caller ID

**Why Telnyx:**
- Native Vapi integration (simple import like Twilio)
- Australian mobile numbers (+614xx) available
- Licensed carrier (proper Telstra/Optus termination)
- Cost: ~$15 AUD/mo + usage
- Requires ID verification via Onfido (straightforward)

### Implementation Steps

1. Create Telnyx account
2. Search for AU mobile number: `filter[country_code]=AU, filter[phone_number_type]=mobile`
3. Complete Onfido ID verification (requires name)
4. Provision number
5. Import to Vapi using Telnyx credentials
6. Update `.env` with new phone number ID
7. Keep Twilio landline as backup

### Australian Compliance Notes (from Research)

**ACMA Requirements:**
- CLI (Caller ID) must be enabled
- Callback number must work for 30 days
- Calling hours: Weekdays 9am-8pm, Sat 9am-5pm, NO Sunday/Public Holidays
- Must disclose name, employer, purpose within first few seconds
- DNCR wash every 30 days

**AI Disclosure:**
- No explicit Australian law requiring AI disclosure (unlike US)
- Best practice: Disclose upfront ("Hi, this is an AI calling on behalf of...")
- Protects against Australian Consumer Law misleading conduct claims

**Twilio-Hosted Requirement:**
- Telstra blocks calls from non-carrier-hosted numbers
- Telnyx is a licensed carrier, so should work

---

## Part 5: Alpha Tag Registration (Future)

### What Are Alpha Tags?

Sending SMS from brand name instead of phone number:
- From number: `+61485031611: "Hi Dave..."`
- From alpha tag: `AgencyOS: "Hi Dave..."`

### New ACMA Regulation: SMS Sender ID Register

**Deadline:** December 2025 (some sources say July 2026)

**Requirement:** All alphanumeric sender IDs must be registered. Unregistered = messages display "Unverified" or "Likely SCAM" or get blocked.

**Impact on Agency OS:**
- If clients want to send as "TheirAgencyName", they need to register
- If WE send as "AgencyOS", we need to register

**Current Decision:** Use dedicated numbers, not alpha tags
- Avoids registration complexity
- Enables 2-way replies (alpha tags can't receive replies)
- Compliant now and after Dec 2025

**Future Consideration:** Build alpha tag registration into onboarding if clients specifically request branded sender IDs.

---

## Part 6: Cost Summary

### Per Ignition Client ($2,500/mo subscription)

| Component | Monthly Cost |
|-----------|--------------|
| SMS number (ClickSend) | $19 |
| SMS usage (~2,000 msgs) | ~$150 |
| LinkedIn scraping (Proxycurl) | ~$15 |
| Voice number (Telnyx) | ~$15 |
| Voice usage (~100 calls) | ~$35 |
| **Total new channel costs** | **~$235** |
| **Margin impact** | **9.4%** |

Still healthy margins on $2,500 subscription.

### Platform-Level Costs

| Service | Monthly | Covers |
|---------|---------|--------|
| Proxycurl Growth | $299 | 20 clients |
| Warmforge | Free (with Salesforge) | 2 concurrent warmups |
| Vapi | Usage-based | - |
| ClickSend | Usage-based | - |

---

## Part 7: Action Items

### Immediate (Before E2E Test)

1. **Telnyx Setup** — Dave creates account, completes ID verification, gets AU mobile number
2. **Proxycurl Trial** — Elliot signs up, tests employee activity endpoint
3. **E2E Test** — Run with Email + SMS + Voice (skip LinkedIn messaging)

### Short-Term (Pre-Launch)

4. **2-Way SMS** — Build inbound webhook handler, intent classification, AI responder
5. **Social Activity Scoring** — Integrate Proxycurl into ALS scoring pipeline
6. **Warmforge Upgrade** — Evaluate plan for 6+ concurrent warmups

### Before December 2025

7. **Alpha Tag Decision** — Decide if offering branded sender IDs to clients
8. **Register "AgencyOS"** — If we send platform-level SMS

---

## Part 8: Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENCY OS CHANNELS                        │
└─────────────────────────────────────────────────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌─────────────┐      ┌─────────────────┐      ┌─────────────┐
│    EMAIL    │      │      SMS        │      │   VOICE AI  │
│             │      │                 │      │             │
│ Salesforge  │      │   ClickSend     │      │    Vapi     │
│ (sending)   │      │   (2-way)       │      │             │
│             │      │                 │      │   Telnyx    │
│ Warmforge   │      │ $19/client/mo   │      │  (AU mobile)│
│ (warmup)    │      │                 │      │             │
└─────────────┘      └─────────────────┘      └─────────────┘
     │                        │                        │
     └────────────────────────┼────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  LEAD SCORING   │
                    │                 │
                    │  Apollo (base)  │
                    │       +         │
                    │  Proxycurl      │
                    │  (social scan)  │
                    │       =         │
                    │  ALS Score      │
                    └─────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
         ┌────────┐      ┌────────┐      ┌────────┐
         │  HOT   │      │  WARM  │      │  COOL  │
         │ 85-100 │      │ 60-84  │      │ 35-59  │
         │        │      │        │      │        │
         │ Email  │      │ Email  │      │ Email  │
         │ SMS    │      │ SMS    │      │ LI     │
         │ Voice  │      │ LI     │      │        │
         │ LI     │      │ Voice  │      │        │
         │ Mail   │      │        │      │        │
         └────────┘      └────────┘      └────────┘
```

---

## Part 9: Key Decisions Log

| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Keep ClickSend for SMS | Perth-based, already integrated, direct AU routes | 2026-02-03 |
| 2 | 1 dedicated number per client | Enables replies, consistent trust, $19/mo acceptable | 2026-02-03 |
| 3 | Extend SMS to Warm tier (60+) | Higher engagement than email, volume manageable | 2026-02-03 |
| 4 | Add Telnyx for Voice | AU mobile numbers, native Vapi, licensed carrier | 2026-02-03 |
| 5 | Use Proxycurl for LinkedIn scan | 6-7x cheaper than Coresignal, real-time data | 2026-02-03 |
| 6 | Add Social Activity to ALS | Catches intent signals before 85 threshold | 2026-02-03 |
| 7 | Use dedicated numbers, not alpha tags | Avoids Dec 2025 registration, enables 2-way | 2026-02-03 |

---

*Session duration: ~1 hour*
*Agents spawned: 7 (env-testmode, audit-sms, audit-vapi, audit-warmforge, research-telephony, research-compliance, research-vapi-providers)*
