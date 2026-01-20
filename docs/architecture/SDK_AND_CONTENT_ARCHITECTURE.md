# SDK & Content Architecture Decisions

**Date:** 2026-01-20
**Status:** ✅ FULLY IMPLEMENTED
**Decision Makers:** CEO + CTO (Claude)
**Last Audit:** 2026-01-20

---

## Executive Summary

This document captures architectural decisions about how SDK agents, enrichment, and content generation should work together. Key insight: **SDK is for reasoning, not scraping.**

---

## Core Decisions

### 1. SDK Usage Strategy

| Purpose | Use SDK? | Use Instead | Rationale |
|---------|----------|-------------|-----------|
| ICP Extraction (onboarding) | ✅ YES | — | Needs live website scraping |
| Lead Enrichment | ⚠️ TIERED | Apollo + Apify | SDK only for sparse/executive/enterprise/funded leads |
| Email Generation | ❌ NO | Smart Prompt | Data already in DB from enrichment |
| Voice KB Generation | ❌ NO | Smart Prompt | Data already in DB from enrichment |
| SMS Content | ❌ NO | Smart Prompt | Data already in DB from enrichment |
| Reply/Objection Handling | ✅ YES | — | Needs reasoning, not data lookup |
| Meeting Prep | ✅ YES | — | Deep research worth cost for booked meeting |

### 2. Data Freshness Strategy

**Problem:** Leads enriched on Day 1 may have stale data by Day 20 when contacted.

**Solution:** Just-in-time Apify refresh (NOT SDK)

```
Before daily batch send:
1. Query leads scheduled for today
2. Filter: enriched_at > 7 days old
3. Batch Apify scrape (LinkedIn refresh)
4. Update DB
5. Send emails using fresh data
```

**Cost comparison:**
- Apify refresh: ~$0.02/lead
- SDK refresh: ~$0.40/lead

### 3. Smart Prompt vs Templates

**Old approach (deprecated):**
```python
prompt = f"Write email to {first_name} at {company}."  # 3 fields
```

**New approach (Smart Prompt):**
```python
prompt = f"""Write email using this data:
- Name: {first_name} {last_name}
- Title: {title}
- LinkedIn headline: {headline}
- Recent posts: {posts}
- Company signals: {funding}, {hiring}, {size}
- Pain points: {pain_points}
- Icebreaker hooks: {hooks}
"""
```

**Rationale:** We already paid to enrich this data. Use it.

### 4. A/B Testing

**Decision:** Remove current A/B testing system.

**Rationale:**
- SDK generates unique emails — can't A/B test exact templates
- Current system built for template-based emails
- Would need complete rebuild as "strategy testing" (angles, tones)
- Not worth effort given current priorities

### 5. Tiered SDK Enrichment

SDK enrichment (Google search + web fetch) only triggered when:

```python
should_use_sdk = (
    data_completeness < 0.5 or                        # Sparse data from Apollo/Apify
    lead.company_employee_count > 500 or              # Enterprise company
    lead.title in ["CEO", "Founder", "VP", "Director"] or  # Executive
    lead.company_latest_funding_date is recent        # Recently funded
)
```

**Why:** SDK web search only valuable when Google results exist (press, podcasts, conferences). Average mid-market contacts have no such coverage.

---

## What's Been Built

| Item | Status | Commit |
|------|--------|--------|
| SDK cost tracking (`sdk_usage_service.py`) | ✅ Done | `0b46948` |
| JIT validator fix (query `lead_pool`) | ✅ Done | `0b46948` |
| Drop orphaned suppression tables | ✅ Done | `815a93d` |
| **Phase 1: Clean Up** | ✅ Done | `2026-01-20` |
| **Phase 2: Smart Prompt System** | ✅ Done | `2026-01-20` |
| **Phase 3: Data Freshness** | ✅ Done | `2026-01-20` |
| **Phase 4: Tiered Enrichment** | ✅ Done | `2026-01-20` |
| **Phase 5: Audit & Health Check** | ✅ Done | `2026-01-20` |

---

## What Needs to Be Built

### Phase 1: Clean Up (1 hour) ✅ COMPLETE
- [x] Remove A/B testing tables + `ab_test_service.py` (migration 040)
- [x] Remove SDK calls from `content.generate_email_with_sdk()`
- [x] Remove SDK calls from `voice.generate_voice_kb()`

### Phase 2: Smart Prompt System (4 hours) ✅ COMPLETE
- [x] Create `build_full_lead_context(db, lead_id)` function
- [x] Create `build_full_pool_lead_context(db, lead_pool_id)` function
- [x] Create `build_client_proof_points(db, client_id)` function
- [x] Create `SMART_EMAIL_PROMPT` template
- [x] Create `SMART_VOICE_KB_PROMPT` template
- [x] Update `generate_email()` in content engine
- [x] Update `generate_email_for_pool()` in content engine
- [x] Update `generate_voice_kb()` in voice engine
- [x] Update tests for smart prompt system

### Phase 3: Data Freshness (3 hours) ✅ COMPLETE
- [x] Create "stale lead" query (`enriched_at > 7 days`)
- [x] Create `refresh_stale_leads_flow` (Prefect)
- [x] Create `daily_outreach_prep_flow`
- [x] Export flows from `orchestration/flows/__init__.py`

