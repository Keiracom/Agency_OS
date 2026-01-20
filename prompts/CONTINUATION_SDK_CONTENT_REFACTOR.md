# Continuation Prompt: SDK & Content Architecture + Automated Distribution

**STATUS:**
- ✅ SDK & Content Architecture (Phases 1-4) COMPLETE
- 🔴 Automated Distribution (Phase 25) PENDING

---

## SDK & Content Architecture (Complete)

See `docs/architecture/SDK_AND_CONTENT_ARCHITECTURE.md` for full audit.

### Summary of What Was Built

### Phase 1: Clean Up ✅
- Deleted `ab_test_service.py`
- Created migration 040 (drops A/B tables, keeps tracking columns)
- Simplified `generate_email_with_sdk()` to delegate to `generate_email()`
- Simplified `generate_voice_kb()` to use Smart Prompt

### Phase 2: Smart Prompt System ✅
- Created `src/engines/smart_prompts.py`:
  - `build_full_lead_context()` - comprehensive lead data builder
  - `build_full_pool_lead_context()` - pool lead data builder
  - `build_client_proof_points()` - client intelligence builder
  - `SMART_EMAIL_PROMPT` and `SMART_VOICE_KB_PROMPT` templates
- Updated content.py and voice.py to use Smart Prompts
- Tests passing (14/14)

### Phase 3: Data Freshness ✅
- Created `src/orchestration/flows/stale_lead_refresh_flow.py`:
  - `get_stale_leads_for_outreach_task()` - finds leads with stale data (>7 days)
  - `refresh_lead_linkedin_data_task()` - refreshes via Apify (~$0.02/lead)
  - `refresh_stale_leads_flow()` - batch refresh flow
  - `daily_outreach_prep_flow()` - runs before daily outreach

### Phase 4: Tiered Enrichment ✅
- Updated `src/agents/sdk_agents/sdk_eligibility.py`:
  - `calculate_data_completeness()` - weighted scoring (0.0-1.0)
  - `is_executive_title()` - checks executive titles
  - Updated `should_use_sdk_enrichment()` with 4 triggers:
    - Sparse data (completeness < 50%)
    - Enterprise company (500+ employees)
    - Executive title (CEO, Founder, VP, Director)
    - Recently funded (< 90 days)

### Phase 5: Audit ✅
- All imports verified working
- All tests passing
- No orphaned code
- Architecture doc updated with full audit summary

## Key Files

| File | Status |
|------|--------|
| `src/engines/smart_prompts.py` | ✅ Created |
| `src/engines/content.py` | ✅ Updated |
| `src/engines/voice.py` | ✅ Updated |
| `src/orchestration/flows/stale_lead_refresh_flow.py` | ✅ Created |
| `src/agents/sdk_agents/sdk_eligibility.py` | ✅ Updated |
| `supabase/migrations/040_drop_ab_testing.sql` | ✅ Created |

## Next Steps for SDK Architecture

1. Run migration 040 in production when ready
2. Schedule `daily_outreach_prep_flow` to run early morning
3. Monitor SDK cost tracking via `sdk_usage_service.py`

---

## Automated Distribution (Phase 25) - PENDING

**Principle:** Agency OS is AUTOMATED. Users configure WHAT to target, not HOW to reach them.

### Context

User insight: "Agency OS is sold as automated. Users shouldn't configure email timing, voice timing, or sequences manually."

Currently user-configurable (WRONG):
- `campaign_sequences.delay_days` - delay between steps
- `campaign_sequences.channel` - what channel per step
- `campaign.work_hours_start/end` - when to send
- `campaign.sequence_steps` - how many steps

### Tasks Remaining

| Task | Status | File |
|------|--------|------|
| Document defaults spec | ✅ | `docs/architecture/AUTOMATED_DISTRIBUTION_DEFAULTS.md` |
| Create sequence_generator.py | 🔴 | `src/services/sequence_generator.py` |
| Implement gradual warmup | 🔴 | `src/engines/email.py` |
| Add timezone detection | 🔴 | `src/engines/scout.py` |
| Remove user sequence config | 🔴 | Frontend simplification |

### Default Sequence (System-Controlled)

| Step | Day | Channel | Logic |
|------|-----|---------|-------|
| 1 | 0 | Email | Initial outreach |
| 2 | 3 | Voice | Follow-up call |
| 3 | 5 | LinkedIn | Connection request |
| 4 | 8 | Email | Value-add touchpoint |
| 5 | 12 | SMS | Final nudge |

### Gradual Warmup Schedule

| Day | Daily Limit |
|-----|-------------|
| 1-3 | 5 |
| 4-7 | 10 |
| 8-14 | 20 |
| 15-21 | 35 |
| 22+ | 50 |

### Timing Defaults

- Send window: 9-11 AM recipient timezone
- Days: Monday-Friday only
- Timezone: Detect from company HQ location

### Implementation Order

1. Create `src/services/sequence_generator.py` (auto-generates default sequence)
2. Update campaign creation API to use auto-generation
3. Add warmup logic to email engine
4. Add timezone detection to enrichment
5. Simplify frontend campaign form

### Key Files to Read

- `docs/architecture/AUTOMATED_DISTRIBUTION_DEFAULTS.md` - Full spec
- `src/models/campaign.py` - Current model (lines 160-188 have user-configurable fields)
- `src/engines/timing.py` - Existing timing engine (good foundation)
- `src/engines/email.py` - Where to add warmup logic

---

**END OF PROMPT**
