# E2E Testing Plan — Final Decision

**Status:** APPROVED
**Date:** January 11, 2026 (Updated January 12, 2026)
**Owner:** CTO
**Budget:** $65 AUD (increased for J2B enrichment)

---

## Test Agency: Sparro Digital

| Field | Value |
|-------|-------|
| **Agency Name** | Sparro |
| **Website** | https://sparro.com.au |
| **Location** | Melbourne, Australia |
| **Type** | Digital Marketing Agency (Performance Marketing) |
| **Size** | ~30-50 employees |
| **Estimated MRR** | $80-150K (based on team size, clients) |
| **Services** | Paid Media, SEO, Social, Analytics |
| **Target Clients** | E-commerce, Retail, DTC brands |

### Why Sparro

| Criteria | Assessment |
|----------|------------|
| **Can afford Agency OS?** | Yes - Velocity or Dominance tier |
| **Clear ICP?** | Yes - E-commerce marketing managers, DTC founders |
| **Website scrapable?** | Yes - Clean site, services/case studies visible |
| **Realistic customer?** | Yes - Growth agency needing pipeline |
| **B2B services?** | Yes - Serves business clients |
| **Australian?** | Yes - Melbourne HQ |

### Why NOT Umped

Umped (previous test agency) was rejected because:
- Smaller recruitment agency, likely under $30K MRR
- Cannot afford $2,500/mo minimum tier
- Does not represent target demographic

---

## Agency OS Target Demographic

| Attribute | Value |
|-----------|-------|
| **Revenue** | $360K-$1.2M+ AUD/year ($30-100K+ MRR) |
| **Team Size** | 2-15 people |
| **Average Client Value** | $4,000+/month |
| **Location** | Australia |
| **Current State** | Doing outbound manually OR paying SDR/agency |
| **Growth Goal** | Want 1-10 new clients/month |

### Agency Types That Fit

| Agency Type | Fit | Why |
|-------------|-----|-----|
| Digital/Marketing Agencies | Excellent | High volume B2B, clear ICP, $3-10K clients |
| Creative/Design Agencies | Good | B2B focus, $5-20K projects |
| Web Dev/Tech Agencies | Good | Technical buyers, $10-50K projects |
| Consulting Firms | Good | High-value clients, $5-20K+ |
| Enterprise Recruitment | Maybe | Depends on size |
| Solo Freelancers | No | Can't afford $2,500/mo |
| Enterprise Agencies | No | Already have SDR teams |

---

## Test Configuration

### Test Agency Profile

```
Agency Name:        Sparro Digital
Website:            https://sparro.com.au
Industry:           Digital Marketing / Performance Marketing
Location:           Melbourne, VIC, Australia
Team Size:          30-50
Estimated MRR:      $100K+
Tier:               Velocity ($5,000/mo)
```

### Target ICP (Expected from Extraction)

```
Titles:             Marketing Manager, Head of Digital,
                    E-commerce Manager, CMO, Founder
Industries:         E-commerce, Retail, DTC, Fashion,
                    Beauty, Consumer Goods
Company Size:       10-200 employees
Location:           Australia (primary), NZ (secondary)
Pain Points:        ROAS pressure, scaling paid media,
                    attribution, incrementality
```

### Test Recipients (All Outreach Redirects Here)

| Channel | Recipient |
|---------|-----------|
| Email | david.stephens@keiracom.com |
| SMS | +61457543392 |
| Voice | +61457543392 |
| LinkedIn | linkedin.com/in/david-stephens-8847a636a/ |

### Sending Domains (Warmforge → Salesforge)

| Domain | Mailboxes | Status | Daily Limit |
|--------|-----------|--------|-------------|
| agencyxos-growth.com | 2 | Warming | 15/mailbox |
| agencyxos-reach.com | 2 | Warming | 15/mailbox |
| agencyxos-leads.com | 2 | Warming | 15/mailbox |

**Total:** 6 mailboxes × 15/day = **90 emails/day capacity** (post-warmup)
**During E2E:** 15 emails/day total (protect warmup)
**Ready Date:** January 20, 2026

---

## Email Infrastructure

| Component | Value |
|-----------|-------|
| **Sending Provider** | Salesforge (via Warmforge mailboxes) |
| **Total Mailboxes** | 6 |
| **Domains** | 3 |
| **Daily Limit (Warmup)** | 15 total |
| **Daily Limit (Post-Warmup)** | 90 total |
| **Threading** | In-Reply-To + References headers |
| **Webhooks** | Salesforge → /api/v1/webhooks/salesforge/events |

### Velocity Tier Capacity (Post-Launch)

