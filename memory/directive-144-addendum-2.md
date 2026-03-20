# Directive #144 Addendum 2 — Size Filter Fix

**Date:** 2026-03-01
**Status:** Approved by CEO

## CEO Decisions

### 1. Move Size Filter Gate to Post-T1.5
- Size filtering happens IMMEDIATELY after T1.5 returns (before deeper tiers)
- NOT at allocation time anymore
- T1.5 fires for ALL ICP category passes (no proxy signals)

### 2. HELD Status for Missing Employee Count
Leads where T1.5 returns NO employee count:
- Status: `HELD`
- Reason: "No company size data — LinkedIn profile incomplete"
- Do NOT pass through silently
- Retain in DB for manual review, do NOT enter campaigns

### 3. Remove Old Size Filtering
- DELETE size filtering from `lead_allocator_service.py:110-115`
- Size constraints now enforced at post-T1.5 gate

### 4. Campaign Size Constraints
- Set during onboarding (e.g., 5-50 staff)
- Enforced at post-T1.5 gate, NOT at allocation

## Implementation Pattern

In siege_waterfall.py or waterfall_v2.py, after T1.5 tier:

```python
# Post-T1.5 Size Gate
employee_count = linkedin_data.get("company_size") or linkedin_data.get("employee_count")
if not employee_count:
    lead.status = "HELD"
    lead.hold_reason = "No company size data — LinkedIn profile incomplete"
    # Skip remaining tiers, do not enter campaign
    return lead

# Check against campaign size constraints
if not self._check_size_constraints(employee_count, campaign.icp_criteria):
    lead.status = "HELD"
    lead.hold_reason = f"Company size {employee_count} outside campaign range"
    return lead
```

## Governance
- LAW I-A: Cat `lead_allocator_service.py` before removing lines 110-115
- Include in `feature/siege-waterfall-v3` branch (no separate PR)
