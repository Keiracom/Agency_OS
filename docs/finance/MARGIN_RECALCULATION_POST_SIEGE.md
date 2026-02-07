# Margin Recalculation: Post-Siege + Post-SDK Deprecation

**Date:** 2026-02-06
**Context:** Original margin calculations used Apollo+Clay+SDK. Now using Siege Waterfall + Smart Prompts.
**Decision Required:** Confirm updated margins are acceptable

---

## What Changed

### Data Enrichment: Apollo+Clay → Siege Waterfall

| Old (Apollo+Clay) | New (Siege Waterfall) | Savings |
|-------------------|----------------------|---------|
| $0.43/lead | $0.105/lead | **75% reduction** |

**Per 1,000 leads:** $430 → $105 = **$325 saved**

### Content Generation: SDK → Smart Prompts (FCO-002)

| Old (SDK) | New (Smart Prompts) | Savings |
|-----------|---------------------|---------|
| $3.20/hot lead | ~$0.05/lead (API calls) | **98% reduction** |
| ~$385/mo overhead | ~$50/mo | **$335/mo saved** |

---

## Recalculated COGS Per Customer

### OLD COGS (Pre-Siege, Pre-FCO-002)

| Cost Category | Ignition (1,250 leads) | Velocity (2,250 leads) | Dominance (4,500 leads) |
|---------------|------------------------|------------------------|-------------------------|
| Data Enrichment (Apollo+Clay) | $538 | $968 | $1,935 |
| SDK Processing | $400 | $720 | $1,440 |
| Email Infrastructure | $39 | $62 | $116 |
| SMS | $10 | $18 | $36 |
| LinkedIn (HeyReach) | $122 | $366 | $610 |
| Voice AI (Vapi) | $164 | $295 | $591 |
| Direct Mail (Lob) | $122 | $220 | $441 |
| Webhooks | $8 | $12 | $23 |
| Infrastructure | $39 | $62 | $116 |
| **OLD TOTAL COGS** | **$1,442** | **$2,723** | **$5,308** |

### NEW COGS (Post-Siege, Post-FCO-002)

| Cost Category | Ignition (1,250 leads) | Velocity (2,250 leads) | Dominance (4,500 leads) |
|---------------|------------------------|------------------------|-------------------------|
| Data Enrichment (Siege) | $131 | $236 | $473 |
| Smart Prompts (API) | $50 | $75 | $100 |
| Email Infrastructure | $39 | $62 | $116 |
| SMS | $10 | $18 | $36 |
| LinkedIn (Unipile) | $79 | $158 | $316 |
| Voice AI (Vapi+Telnyx) | $100 | $180 | $360 |
| Direct Mail (Lob) | $122 | $220 | $441 |
| Webhooks | $8 | $12 | $23 |
| Infrastructure | $39 | $62 | $116 |
| **NEW TOTAL COGS** | **$578** | **$1,023** | **$1,981** |

---

## Updated Margin Analysis

### Ignition ($2,500/mo)
| Metric | Old | New |
|--------|-----|-----|
| Revenue | $2,500 | $2,500 |
| COGS | $1,442 | $578 |
| Gross Profit | $1,058 | **$1,922** |
| Gross Margin | 42.3% | **76.9%** |

### Velocity ($4,000/mo)
| Metric | Old | New |
|--------|-----|-----|
| Revenue | $4,000 | $4,000 |
| COGS | $2,723 | $1,023 |
| Gross Profit | $1,277 | **$2,977** |
| Gross Margin | 31.9% | **74.4%** |

### Dominance ($7,500/mo)
| Metric | Old | New |
|--------|-----|-----|
| Revenue | $7,500 | $7,500 |
| COGS | $5,308 | $1,981 |
| Gross Profit | $2,192 | **$5,519** |
| Gross Margin | 29.2% | **73.6%** |

---

## Summary

| Tier | Old Margin | New Margin | Change |
|------|------------|------------|--------|
| Ignition | 42.3% | **76.9%** | +34.6% |
| Velocity | 31.9% | **74.4%** | +42.5% |
| Dominance | 29.2% | **73.6%** | +44.4% |

**All tiers now exceed the 70% margin target.**

---

## Assumptions

1. Siege Waterfall fully implemented and wired
2. Smart Prompts as primary (SDK deprecated)
3. Unipile replaces HeyReach ($79 vs $122)
4. Telnyx direct reduces Voice AI costs by 40%
5. 20% of leads reach Tier 5 (Kaspr mobile enrichment)
6. **SMS extended to Warm tier (60-84)** — Decision 2026-02-06

### SMS Extension Impact (Warm Tier)

Current SMS costs assume Hot only (10% of leads).
With Warm extension (~35% of leads total), SMS costs increase ~2.5x:

| Tier | Old SMS | New SMS | Delta |
|------|---------|---------|-------|
| Ignition | $10 | $25 | +$15 |
| Velocity | $18 | $45 | +$27 |
| Dominance | $36 | $90 | +$54 |

**Revised Margins with SMS Extension:**

| Tier | Revenue | New COGS | Gross Profit | Margin |
|------|---------|----------|--------------|--------|
| Ignition | $2,500 | $593 | $1,907 | **76.3%** ✅ |
| Velocity | $4,000 | $1,050 | $2,950 | **73.8%** ✅ |
| Dominance | $7,500 | $2,035 | $5,465 | **72.9%** ✅ |

**All tiers remain above 70% target with SMS extension.**

---

## CEO Approval

| Item | Status |
|------|--------|
| Ignition margin 76.9% | ☐ Approved |
| Velocity margin 74.4% | ☐ Approved |
| Dominance margin 73.6% | ☐ Approved |
| No price increase needed | ☐ Approved |

---

*Prepared by Elliot (MD/CTO) — 2026-02-06*
*Supersedes SDK_FINAL_PL_MODEL.md margin calculations*