| Channel | Monthly Allocation | Daily Rate |
|---------|-------------------|------------|
| Email | 2,250 leads | ~75/day |
| LinkedIn | 3 seats × 20/day | 60/day |
| Voice | 844 minutes | ~28 calls/day |
| SMS | 225 messages | ~8/day |
| Direct Mail | 225 postcards | ~8/day |

---

## ALS (Agency Lead Score) Implementation

**File:** `src/engines/scorer.py`
**Spec:** `docs/specs/engines/SCORER_ENGINE.md`
**E2E Journey:** J2.7 (Base Scoring), J2B.5 (LinkedIn Boost)

### Scoring Formula (100 points max + boosts)

| Component | Max Points | Weight | What It Measures |
|-----------|------------|--------|------------------|
| Data Quality | 20 | 20% | Verified email, phone, LinkedIn |
| Authority | 25 | 25% | Job title seniority |
| Company Fit | 25 | 25% | Industry, size, location |
| Timing | 15 | 15% | New role, hiring, funding |
| Risk | 15 | 15% | Bounces, unsubscribes, competitors |
| **LinkedIn Boost** | +10 | Additive | Engagement signals from enrichment |
| **Buyer Boost** | +15 | Additive | Known agency buyer (Phase 24F) |

### LinkedIn Enrichment Boost (Phase 24A+)

Leads enriched via J2B get up to +10 additional ALS points:

| Signal | Points | Condition |
|--------|--------|-----------|
| Person has posts | +3 | Active on LinkedIn |
| Company has posts | +2 | Active company page |
| 500+ connections | +2 | Influential network |
| 1000+ followers | +2 | Established company |
| Posted in 30 days | +1 | Recently active |
| **MAX TOTAL** | **+10** | Capped |

**Impact Example:** A lead scoring 78 (Warm) can reach 88 (Hot) after enrichment, unlocking SMS/Voice channels.

### Tier Thresholds

| Tier | Score | Channels Available |
|------|-------|-------------------|
| **Hot** | 85-100 | Email, SMS, LinkedIn, Voice, Direct Mail |
| **Warm** | 60-84 | Email, LinkedIn, Voice |
| **Cool** | 35-59 | Email, LinkedIn |
| **Cold** | 20-34 | Email only |
| **Dead** | <20 | None (suppressed) |

**CRITICAL:** Hot starts at 85, NOT 80.

### Expected Tier Distribution (50 Test Leads)

| Tier | Expected % | Count | Channels |
|------|------------|-------|----------|
| Hot | 10% | 5 | All 5 |
| Warm | 25% | 12-13 | 3 |
| Cool | 40% | 20 | 2 |
| Cold | 20% | 10 | 1 |
| Dead | 5% | 2-3 | 0 |

**Note:** After J2B enrichment, Hot tier may increase to 15-20% as LinkedIn boosts push Warm leads up.

---

## Compliance Integrations

### DNCR (Australian Do Not Call Register)

**File:** `src/integrations/dncr.py`
**E2E Journey:** J4.4

| Setting | Value |
|---------|-------|
| API URL | https://api.dncr.gov.au/v1 |
| Cache TTL | 24 hours (Redis) |
| Required For | SMS outreach to Australian numbers (+61) |

**How it works:**
1. Before sending SMS, `twilio.py` calls `dncr_client.check_number()`
2. DNCRClient checks Redis cache first (24hr TTL)
3. If not cached, calls ACMA DNCR API
4. If on DNCR, SMS is blocked and logged as `rejected_dncr`
5. Graceful fallback if DNCR API unavailable

**TEST_MODE:** DNCR check still runs but test recipient bypasses block.

### Cal.com (Meeting Scheduling)

**File:** `src/api/routes/webhooks.py` (lines 1589-1722)
**E2E Journey:** J8.3

| Event | Handler Action |
|-------|----------------|
| BOOKING_CREATED | Create meeting record, link to lead |
| BOOKING_CANCELLED | Update meeting status, log reason |
| BOOKING_RESCHEDULED | Update scheduled_at timestamp |

---

## Budget

### Paid API Costs

| API | Purpose | Usage | Cost (AUD) |
|-----|---------|-------|------------|
| **Apollo** | Source 50 test leads matching Sparro's ICP | 50 credits | $50.00 |
| **Apify** | LinkedIn person scraping (J2B.2) | 20 profiles | $1.00 |
| **Apify** | LinkedIn company scraping (J2B.3) | 20 companies | $1.00 |
| **Anthropic** | ICP extraction + content gen + personalization analysis | ~200K tokens | $9.00 |
| **Twilio SMS** | TEST_MODE verification | 5 SMS | $0.40 |
| **Twilio Voice** | TEST_MODE verification | 3 calls | $0.20 |
| **Salesforge** | Email sending | Included | $0.00 |
| **HeyReach** | LinkedIn TEST_MODE | 3 requests | Included |
| **TOTAL** | | | **~$61.60** |

