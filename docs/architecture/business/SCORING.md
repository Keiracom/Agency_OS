# Scoring Architecture — ALS & Channel Access

**Purpose:** Define ALS (Agency Lead Score) calculation and channel access rules.
**Status:** SPEC COMPLETE
**Code Status:** PARTIAL - scoring implemented, channel enforcement has gaps

---

## 1. ALS Overview

**ALS (Agency Lead Score)** is a 0-100 score that determines:
1. Lead quality/priority
2. Which outreach channels can be used
3. Whether to use SDK enrichment (Hot leads only)

---

## 2. ALS Formula (5 Components, 100 points max)

**Source:** `docs/specs/engines/SCORER_ENGINE.md`

| Component | Max Points | Weight | Description |
|-----------|------------|--------|-------------|
| Data Quality | 20 | 0.15 | Contact completeness |
| Authority | 25 | 0.30 | Decision-making power |
| Company Fit | 25 | 0.25 | ICP alignment + SEO signals |
| Timing | 15 | 0.20 | Intent/urgency signals |
| Risk | 15 | 0.10 | Negative indicators (deductions) |

---

## 3. ALS Tier Thresholds

**Source of Truth:** `src/config/tiers.py` lines 131-159

| ALS Score | Tier Name | Description |
|-----------|-----------|-------------|
| **85-100** | Hot | Highest priority, all channels |
| **60-84** | Warm | Good fit, most channels |
| **35-59** | Cool | Moderate fit, limited channels |
| **20-34** | Cold | Low fit, email only |
| **<20** | Dead | Suppress - do not contact |

**CRITICAL:** Hot threshold is **85**, not 80. This is a common mistake.

---

## 4. Channel Access by ALS Tier

**Source of Truth:** `src/config/tiers.py` `CHANNEL_ACCESS_BY_ALS`

| Tier | Email | LinkedIn | Voice | SMS | Direct Mail |
|------|-------|----------|-------|-----|-------------|
| Hot (85+) | Yes | Yes | Yes | Yes | Yes |
| Warm (60-84) | Yes | Yes | Yes | No | No |
| Cool (35-59) | Yes | Yes | No | No | No |
| Cold (20-34) | Yes | No | No | No | No |
| Dead (<20) | No | No | No | No | No |

### Rationale

- **SMS/Mail = Hot only**: These channels are expensive and intrusive; reserve for highest-quality leads
- **Voice = Warm+**: Phone calls are time-intensive; prioritize warmer leads
- **LinkedIn = Cool+**: LinkedIn has strict rate limits; use on better-fit leads
- **Email = Cold+**: Email is cheapest; acceptable for lower-quality leads
- **Dead = Suppress**: Too low quality; would damage deliverability

---

## 5. Channel Access Enforcement

### Where Enforcement MUST Happen

| Stage | Purpose | Code Location | Status |
|-------|---------|---------------|--------|
| **Allocation** | Assign only eligible channels | `enrichment_flow.py:allocate_channels_for_lead_task` | IMPLEMENTED |
| **Execution** | Verify before send | `outreach_flow.py` send tasks | GAP |

### Current Implementation (Allocation Time)

In `src/orchestration/flows/enrichment_flow.py` lines 307-330:

```python
tier_channel_map = {
    "hot": [EMAIL, SMS, LINKEDIN, VOICE, MAIL],
    "warm": [EMAIL, LINKEDIN, VOICE],
    "cool": [EMAIL, LINKEDIN],
    "cold": [EMAIL],
    "dead": [],
}
available_channels = tier_channel_map.get(als_tier.lower(), [])
```

**Issue:** This is a HARDCODED duplicate. Should use `get_available_channels()` from `tiers.py`.

### GAP: Execution Time Verification

The `outreach_flow.py` does NOT verify ALS score before sending. This is a safety issue.

**Required Fix:** Add ALS check before SMS/Voice sends:

```python
# In send_sms_outreach_task and send_voice_outreach_task
from src.config.tiers import get_available_channels

lead = await db.get(Lead, lead_uuid)
allowed_channels = get_available_channels(lead.als_score)

if "sms" not in allowed_channels:
    return {"success": False, "error": f"ALS {lead.als_score} not eligible for SMS"}
```

---

## 6. SDK Eligibility

**Rule:** SDK enrichment is only used for HOT leads (ALS 85+).

**Source:** `src/agents/sdk_agents/sdk_eligibility.py`

```python
def should_use_sdk_email(lead_data: dict) -> bool:
    """SDK email for Hot leads only."""
    return lead_data.get("als_score", 0) >= 85

def should_use_sdk_voice_kb(lead_data: dict) -> bool:
    """SDK voice KB for Hot leads only."""
    return lead_data.get("als_score", 0) >= 85
```

**Why:** SDK calls are expensive (~$0.05-0.15 per lead). Only worth it for leads likely to convert.

---

## 7. Code Locations

| Component | Location | Status |
|-----------|----------|--------|
| ALS tier thresholds | `src/config/tiers.py:ALS_TIER_THRESHOLDS` | IMPLEMENTED |
| Channel access map | `src/config/tiers.py:CHANNEL_ACCESS_BY_ALS` | IMPLEMENTED |
| `get_als_tier()` | `src/config/tiers.py:148` | IMPLEMENTED |
| `get_available_channels()` | `src/config/tiers.py:162` | IMPLEMENTED but UNUSED |
| Scorer engine | `src/engines/scorer.py` | IMPLEMENTED |
| Allocation enforcement | `src/orchestration/flows/enrichment_flow.py` | IMPLEMENTED (hardcoded) |
| Execution enforcement | `src/orchestration/flows/outreach_flow.py` | GAP |

---

## 8. Implementation Tasks

| Task | Priority | Description |
|------|----------|-------------|
| Use `get_available_channels()` in enrichment_flow | HIGH | Replace hardcoded tier_channel_map |
| Add ALS check in SMS send task | HIGH | Verify lead is Hot before SMS |
| Add ALS check in Voice send task | HIGH | Verify lead is Warm+ before Voice |
| Add ALS check in Mail send task | MEDIUM | Verify lead is Hot before Mail |

---

## 9. Verification Checklist

```
[ ] ALS_TIER_THRESHOLDS matches this spec (Hot = 85+)
[ ] CHANNEL_ACCESS_BY_ALS matches this spec
[ ] get_available_channels() is called in enrichment_flow (not hardcoded)
[ ] SMS send task checks ALS >= 85
[ ] Voice send task checks ALS >= 60
[ ] Mail send task checks ALS >= 85
[ ] Dead leads (ALS < 20) are never contacted
[ ] Tests exist for channel access enforcement
```

---

## 10. Related Documents

| Document | Relationship |
|----------|--------------|
| `docs/specs/engines/SCORER_ENGINE.md` | Detailed ALS formula |
| `docs/architecture/TIER_BILLING_ARCHITECTURE.md` | Subscription tiers |
| `docs/architecture/distribution/` | Channel-specific rules |
