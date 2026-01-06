# Phase 24: Lead Pool Architecture

**Status:** 📋 Planned  
**Priority:** High (Pre-Launch)  
**Spec:** `docs/specs/LEAD_POOL_ARCHITECTURE.md`  
**Estimate:** 43 hours

---

## Overview

Implement a centralised lead pool where Agency OS owns and controls all leads. Leads are exclusively assigned to one client — no lead will ever be contacted by multiple agencies.

---

## Why This Phase

### Problem 1: Cross-Campaign Spam
Same lead can appear in multiple campaigns and get contacted via email, LinkedIn, SMS simultaneously.

### Problem 2: Cross-Client Collision  
Two clients targeting same industry could both contact the same lead.

### Problem 3: Wasted Data
Apollo gives us 50+ fields per lead. We only save ~20. Throwing away valuable personalisation data.

---

## Solution Summary

| Component | What It Does |
|-----------|--------------|
| **Lead Pool** | Master table of all leads, fully enriched |
| **Lead Assignments** | Tracks which client owns which lead (exclusive) |
| **JIT Validation** | Pre-send checks before any outreach |
| **Full Data Capture** | Save all 50+ fields from Apollo |

---

## Core Rules

1. **One lead = One client** — No lead is ever contacted by two agencies
2. **Platform controls distribution** — Allocator decides who gets which lead
3. **Save everything** — All enrichment data captured
4. **Validate before every send** — JIT checks prevent bad sends

---

## Tasks

| ID | Task | Priority | Est | Status |
|----|------|----------|-----|--------|
| POOL-001 | Create `lead_pool` table migration | High | 2h | ⬜ |
| POOL-002 | Create `lead_assignments` table migration | High | 1h | ⬜ |
| POOL-003 | Add pool references to existing `leads` table | High | 1h | ⬜ |
| POOL-004 | Update Apollo integration to capture all fields | High | 3h | ⬜ |
| POOL-005 | Create Lead Pool service (CRUD operations) | High | 4h | ⬜ |
| POOL-006 | Create Allocator service (assignment logic) | High | 4h | ⬜ |
| POOL-007 | Implement JIT Validation service | High | 4h | ⬜ |
| POOL-008 | Update Scout Engine to write to pool first | High | 3h | ⬜ |
| POOL-009 | Update Scorer Engine to read from pool | Medium | 2h | ⬜ |
| POOL-010 | Update Content Engine to use new fields | Medium | 3h | ⬜ |
| POOL-011 | Update campaign lead assignment flow | High | 4h | ⬜ |
| POOL-012 | Add pool admin UI (view pool, manual assign) | Low | 4h | ⬜ |
| POOL-013 | Migrate existing leads to pool | Medium | 2h | ⬜ |
| POOL-014 | Add pool analytics (utilisation, assignment rate) | Low | 2h | ⬜ |
| POOL-015 | Write tests for pool operations | High | 4h | ⬜ |

**Total:** 15 tasks, 43 hours

---

## New Database Tables

### `lead_pool` (Master lead record)
- All enrichment data (50+ fields)
- Global status (bounced, unsubscribed)
- Deduplication via `apollo_id` and `email`

### `lead_assignments` (Client ownership)
- Links pool lead to client
- Exclusive — one lead can only have one active assignment
- Tracks contact history, outcomes

---

## JIT Validation Checks

Before ANY outreach:

| Check | Blocks If... |
|-------|--------------|
| Pool: Bounced | Email has bounced globally |
| Pool: Unsubscribed | Lead requested no contact |
| Pool: Email status | Email is "guessed" not "verified" |
| Assignment: Active | Lead not assigned to this client |
| Assignment: Replied | Lead has already replied |
| Assignment: Recent | Contacted within last 3 days |
| Channel: Cooling | Same channel used within 7 days |
| Rate: Limit | Daily send limit reached |
| Warmup: Ready | Email warmup incomplete |

---

## Data Capture Improvement

| Category | Before | After |
|----------|--------|-------|
| Person fields | 10 | 20+ |
| Organisation fields | 10 | 20+ |
| Total | ~20 | ~50 |

Key new fields:
- `email_status` (verified/guessed)
- `linkedin_headline`
- `city`, `state`, `country`
- `company_description`
- `company_revenue`
- `company_technologies`
- `employment_history` (full)

---

## Dependencies

| Phase | Dependency |
|-------|------------|
| Phase 3 | Apollo integration (update) |
| Phase 4 | Scout, Scorer, Content engines (update) |
| Phase 19 | Email infrastructure (JIT warmup check) |

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Lead collision rate | 0% |
| Data capture rate | 100% of Apollo fields |
| JIT validation coverage | 100% of sends |
| Bounce rate | <3% |

---

## Files to Create/Modify

### New Files
- `supabase/migrations/024_lead_pool.sql`
- `src/services/lead_pool.py`
- `src/services/lead_allocator.py`
- `src/services/jit_validator.py`

### Modified Files
- `src/integrations/apollo.py` — Full field capture
- `src/engines/scout.py` — Write to pool
- `src/engines/scorer.py` — Read from pool
- `src/engines/content.py` — Use new fields
- `src/engines/email.py` — JIT validation
- `src/engines/sms.py` — JIT validation
- `src/engines/linkedin.py` — JIT validation
- `src/engines/voice.py` — JIT validation
- `src/engines/mail.py` — JIT validation

---

## Risks

| Risk | Mitigation |
|------|------------|
| Migration corrupts data | Backup before, test on staging |
| Pool query performance | Proper indexes |
| Race condition on assignment | Database unique constraint |

---

## Completion Checklist

- [ ] All migrations applied
- [ ] Lead Pool service working
- [ ] Allocator assigning leads correctly
- [ ] JIT validation blocking bad sends
- [ ] All Apollo fields captured
- [ ] Existing leads migrated
- [ ] Tests passing
- [ ] Documentation updated