### What We're NOT Spending On

- No volume lead sourcing (save for real customers)
- No real cold outreach (TEST_MODE only)
- No additional mailbox purchases
- No new integrations

---

## Execution Timeline

| Date | Phase | Journey | Deliverable |
|------|-------|---------|-------------|
| Jan 11-12 | Infrastructure | J0 | All services verified, no blockers |
| Jan 13 | Onboarding | J1 | Sparro user created, ICP extracted |
| Jan 14 | Campaign | J2 | 50 leads sourced, scored, assigned |
| Jan 14 | Enrichment | J2B | LinkedIn scraped, ALS boosted, personalization ready |
| Jan 15 | Outreach | J3-J4 | Email + SMS TEST_MODE verified |
| Jan 16 | Outreach | J5-J6 | Voice + LinkedIn functional |
| Jan 17 | Replies | J7 | Intent classification working |
| Jan 18 | Meetings | J8 | Calendar webhooks, deal creation |
| Jan 19 | Dashboard | J9 | Metrics accuracy verified |
| Jan 20 | Admin | J10 | Platform admin functional |

**System ready for first real customer: January 20, 2026**

---

## Approval Gates

| Gate | Trigger | Cost | CEO Action |
|------|---------|------|------------|
| **GATE-1** | Start J0 | $0 | Approve this plan |
| **GATE-2** | ICP extraction (J1.10) | ~$3 | Approve Anthropic call |
| **GATE-3** | Lead sourcing (J2.3) | ~$50 | Approve Apollo 50 credits |
| **GATE-4** | Any outreach (J3+) | ~$1 | Confirm TEST_MODE verified |

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Sparro website changes | Low | Medium | Fallback: Use archived version or pick similar agency |
| ICP extraction fails | Low | Medium | Manual ICP definition based on services page |
| Apollo has no matches | Low | Medium | Broaden ICP to "Australian e-commerce" |
| TEST_MODE misconfigured | Medium | Critical | Verify before every outreach test |
| Mailbox warmup interrupted | Low | High | Daily limit = 15, no bulk sends |

---

## Success Criteria

E2E testing is complete when:

- [x] Test agency selected (Sparro)
- [ ] J0: Infrastructure passes (all 9 sub-task groups including meta-check)
- [ ] J1: Signup → ICP extraction → Dashboard works
- [ ] J2: 50 leads sourced, scored, assigned
- [ ] J2B: LinkedIn enriched, personalization generated, ALS boosted
- [ ] J3: Email channel sends to test recipient
- [ ] J4: SMS channel sends to test recipient
- [ ] J5: Voice channel calls test recipient
- [ ] J6: LinkedIn channel sends to test profile
- [ ] J7: Reply handling classifies intent correctly
- [ ] J8: Meeting webhook creates deal
- [ ] J9: Dashboard shows accurate metrics
- [ ] J10: Admin panel fully functional
- [ ] All critical issues resolved
- [ ] All fixes documented
- [ ] Mailboxes ready (Jan 20)

---

## Key Files Reference

| Document | Purpose |
|----------|---------|
| `E2E_MASTER.md` | Status dashboard |
| `E2E_INSTRUCTIONS.md` | Execution protocol |
| `E2E_TASK_BREAKDOWN.md` | What we're testing |
| `J0_INFRASTRUCTURE.md` | Infrastructure audit (9 groups) |
| `J1_ONBOARDING.md` | Signup & onboarding journey |
| `J2_CAMPAIGN.md` | Campaign & lead sourcing journey |
| `J2B_ENRICHMENT.md` | LinkedIn enrichment & ALS boost journey |
| `J3_EMAIL.md` - `J6_LINKEDIN.md` | Outreach channel journeys |
| `J7_REPLY.md` | Reply handling journey |
| `J8_MEETING.md` | Meeting & deals journey |
| `J9_DASHBOARD.md` | Dashboard validation journey |
| `J10_ADMIN.md` | Admin panel journey |
| `ISSUES_FOUND.md` | Problems discovered |
| `FIXES_APPLIED.md` | Changes made |

---

## Immediate Next Action

1. CEO approves this plan
2. CTO begins J0.1 (Railway Services Health Check)
3. No paid APIs until Gate 2

---

*Document created January 11, 2026. Approved by CEO.*
