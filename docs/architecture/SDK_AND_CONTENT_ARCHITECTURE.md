# SDK & Content Architecture Decisions

**Date:** 2026-01-20
**Status:** Partially Implemented
**Decision Makers:** CEO + CTO (Claude)

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

---

## What Needs to Be Built

### Phase 1: Clean Up (1 hour)
- [ ] Remove A/B testing tables + `ab_test_service.py`
- [ ] Remove SDK calls from `content.generate_email_with_sdk()`
- [ ] Remove SDK calls from `voice.generate_voice_kb()`

### Phase 2: Smart Prompt System (4 hours)
- [ ] Create `build_full_lead_context(db, lead_id)` function
- [ ] Create `SMART_EMAIL_PROMPT` template
- [ ] Create `SMART_VOICE_KB_PROMPT` template
- [ ] Replace template path in content engine
- [ ] Replace template path in voice engine

### Phase 3: Data Freshness (3 hours)
- [ ] Create "stale lead" query (`enriched_at > 7 days`)
- [ ] Create `refresh_stale_leads_flow` (Prefect)
- [ ] Wire into `daily_outreach_prep_flow`

### Phase 4: Tiered Enrichment (2 hours)
- [ ] Create `calculate_data_completeness(lead_data)` function
- [ ] Create `should_use_sdk_enrichment()` with new triggers
- [ ] Update `enrichment_flow.py` to use tiered approach

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
