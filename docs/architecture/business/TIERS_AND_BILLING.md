# Tier & Billing Architecture

**Purpose:** Define subscription tiers, lead quotas, credit system, and monthly pacing.
**Status:** SPEC COMPLETE
**Code Status:** PARTIAL - tiers defined, monthly scheduling NOT implemented

---

## 1. Subscription Tiers

**Source of Truth:** `src/config/tiers.py`

| Tier | Monthly Price (AUD) | Founding Price | Leads/Month | Max Campaigns | LinkedIn Seats | Daily Outreach |
|------|---------------------|----------------|-------------|---------------|----------------|----------------|
| Ignition | $2,500 | $1,250 | 1,250 | 5 (3 AI + 2 custom) | 1 | 50 |
| Velocity | $5,000 | $2,500 | 2,250 | 10 (6 AI + 4 custom) | 3 | 100 |
| Dominance | $7,500 | $3,750 | 4,500 | 20 (12 AI + 8 custom) | 5 | 200 |

### Key Principles

1. **Volume-based, not feature-based** - All tiers get all features
2. **Founding discount** - 50% off, locked for life if subscription maintained
3. **No rollover** - Unused leads do NOT roll over to next month

---

## 2. Credit System

### Database Fields

**Table:** `clients`

| Field | Type | Purpose |
|-------|------|---------|
| `tier` | enum | Current subscription tier |
| `credits_remaining` | integer | Leads remaining this billing period |
| `credits_reset_at` | timestamptz | When credits reset to tier quota |
| `stripe_customer_id` | text | Stripe customer for billing |
| `stripe_subscription_id` | text | Stripe subscription for renewals |

### Credit Lifecycle

```
1. Client signs up → credits_remaining = tier.leads_per_month
2. Lead sourced → credits_remaining -= 1
3. Monthly reset date reached → credits_remaining = tier.leads_per_month
4. Upgrade tier → credits_remaining += (new_quota - old_quota)
5. Downgrade tier → credits_remaining = min(current, new_quota)
```

---

## 3. Monthly Lead Scheduling

### Problem Statement

Without pacing, a client could burn through all leads in the first week, leaving no outreach for the rest of the month.

### Solution: Daily Lead Pacing

**Formula:**
```
daily_lead_target = leads_per_month / work_days_per_month
work_days_per_month = 22 (average)
```

| Tier | Leads/Month | Daily Target | With 10% Buffer |
|------|-------------|--------------|-----------------|
| Ignition | 1,250 | ~57 | ~52 |
| Velocity | 2,250 | ~102 | ~93 |
| Dominance | 4,500 | ~205 | ~186 |

### Implementation Requirements

**Scheduled Flow:** `monthly_pacing_flow.py`

```python
@flow(name="daily_lead_pacing")
async def daily_lead_pacing_flow():
    """
    Runs daily to:
    1. Check each active client's lead consumption rate
    2. Alert if burning too fast (>120% of daily target)
    3. Alert if too slow (<50% of daily target by mid-month)
    """
    pass  # TO BE IMPLEMENTED
```

**Credit Reset Flow:** `credit_reset_flow.py`

```python
@flow(name="credit_reset_check")
async def credit_reset_check_flow():
    """
    Runs hourly to:
    1. Find clients where credits_reset_at <= now()
    2. Reset credits_remaining to tier.leads_per_month
    3. Set credits_reset_at to next billing date
    4. Log reset event
    """
    pass  # TO BE IMPLEMENTED
```

---

## 4. Rate Limits by Resource

These are RESOURCE-level limits, not tier limits.

| Resource Type | Daily Limit | Per |
|---------------|-------------|-----|
| Email domain | 50 | per domain |
| LinkedIn seat | 17 | per seat |
| SMS number | 100 | per phone number |
| Voice number | 50 | per phone number |
| Direct mail | 1,000 | per account |

### Tier × Resources = Total Capacity

| Tier | LinkedIn Seats | LinkedIn Capacity/Day | Email Domains (typical) | Email Capacity/Day |
|------|----------------|----------------------|-------------------------|-------------------|
| Ignition | 1 | 17 | 1-2 | 50-100 |
| Velocity | 3 | 51 | 2-3 | 100-150 |
| Dominance | 5 | 85 | 3-5 | 150-250 |

---

## 5. 5-Step Sequence Impact on Capacity

Each lead goes through a 5-step sequence. This affects capacity planning:

**Example: Velocity Tier**
- Daily outreach limit: 100 touches
- 5-step sequence: 1 lead = 5 touches (over 12 days)
- New leads per day: ~20 to stay within 100/day

**Calculation:**
```
active_leads_in_sequence = new_leads_per_day × avg_sequence_duration_days
daily_touches = active_leads_in_sequence × (touches_per_day_per_lead)

For steady state:
new_leads_per_day = daily_outreach_limit / avg_touches_per_lead_per_day
```

---

## 6. Code Locations

| Component | Location | Status |
|-----------|----------|--------|
| Tier configuration | `src/config/tiers.py` | IMPLEMENTED |
| Client model (credits) | `src/models/client.py` | IMPLEMENTED |
| Credit deduction | `src/orchestration/flows/enrichment_flow.py` | IMPLEMENTED |
| Credit reset flow | `src/orchestration/flows/credit_reset_flow.py` | IMPLEMENTED |
| Credit reset schedule | `src/orchestration/schedules/scheduled_jobs.py` | IMPLEMENTED |
| Daily pacing flow | — | NOT IMPLEMENTED |
| Stripe webhook handler | `src/api/routes/webhooks.py` | PARTIAL |

---

## 7. Implementation Priority

| Task | Priority | Dependencies |
|------|----------|--------------|
| Credit reset flow | HIGH | None |
| Daily pacing alerts | MEDIUM | Credit reset flow |
| Stripe subscription sync | MEDIUM | Credit reset flow |
| Upgrade/downgrade handling | LOW | Stripe sync |

---

## 8. Verification Checklist

```
[ ] Tier config matches this spec
[ ] Client model has all credit fields
[ ] Credit deduction happens on lead sourcing
[ ] Credit reset flow runs hourly
[ ] Daily pacing flow runs daily
[ ] Stripe webhooks update credits on renewal
[ ] Tests exist for credit lifecycle
```
