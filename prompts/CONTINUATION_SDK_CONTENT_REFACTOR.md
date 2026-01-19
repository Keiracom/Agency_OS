# Continuation Prompt: SDK & Content Architecture Refactor

**Copy everything below this line into a new Claude Code session:**

---

## Context

Read `docs/architecture/SDK_AND_CONTENT_ARCHITECTURE.md` first. This contains decisions made on 2026-01-20 about how SDK agents, enrichment, and content generation should work.

## Summary of Decisions

1. **SDK is for reasoning, not scraping** — Use Apify for data refresh, SDK only for reply handling and meeting prep
2. **Smart Prompt replaces templates** — Use all DB data for email generation, not SDK
3. **Tiered SDK enrichment** — SDK only for sparse/executive/enterprise/funded leads
4. **Remove A/B testing** — Moot for unique SDK-generated emails
5. **Just-in-time Apify refresh** — Re-scrape stale leads before batch send

## What's Done

- ✅ SDK cost tracking (`src/services/sdk_usage_service.py`)
- ✅ JIT validator fix (queries `lead_pool` not `lead_assignments`)
- ✅ Dropped orphaned suppression tables (migration 039)

## What Needs to Be Built

### Phase 1: Clean Up (1 hour)
- [ ] Remove A/B testing tables + `ab_test_service.py`
- [ ] Remove SDK calls from `content.generate_email_with_sdk()`
- [ ] Remove SDK calls from `voice.generate_voice_kb()`

### Phase 2: Smart Prompt System (4 hours)
- [ ] Create `build_full_lead_context(db, lead_id)` function
- [ ] Create `SMART_EMAIL_PROMPT` template
- [ ] Replace template path in content engine

### Phase 3: Data Freshness (3 hours)
- [ ] Create `refresh_stale_leads_flow` (Prefect)
- [ ] Wire into daily outreach prep

### Phase 4: Tiered Enrichment (2 hours)
- [ ] Update `should_use_sdk_enrichment()` with new triggers
- [ ] Update enrichment flow

## Instructions

1. Read the architecture doc: `docs/architecture/SDK_AND_CONTENT_ARCHITECTURE.md`
2. Check what's already done by reviewing recent commits
3. Continue with the next uncompleted phase
4. Pause after each phase for approval before continuing
5. Commit after each phase

## Key Files

| File | Purpose |
|------|---------|
| `src/engines/content.py` | Email generation — needs Smart Prompt |
| `src/engines/voice.py` | Voice KB — needs Smart Prompt |
| `src/engines/scout.py` | Enrichment — needs tiered SDK |
| `src/services/ab_test_service.py` | DELETE this |
| `src/services/sdk_usage_service.py` | Cost tracking (already built) |

## Commands to Start

```bash
# Check recent commits
git log --oneline -10

# See current state
git status

# Read the architecture doc
cat docs/architecture/SDK_AND_CONTENT_ARCHITECTURE.md
```

Start with Phase 1 (Clean Up) unless told otherwise.

---

**END OF PROMPT**
