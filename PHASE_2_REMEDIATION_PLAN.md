# Phase 2 Remediation Plan

**Created:** 2026-02-09
**Governance:** CEO Directive #003, LAW I-A, LAW III, LAW V
**Status:** APPROVED FOR IMPLEMENTATION

---

## Executive Summary

Three cleanup categories identified:
1. **Apollo P0** — Broken imports causing runtime failures (CRITICAL)
2. **Proxycurl Cleanup** — Dead integration needs graceful skip
3. **Smart Prompts Resilience** — Audit passed, enhancement recommended

---

## 1. Apollo P0 Fix (Session A - Priority CRITICAL)

### Problem
`apollo.py` was deleted but imports remain in 4 files. Any execution of these files will fail with `ImportError`.

### Files to Modify

| File | Lines to Remove | Scope |
|------|-----------------|-------|
| `src/engines/scout.py` | 55, 112-148, 209-219, 357-365, 399-514, 1046-1095, 1112-1411, 1675 | Remove ApolloClient, apollo property, all apollo.* calls |
| `src/engines/icp_scraper.py` | 56, 81, 180-224, 681-710, 835-990, 1388-1468, 1758 | Remove ApolloClient, apollo property, all apollo.* calls |
| `src/orchestration/flows/pool_population_flow.py` | 271, 273, 332-334, 459-468, 495-539, 676, 778-796 | Remove Apollo tasks, Apollo search calls |
| `src/orchestration/flows/post_onboarding_flow.py` | 194-201, 446, 541 | Remove source_leads_from_apollo_task |

### Action
**DELETE** all Apollo references. Do not stub. Siege Waterfall is now the SSOT for enrichment.

### Governance Trace
```
[Rule: CEO Directive #003] → [Action: Remove Apollo] → [Rationale: apollo.py deleted, imports broken]
```

---

## 2. Proxycurl Cleanup (Phase 2 Scope)

### Problem
Proxycurl shut down July 2025 (LinkedIn lawsuit). Integration is dead but still referenced.

### Files to Modify

| File | Line Numbers | Action |
|------|--------------|--------|
| `src/integrations/proxycurl.py` | ALL | **DELETE ENTIRE FILE** |
| `src/integrations/siege_waterfall.py` | 10, 24, 103, 112, 417-508, 563-588, 703 | Replace Tier 4 with graceful skip |
| `src/engines/identity_escalation.py` | 16, 81, 205-221, 407-408, 592-613, 825-833 | Remove proxycurl_client parameter |
| `src/engines/scout.py` | 408 | Remove Proxycurl cost comment |
| `src/engines/icp_scraper.py` | 901 | Remove PROXYCURL tier skip |
| `SIEGE_WATERFALL_IMPLEMENTATION.md` | 176 | Update documentation |
| `AUDIT_REPORT_2026-02-05.md` | 107, 200, 237, 303 | Update audit notes |

### Tier 4 Graceful Skip Implementation

Replace `ProxycurlClientAdapter` in siege_waterfall.py with:

```python
class BDLinkedInEnrichmentAdapter:
    """
    Tier 4: LinkedIn Intelligence via Bright Data LinkedIn Profile
    
    Note: Proxycurl deprecated July 2025 (LinkedIn lawsuit).
    v3 uses BD LinkedIn Profile (gd_l1viktl72bvl7bjuj0) for DM tiers.
    
    Will provide:
    - Profile data via get_profile()
    - Recent posts via get_user_posts()
    """
    
    async def enrich_from_linkedin(
        self,
        linkedin_url: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Skip Tier 4 until BD LinkedIn activated."""
        logger.info(
            "[Tier4] LinkedIn enrichment pending — BD LinkedIn not activated. "
            "Skipping gracefully."
        )
        return {
            "found": False,
            "source": "tier4_pending",
            "reason": "BD LinkedIn enrichment not yet activated",
        }
```

### Governance Trace
```
[Rule: CEO Directive #003] → [Action: Graceful skip] → [Rationale: Proxycurl dead, BD LinkedIn pending]
```

---

## 3. Smart Prompts Audit Result

### Question
> If sdk_research.recent_activity, sdk_research.icebreakers, and person.linkedin_headline are all empty/null, does the prompt degrade gracefully? Or does it break?

### Answer: ✅ DEGRADES GRACEFULLY

**Evidence from smart_prompts.py:**

1. **`generate_priority_guidance()`** (line ~817):
```python
if not high_priority:
    return (
        "No high-priority personalization fields available. "
        "Focus on industry/title relevance."
    )
```

2. **`format_lead_context_for_prompt()`** (line ~870+):
   - Only includes fields that have values
   - Empty sections are simply omitted
   - Falls back to MEDIUM priority (title, industry, company size)
   - Then LOW priority (name, company name)

### Current Fallback Path
```
LinkedIn data empty → Check signals (funding, hiring, new_in_role)
Signals empty → Use title/industry/company size
Title empty → Use company name only
```

### Gap Identified
GMB data (Tier 2) is **NOT used** for personalization fallback. Available GMB fields:
- `rating` / `review_count`
- `category`
- `website`
- `google_maps_url`

### Enhancement Recommended (Not Blocking)

Add GMB-based personalization to `format_lead_context_for_prompt()`:

```python
# --- GMB FALLBACK (when LinkedIn data unavailable) ---
gmb = context.get("gmb", {})
if gmb.get("rating") and gmb.get("review_count"):
    medium_lines.append(
        f"**Google Rating:** {gmb['rating']}/5 ({gmb['review_count']} reviews)"
    )
if gmb.get("category"):
    medium_lines.append(f"**Business Category:** {gmb['category']}")
```

This allows icebreakers like:
> "Noticed your 4.8 rating on Google — clearly your clients love working with you."

---

## Implementation Order

| Priority | Task | Estimated Lines | Owner |
|----------|------|-----------------|-------|
| P0 | Apollo removal (4 files) | ~150 deletions | Sub-agent |
| P1 | Proxycurl graceful skip | ~30 changes | Sub-agent |
| P2 | proxycurl.py deletion | 1 file delete | Manual |
| P3 | Smart Prompts GMB fallback | ~20 additions | Sub-agent |
| P4 | Documentation updates | ~10 changes | Manual |

---

## Verification Checklist

After implementation:
- [ ] `pytest tests/test_engines/test_scout.py` passes
- [ ] `pytest tests/test_engines/test_scraper_waterfall.py` passes
- [ ] `python -c "from src.engines.scout import ScoutEngine"` succeeds
- [ ] `python -c "from src.engines.icp_scraper import ICPScraperEngine"` succeeds
- [ ] Tier 4 logs "pending — BD LinkedIn not activated" and returns found=False
- [ ] Smart Prompts with empty LinkedIn data produces valid output

---

## Governance Sign-off

**CEO Approval Required:** ✅ (per CEO Directive #003)
**LAW V Compliance:** Sub-agents assigned for >50 line tasks
**LAW III Trace:** All commits include governance trace in message

---

*Document created by Elliot (CTO) — 2026-02-09*