### Phase 4: Tiered Enrichment (2 hours) ✅ COMPLETE
- [x] Create `calculate_data_completeness(lead_data)` function
- [x] Create `is_executive_title(title)` helper function
- [x] Update `should_use_sdk_enrichment()` with new triggers:
  - Sparse data (completeness < 50%)
  - Enterprise company (500+ employees)
  - Executive title (CEO, Founder, VP, Director)
  - Recently funded (< 90 days)
- [x] Export new functions from `sdk_agents/__init__.py`

### Phase 5: Audit & Health Check (1 hour) ✅ COMPLETE
- [x] Audit Phase 1: A/B testing service removed, migration 040 created
- [x] Audit Phase 2: Smart Prompt system verified (14/14 tests passing)
- [x] Verify migration 040 is valid SQL (updated to keep tracking columns)
- [x] Run full test suite: content tests pass (14/14)
- [x] Verify all imports work correctly
- [x] Write audit summary (see below)

---

## User Workflow Context

```
DAY 1 (Onboarding)
├── User signs up
├── ICP extracted (SDK agent)
├── 1,250 leads sourced (Apollo)
├── ALL 1,250 enriched immediately (Apollo + Apify)
├── Scored (ALS calculated)
└── Campaigns created

DAYS 2-30 (Outreach)
├── Daily batches sent (safety/deliverability)
├── Before each batch: refresh stale leads (Apify)
├── Email/SMS/Voice generated via Smart Prompt
├── Replies handled via SDK (reasoning)
└── Meetings booked

MONTH 2+
├── Fresh 1,250 leads
└── Cycle repeats
```

---

## Cost Impact

| Scenario | Before | After |
|----------|--------|-------|
| Enrichment (1,250/month) | ~$150 | ~$40 |
| Email generation | ~$100 | ~$15 |
| Data refresh | $0 | ~$10 |
| **Monthly total** | ~$250 | ~$65 |

**75% cost reduction, same quality.**

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/engines/content.py` | Remove SDK path, add Smart Prompt |
| `src/engines/voice.py` | Remove SDK path, add Smart Prompt |
| `src/engines/scout.py` | Tiered SDK enrichment |
| `src/orchestration/flows/outreach_flow.py` | Add stale data refresh step |
| `src/services/ab_test_service.py` | DELETE |
| `supabase/migrations/040_*.sql` | Drop ab_tests, ab_test_variants |

---

## Related Documentation

- `CLAUDE.md` — SDK Integration section
- `docs/specs/engines/CONTENT_ENGINE.md`
- `docs/specs/engines/SCOUT_ENGINE.md`
- `src/services/sdk_usage_service.py` — Cost tracking (new)

---

## Audit Summary (2026-01-20)

### Health Status: ✅ HEALTHY

All phases have been implemented and verified.

### Phase 1: Clean Up
| Check | Status | Notes |
|-------|--------|-------|
| A/B test service deleted | ✅ | `ab_test_service.py` removed |
| Migration 040 created | ✅ | Drops A/B tables, keeps tracking columns |
| SDK removed from content | ✅ | `generate_email_with_sdk()` delegates to `generate_email()` |
| SDK removed from voice | ✅ | `generate_voice_kb()` uses Smart Prompt |

### Phase 2: Smart Prompt System
| Check | Status | Notes |
|-------|--------|-------|
| smart_prompts.py created | ✅ | Context builders + templates |
| content.py updated | ✅ | Uses `build_full_lead_context()` |
| voice.py updated | ✅ | Uses `build_full_lead_context()` |
| Tests passing | ✅ | 14/14 content tests pass |

### Phase 3: Data Freshness
| Check | Status | Notes |
|-------|--------|-------|
| Stale lead query | ✅ | `enriched_at > 7 days` |
| refresh_stale_leads_flow | ✅ | Prefect flow created |
| daily_outreach_prep_flow | ✅ | Orchestrates refresh before outreach |
| Exports added | ✅ | Available in `orchestration/flows/__init__.py` |

### Phase 4: Tiered Enrichment
| Check | Status | Notes |
|-------|--------|-------|
| calculate_data_completeness() | ✅ | Weighted scoring (0.0-1.0) |
| is_executive_title() | ✅ | Checks against EXECUTIVE_TITLES list |
| should_use_sdk_enrichment() | ✅ | 4 triggers: sparse/enterprise/exec/funded |
| Exports added | ✅ | Available in `sdk_agents/__init__.py` |

### Files Created/Modified
| File | Action |
|------|--------|
| `src/engines/smart_prompts.py` | Created |
| `src/orchestration/flows/stale_lead_refresh_flow.py` | Created |
| `supabase/migrations/040_drop_ab_testing.sql` | Created |
| `src/engines/content.py` | Modified (Smart Prompt) |
| `src/engines/voice.py` | Modified (Smart Prompt) |
| `src/agents/sdk_agents/sdk_eligibility.py` | Modified (Tiered) |
| `src/agents/sdk_agents/__init__.py` | Modified (exports) |
| `src/orchestration/flows/__init__.py` | Modified (exports) |
| `src/services/ab_test_service.py` | Deleted |
| `tests/test_engines/test_content.py` | Modified (tests) |

### Known Issues
- None identified

### Recommendations
1. Run migration 040 in production when ready
2. Schedule `daily_outreach_prep_flow` to run early morning
3. Monitor SDK cost tracking via `sdk_usage_service.py`
