# Lead Pool Architecture — Executive Summary

**Date:** January 6, 2026  
**For:** Dave (CEO)

---

## What We Discussed

### Problem 1: Same Lead Getting Spammed

**Issue:** If you create 5 similar campaigns, the same person could get:
- Email on Monday
- LinkedIn message on Tuesday
- SMS on Wednesday
- Phone call on Thursday

All from different campaigns. They feel spammed.

**Solution:** Before we send ANYTHING, we check:
- Have we already contacted this person?
- Have they replied?
- Has their email bounced?
- Are we sending too much today?

If any of these are true, we don't send.

---

### Problem 2: Two Agencies Contacting Same Lead

**Issue:** Agency A and Agency B both do marketing for construction companies. Both want to reach Sarah (CEO of BuildRight Construction).

Without protection, Sarah gets pitched by both agencies. Confusing and annoying.

**Solution:** **One lead = One agency.** Forever.

- Sarah goes into the platform Lead Pool
- When Agency A starts a construction campaign, Sarah gets assigned to them
- Agency B can never get Sarah — they get different construction leads
- Sarah only ever hears from one marketing agency

---

### Problem 3: Throwing Away Data We Paid For

**Issue:** Apollo gives us 50+ pieces of information about each lead. We only save about 20.

**What we're losing:**
- Is the email verified or guessed? (guessed = more bounces)
- Person's LinkedIn headline (great for personalisation)
- Person's city (for timezone and location-based messaging)
- Company description (don't need to scrape their website)
- Company revenue (big vs small = different pitch)
- Tech stack (what software they use)
- Previous jobs (connection points)

**Solution:** Save everything. We already paid for it.

---

## The New Architecture (Simple Version)

```
AGENCY OS LEAD POOL
(We own all the leads)
        │
        ▼
   WE DECIDE WHO GETS WHO
        │
   ┌────┴────┐
   ▼         ▼
Agency A   Agency B
gets:      gets:
Sarah      Mike
Tom        Lisa
Jane       Paul

Sarah will NEVER go to Agency B.
Mike will NEVER go to Agency A.
```

---

## What Happens When...

| Event | What Happens |
|-------|--------------|
| Email bounces | Lead marked as bounced — NO ONE can email them again |
| Lead says "not interested" | Cooling period (no contact for 12 months) |
| Lead converts (becomes customer) | They stay with that agency forever |
| Lead asks to be removed | Marked as unsubscribed — no one contacts again |
| Agency cancels subscription | Their leads go back to the pool for others |
| Pool runs out of matching leads | We enrich more |

---

## Documents Created

| Document | Location | What It Contains |
|----------|----------|------------------|
| Full Technical Spec | `docs/specs/LEAD_POOL_ARCHITECTURE.md` | Database tables, code examples, validation rules, all 50+ fields |
| Phase Task List | `docs/phases/PHASE_24_LEAD_POOL.md` | 15 implementation tasks |

---

## Implementation Effort

| Metric | Value |
|--------|-------|
| Tasks | 15 |
| Estimated Hours | 43 |
| Priority | High (Pre-Launch) |
| Phase Number | 24 |

---

## Key Benefits

1. **No spam** — Lead only hears from one agency, ever
2. **No wasted data** — Save everything we pay for
3. **No collisions** — Platform controls who gets which lead
4. **Better personalisation** — More data = better emails
5. **Platform intelligence** — Learn what works across ALL clients

---

## Next Steps

1. **Review** this summary and the full spec
2. **Approve** for implementation
3. **Prioritise** against current work (Phase 21 E2E tests, etc.)
4. **Implement** — 15 tasks, about 43 hours of work

---

**Questions?** Ask Claude to explain any part in more detail.
