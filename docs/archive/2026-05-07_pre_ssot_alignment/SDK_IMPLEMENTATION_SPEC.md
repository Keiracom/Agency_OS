# SDK Implementation Specification

**Status:** Planned
**Approved By:** CEO
**Date:** January 19, 2026

---

## What is SDK?

SDK (Claude Agent SDK) is Claude with tools in a multi-turn loop. It is NOT a replacement for Claude — it IS Claude, used in agent mode.

| Mode | Model | Turns | Tools | Cost |
|------|-------|-------|-------|------|
| Standard | Haiku | 1 | None | $0.03-0.20 |
| Agent SDK | Sonnet | 3-10 | web_search, web_fetch | $1.00-2.00 |

---

## Data Access

**Both Standard Claude and SDK have access to:**
- Apollo enrichment data
- LinkedIn personal profile scrape
- LinkedIn company profile scrape

**SDK adds:**
- Real-time web search (funding, news, announcements)
- URL fetching (careers pages, press releases)
- Multi-turn reasoning (Claude decides what to research)

---

## Implementation Model (Approved)

### SDK Enrichment — SELECTIVE

Fires only for Hot leads (ALS 85+) WITH priority signals.

**Priority Signals (any ONE qualifies):**
- Recent funding (< 90 days)
- Actively hiring (3+ roles)
- Tech stack match > 80%
- LinkedIn engagement > 70
- Referral source
- Employee count 50-500

**Expected coverage:** ~20% of Hot leads

### SDK Email — ALL HOT

Fires for ALL Hot leads (ALS 85+), regardless of signals.

**Expected coverage:** 100% of Hot leads (10% of total)

### SDK Voice KB — ALL HOT

Fires for ALL Hot leads (ALS 85+), regardless of signals.

**Expected coverage:** 100% of Hot leads (10% of total)

---

## Lead Flow

```
Lead Assigned
    │
    ├── LinkedIn Scrape (ALL leads)
    │
    ├── ALS Scoring
    │       │
    │       ├── Cold/Cool/Warm (ALS < 85)
    │       │       │
    │       │       └── Standard Claude (Haiku)
    │       │           • Uses scraped data only
    │       │           • Single API call
    │       │
    │       └── Hot (ALS 85+)
    │               │
    │               ├── Enrichment
    │               │       │
    │               │       ├── Has signals? → SDK Agent
    │               │       └── No signals? → Standard Claude
    │               │
    │               ├── Email → SDK Agent (ALL Hot)
    │               │
    │               └── Voice KB → SDK Agent (ALL Hot)
```

---

## Files to Create/Modify

| File | Change |
|------|--------|
| `src/agents/sdk_agents/sdk_eligibility.py` | New — `should_use_sdk_brain()` |
| `src/integrations/sdk_brain.py` | New — Agent SDK wrapper |
| `src/engines/scout.py` | Modify — Add SDK enrichment path |
| `src/engines/content.py` | Modify — Add SDK email path |
| `src/engines/voice.py` | Modify — Add SDK voice KB path |

---

## Cost Summary (per Velocity Tier customer)

| Component | Leads | Cost |
|-----------|-------|------|
| SDK Enrichment | 45 (20% of Hot) | $54 |
| SDK Email | 225 (all Hot) | $56 |
| SDK Voice KB | 225 (all Hot) | $403 |
| **Total SDK** | | **$513/month** |

---

## Quality Comparison

### Email Output

| Aspect | Standard Claude | SDK Agent |
|--------|-----------------|-----------|
| Data source | Scraped only | Scraped + real-time web |
| Personalization | Name, title, LinkedIn posts | + funding amounts, job openings, news |
| Expected reply rate | 3-5% | 8-12% |

### Voice KB Output

| Aspect | Standard Claude | SDK Agent |
|--------|-----------------|-----------|
| Objection handling | Generic scripts | Company-specific responses |
| Competitor intel | None | Researched |
| Conversation context | Basic | Funding, hiring, recent news |

---

## Testing Checklist

- [ ] `should_use_sdk_brain()` correctly identifies signal-eligible leads
- [ ] SDK Enrichment fires ONLY for Hot + signals
- [ ] SDK Email fires for ALL Hot leads
- [ ] SDK Voice KB fires for ALL Hot leads
- [ ] Standard Claude handles all non-Hot leads unchanged
- [ ] SDK cost logged to `sdk_usage_log` table
- [ ] Fallback to Standard Claude when SDK fails
- [ ] Budget safeguard prevents runaway costs (optional)

---

## Related Documents

| Document | Location |
|----------|----------|
| Full P&L Model | `docs/finance/SDK_FINAL_PL_MODEL.md` |
| Option C (Selective Usage) | `docs/finance/SDK_OPTION_C_SELECTIVE_USAGE.md` |
| Executive Summary | `docs/finance/SDK_MARGIN_ANALYSIS_EXECUTIVE_SUMMARY.md` |

---

**Prepared by:** CTO Office
**Date:** January 19, 2026
