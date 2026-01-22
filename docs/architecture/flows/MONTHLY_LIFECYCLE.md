# Monthly Lifecycle — Agency OS

**Purpose:** Defines recurring monthly operations — lead replenishment, campaign continuity, and CIS-informed refinement after month 1.
**Status:** SPECIFICATION
**Last Updated:** 2026-01-21

---

## Overview

After onboarding completes, Agency OS enters a **monthly cycle**:

```
Month 1 (Onboarding):
  ICP → Campaigns → Leads (tier quota) → Outreach begins

Month 2+:
  Credit Reset → Replenishment → Continued Outreach → CIS Refinement
```

Key principle: **"Set it and forget it"** — clients configure WHAT (ICP), system handles WHEN and HOW to replenish.

---

## Code Locations

| Component | File | Status |
|-----------|------|--------|
| Credit Reset Flow | `src/orchestration/flows/credit_reset_flow.py` | IMPLEMENTED |
| Monthly Replenishment Flow | `src/orchestration/flows/monthly_replenishment_flow.py` | IMPLEMENTED |
| Pool Population | `src/orchestration/flows/pool_population_flow.py` | IMPLEMENTED |
| Lead Allocator | `src/services/lead_allocator_service.py` | IMPLEMENTED |
| CIS Pattern Learning | `src/orchestration/flows/pattern_learning_flow.py` | IMPLEMENTED |
| CIS Detectors | `src/detectors/*.py` (WHO, WHAT, WHEN, HOW, Funnel) | IMPLEMENTED |
| Client Intelligence | `src/engines/client_intelligence.py` | IMPLEMENTED |
| Client Intelligence Model | `src/models/client_intelligence.py` | IMPLEMENTED |
| ICP Refinement | `src/engines/icp_refiner.py` | NOT IMPLEMENTED |
| Campaign Evolution Agents | `src/agents/campaign_evolution/` | NOT IMPLEMENTED |

---

## Monthly Cycle Timeline

| Day | Event | Flow | Action |
|-----|-------|------|--------|
| 0 | **Credit Reset** | `credit_reset_check_flow` | `credits_remaining` → tier quota |
| 0 | **Replenishment** | `monthly_replenishment_flow` | Calculate gap, source leads, assign to campaigns |
| 1-30 | **Outreach** | `outreach_flow` | Hourly sequence execution (8AM-6PM Mon-Fri) |
| 7, 14, 21, 28 | **Pattern Learning** | `pattern_learning_flow` | CIS detectors run (Sunday 3AM) |
| 30 | **Cycle Repeats** | — | Credit reset triggers next month |

---

## Lead Replenishment Flow

### Trigger

The `monthly_replenishment_flow` is triggered immediately after credit reset:

```python
# In credit_reset_flow.py, after resetting credits:
if reset_successful:
    await run_deployment(
        name="monthly_replenishment/monthly-replenishment-flow",
        parameters={"client_id": str(client_id)},
        timeout=0,
    )
```

### Gap Calculation

Smart replenishment — only source what's needed:

```python
async def calculate_lead_gap(db: AsyncSession, client_id: UUID) -> int:
    """
    Calculate how many new leads to source.

    Gap = Tier Quota - Active Pipeline

    Active Pipeline includes:
    - Leads in active sequences (not completed)
    - Leads pending outreach start
    - Excludes: converted, unsubscribed, bounced, completed-no-reply
    """
    # Get tier quota
    client = await db.get(Client, client_id)
    tier_quota = get_leads_for_tier(client.tier.value)

    # Count active pipeline
    pipeline_count = await db.scalar(
        select(func.count(Lead.id))
        .where(
            Lead.client_id == client_id,
            Lead.deleted_at.is_(None),
            Lead.status.in_([
                LeadStatus.NEW,
                LeadStatus.ENRICHED,
                LeadStatus.IN_SEQUENCE,
                LeadStatus.REPLIED,  # Still in play
            ]),
        )
    )

    gap = max(0, tier_quota - pipeline_count)
    return gap
```

### Replenishment Options

| Option | Behavior | Config |
|--------|----------|--------|
| **Full** | Source full tier quota regardless of pipeline | `replenishment_mode = "full"` |
| **Smart** (default) | Source only the gap | `replenishment_mode = "smart"` |
| **Manual** | Notify client, wait for approval | `replenishment_mode = "manual"` |

### Flow Implementation

```python
@flow(name="monthly_replenishment")
async def monthly_replenishment_flow(
    client_id: str | UUID,
    force_full: bool = False,
) -> dict[str, Any]:
    """
    Post-credit-reset lead replenishment.

    1. Calculate lead gap (or use full quota if force_full)
    2. Refine ICP using CIS patterns (if eligible)
    3. Source leads from Apollo
    4. Score leads (ALS)
    5. Assign to ACTIVE campaigns by allocation %
    6. Trigger enrichment
    """
    if isinstance(client_id, str):
        client_id = UUID(client_id)

    # Step 1: Calculate gap
    async with get_db_session() as db:
        if force_full:
            client = await db.get(Client, client_id)
            gap = get_leads_for_tier(client.tier.value)
        else:
            gap = await calculate_lead_gap(db, client_id)

    if gap <= 0:
        return {"success": True, "leads_sourced": 0, "reason": "Pipeline full"}

    # Step 2: Refine ICP (if eligible)
    icp_criteria = await get_refined_icp(client_id)

    # Step 3: Source leads
    source_result = await source_leads_task(client_id, icp_criteria, gap)

    # Step 4: Assign to campaigns
    assign_result = await assign_to_active_campaigns_task(
        client_id,
        source_result["lead_ids"],
    )

    return {
        "success": True,
        "leads_sourced": source_result["count"],
        "leads_assigned": assign_result["count"],
        "campaigns_updated": assign_result["campaigns"],
    }
```

---

## Intelligence Engines (Learning Systems)

Agency OS has two intelligence engines that continuously learn and improve:

### 1. Conversion Intelligence System (CIS)

**Purpose:** Learn what converts — which leads, content, timing, and channels work best.

| Detector | Learns | Informs |
|----------|--------|---------|
| **WHO** | Which lead attributes convert (titles, industries, company size) | ICP refinement for sourcing |
| **WHAT** | Which content resonates (subjects, pain points, CTAs) | Smart Prompt templates |
| **WHEN** | Which timing works (days, hours, sequence gaps) | Send scheduling |
| **HOW** | Which channels perform (email vs voice vs LinkedIn) | Channel allocation |
| **Funnel** | Downstream outcomes (show rates, win rates) | Deal pipeline optimization |

**Schedule:** Weekly (Sunday 3AM)
**Code:** `src/detectors/`, `pattern_learning_flow.py`

### 2. Client Intelligence Engine

**Purpose:** Learn about the client's business for SDK personalization.

| Source | Data Collected | Used For |
|--------|---------------|----------|
| Website | Case studies, services, testimonials | Proof points in outreach |
| LinkedIn | Company info, specialties, employee count | Authority signals |
| Trustpilot/G2 | Ratings, reviews, customer feedback | Social proof |
| Twitter/Facebook/Instagram | Social presence, recent posts | Engagement context |

**Schedule:** On-demand (onboarding) + periodic refresh
**Code:** `src/engines/client_intelligence.py`, `ClientIntelligence` model

### How Intelligence Feeds Month 2+

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LOOP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐        ┌───────────────┐                    │
│  │    CIS        │        │   Client      │                    │
│  │  (Conversion) │        │ Intelligence  │                    │
│  └───────┬───────┘        └───────┬───────┘                    │
│          │                        │                             │
│          │ WHO patterns          │ Proof points                │
│          │ WHAT patterns         │ Testimonials                │
│          │ WHEN patterns         │ Case studies                │
│          │ HOW patterns          │ Social proof                │
│          │                        │                             │
│          └────────────┬───────────┘                            │
│                       ▼                                         │
│          ┌────────────────────────┐                            │
│          │   Month 2+ Decisions   │                            │
│          ├────────────────────────┤                            │
│          │ • ICP refinement       │ ← WHO patterns             │
│          │ • Content optimization │ ← WHAT + Client Intel      │
│          │ • Timing optimization  │ ← WHEN patterns            │
│          │ • Channel rebalancing  │ ← HOW patterns             │
│          │ • Campaign evolution   │ ← All patterns             │
│          └────────────────────────┘                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## CIS-Informed ICP Refinement

### Eligibility

CIS refinement activates when client has:
- **Minimum 20 conversions** (configured in `scheduled_jobs.py`, default `min_sample_size=30` in detector base)
- **At least 2 months** of data
- WHO detector patterns with **confidence > 0.7**

### How CIS Calculates Patterns

CIS detectors analyze **ALL leads** (converted AND non-converted):

```python
# From src/detectors/base.py - conversion_rate_by()
for item in items:
    stats[key]["total"] += 1        # Counts ALL leads
    if is_converted_fn(item):
        stats[key]["converted"] += 1  # Only conversions

rate = segment_stats["converted"] / segment_stats["total"]
```

**Key insight:** Non-conversions are essential — they form the denominator. Without tracking failures, you can't calculate meaningful conversion rates.

Example: 100 Tech leads → 10 convert = 10% rate. 50 Finance leads → 8 convert = 16% rate. Finance is better despite fewer absolute conversions.

### Refinement Logic

```python
async def get_refined_icp(client_id: UUID) -> dict[str, Any]:
    """
    Get ICP criteria, refined by CIS WHO patterns if eligible.

    Returns base ICP if not eligible for refinement.
    """
    async with get_db_session() as db:
        # Get base ICP
        client = await db.get(Client, client_id)
        base_icp = {
            "industries": client.icp_industries or [],
            "titles": client.icp_titles or [],
            "company_sizes": client.icp_company_sizes or [],
            "locations": client.icp_locations or [],
        }

        # Check eligibility
        conversion_count = await count_conversions(db, client_id)
        if conversion_count < 20:
            return base_icp

        # Get WHO patterns
        who_patterns = await get_who_patterns(db, client_id)
        if not who_patterns or who_patterns.confidence < 0.7:
            return base_icp

        # Apply refinements
        refined_icp = apply_who_refinements(base_icp, who_patterns)
        return refined_icp


def apply_who_refinements(
    base_icp: dict,
    who_patterns: ConversionPattern,
) -> dict:
    """
    Apply WHO detector insights to ICP.

    Example: If CTOs convert 2x better than VPs,
    prioritize CTO in Apollo search.
    """
    refined = base_icp.copy()

    # Reorder titles by conversion rate
    if who_patterns.pattern_data.get("title_conversion_rates"):
        rates = who_patterns.pattern_data["title_conversion_rates"]
        refined["titles"] = sorted(
            base_icp["titles"],
            key=lambda t: rates.get(t, 0),
            reverse=True,
        )

    # Similar for industries, company sizes
    # ...

    return refined
```

### Pattern → ICP Mapping

| WHO Pattern | ICP Refinement |
|-------------|----------------|
| `title_conversion_rates` | Reorder titles by conversion rate |
| `industry_lift` | Prioritize high-lift industries |
| `company_size_sweet_spot` | Narrow company size range |
| `seniority_authority` | Adjust seniority targeting |
| `timing_signals` | Add "recently funded" filter |

---

## Campaign Continuity

### Status Behavior

| Status | Receives New Leads | Outreach Active |
|--------|-------------------|-----------------|
| `DRAFT` | No | No |
| `ACTIVE` | **Yes** | **Yes** |
| `PAUSED` | No | No |
| `COMPLETED` | No | No |

### Lead Distribution

New leads assigned to ACTIVE campaigns proportionally:

```python
async def assign_to_active_campaigns_task(
    client_id: UUID,
    lead_ids: list[UUID],
) -> dict[str, Any]:
    """
    Assign leads to ACTIVE campaigns by allocation percentage.
    """
    async with get_db_session() as db:
        # Get ACTIVE campaigns with allocations
        campaigns = await db.execute(
            select(Campaign)
            .where(
                Campaign.client_id == client_id,
                Campaign.status == CampaignStatus.ACTIVE,
                Campaign.deleted_at.is_(None),
            )
        )
        active_campaigns = campaigns.scalars().all()

        if not active_campaigns:
            return {"count": 0, "campaigns": [], "error": "No active campaigns"}

        # Calculate leads per campaign
        total_leads = len(lead_ids)
        assignments = []

        for campaign in active_campaigns:
            pct = campaign.lead_allocation_pct or 0
            count = int(total_leads * pct / 100)

            if count > 0:
                # Assign leads
                leads_for_campaign = lead_ids[:count]
                lead_ids = lead_ids[count:]

                await allocator.assign_leads(
                    lead_ids=leads_for_campaign,
                    campaign_id=campaign.id,
                )

                assignments.append({
                    "campaign_id": str(campaign.id),
                    "campaign_name": campaign.name,
                    "leads_assigned": count,
                })

        return {
            "count": sum(a["leads_assigned"] for a in assignments),
            "campaigns": assignments,
        }
```

### No Active Campaigns

If all campaigns are DRAFT/PAUSED/COMPLETED:
- Leads are sourced but **not assigned**
- Leads remain in pool with `campaign_id = NULL`
- Client notified to activate a campaign

---

## Lead Lifecycle States

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    ▼                                      │
┌─────┐  enrich  ┌──────────┐  start   ┌────────────┐     │
│ NEW │─────────►│ ENRICHED │─────────►│ IN_SEQUENCE│     │
└─────┘          └──────────┘          └─────┬──────┘     │
                                             │            │
                      ┌──────────────────────┼────────────┤
                      │                      │            │
                      ▼                      ▼            │
                ┌──────────┐          ┌──────────┐        │
                │ REPLIED  │          │COMPLETED │        │
                └────┬─────┘          └────┬─────┘        │
                     │                     │              │
         ┌───────────┼───────────┐         │              │
         ▼           ▼           ▼         ▼              │
   ┌──────────┐ ┌─────────┐ ┌────────┐ ┌────────┐         │
   │ MEETING  │ │   NOT   │ │  OOO   │ │ARCHIVED│─────────┘
   │ _BOOKED  │ │INTERESTED│ │        │ │        │ re-engage
   └────┬─────┘ └─────────┘ └────────┘ └────────┘
        │
        ▼
   ┌──────────┐
   │CONVERTED │ (terminal)
   └──────────┘
```

### Conversion Tracking

**How does a lead become CONVERTED?**

| File | Trigger | When |
|------|---------|------|
| `src/engines/closer.py` | Reply classified as "interested" + meeting booked | Email reply handling |
| `src/engines/voice.py` | Call outcome = `meeting_booked` or `positive_outcome` | Voice call completion |
| `src/services/deal_service.py` | Deal created in CRM (HubSpot, Pipedrive, Close) | Manual or auto-deal creation |

**Code example (closer.py):**
```python
# When reply indicates meeting was booked
if reply_intent == ReplyIntent.INTERESTED and meeting_booked:
    lead.status = LeadStatus.CONVERTED
    await db.commit()
```

**What CIS tracks for pattern learning:**
- `CONVERTED` = positive outcome (success)
- `NOT_INTERESTED`, `BOUNCED`, `UNSUBSCRIBED` = negative outcomes (failure)
- `IN_SEQUENCE`, `REPLIED` = still in progress (excluded from rate calculations)

### Carryover Rules

| State | Month 2 Behavior |
|-------|------------------|
| `NEW` | Continue — awaiting enrichment |
| `ENRICHED` | Continue — awaiting sequence start |
| `IN_SEQUENCE` | Continue — sequence proceeds |
| `REPLIED` | Continue — pending follow-up |
| `MEETING_BOOKED` | Continue — pending meeting |
| `CONVERTED` | Complete — no action |
| `NOT_INTERESTED` | Archive — remove from pipeline count |
| `ARCHIVED` | Archive — can be re-engaged if strategy changes |
| `COMPLETED` (no reply) | Archive — sequence exhausted |

---

## Configuration

### Client-Level Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `replenishment_mode` | enum | `smart` | `full`, `smart`, or `manual` |
| `auto_replenish` | bool | `TRUE` | Auto-source after credit reset |
| `cis_refinement_enabled` | bool | `TRUE` | Use CIS patterns for ICP |
| `min_pipeline_alert` | int | 100 | Alert if pipeline drops below |

### Platform-Level Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Min conversions for CIS | 20 | Statistical significance |
| Min months for CIS | 2 | Enough data |
| Pattern confidence threshold | 0.7 | WHO pattern reliability |

---

## Scheduling

### Flow Schedule

| Flow | Schedule | Trigger |
|------|----------|---------|
| `credit_reset_check_flow` | Hourly | Cron |
| `monthly_replenishment_flow` | On-demand | Post-credit-reset |
| `pattern_learning_flow` | Weekly (Sunday 3AM) | Cron |
| `icp_refinement_flow` | Monthly (after patterns) | Post-pattern-learning |

### Schedule Registry Addition

```python
# In scheduled_jobs.py

"monthly_replenishment": {
    "schedule": None,  # Triggered by credit_reset, not scheduled
    "description": "Post-credit-reset lead replenishment",
    "work_queue": "agency-os-queue",
    "tags": ["leads", "monthly", "replenishment"],
},
```

---

## Notifications

### Client Notifications

| Event | Notification |
|-------|--------------|
| Credit reset | "Your monthly credits have been reset to {quota}" |
| Replenishment complete | "We've added {count} new leads to your campaigns" |
| Pipeline low | "Your pipeline is below {threshold} leads" |
| No active campaigns | "Leads sourced but not assigned — activate a campaign" |

### Admin Alerts

| Event | Alert |
|-------|-------|
| Replenishment failed | Sentry error + Slack notification |
| CIS refinement applied | Logged for audit |
| Unusual consumption | "> 120% daily burn rate" |

---

## Key Rules

1. **Smart replenishment is default** — Don't over-source if pipeline is full
2. **Only ACTIVE campaigns receive leads** — DRAFT/PAUSED/COMPLETED are excluded
3. **CIS refinement requires 20+ conversions** — Don't optimize on small samples
4. **Leads carry over** — Unconverted leads continue in sequence
5. **Archived leads don't count** — Removed from pipeline calculation
6. **Credits are for NEW leads** — Carryover leads don't consume credits

---

## Campaign Evolution (Month 2+)

### The Gap

Month 1: AI suggests campaigns based on ICP extraction
Month 2+: **No campaign evolution** — same campaigns run forever

### Proposed: Multi-Agent Campaign Analysis

After CIS pattern learning (weekly), a multi-agent system analyzes:

```
┌─────────────────────────────────────────────────────────────┐
│                  CAMPAIGN EVOLUTION AGENTS                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ WHO Analyzer │  │WHAT Analyzer │  │ HOW Analyzer │      │
│  │              │  │              │  │              │      │
│  │ Which leads  │  │ Which content│  │ Which channel│      │
│  │ convert?     │  │ resonates?   │  │ works best?  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│         └────────────┬────┴────────────────┘               │
│                      ▼                                      │
│              ┌───────────────┐                              │
│              │  Orchestrator │                              │
│              │    Agent      │                              │
│              └───────┬───────┘                              │
│                      │                                      │
│                      ▼                                      │
│              ┌───────────────┐                              │
│              │  Suggestions  │                              │
│              │  • New campaigns                             │
│              │  • Pause underperformers                     │
│              │  • Adjust allocations                        │
│              │  • Refine targeting                          │
│              └───────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Input | Output |
|-------|-------|--------|
| **WHO Analyzer** | CIS WHO patterns, lead data | Target refinement suggestions |
| **WHAT Analyzer** | CIS WHAT patterns, content performance | Content strategy suggestions |
| **HOW Analyzer** | CIS HOW patterns, channel metrics | Channel mix suggestions |
| **Orchestrator** | All analyzer outputs | Campaign action recommendations |

### Suggested Actions

| Action | Trigger | Confidence Required |
|--------|---------|---------------------|
| **Create new campaign** | Untapped segment identified | 0.8+ |
| **Pause campaign** | < 1% reply rate after 100 leads | 0.7+ |
| **Adjust allocation** | One campaign outperforming others | 0.7+ |
| **Refine targeting** | Clear WHO patterns emerge | 0.7+ |
| **Change channel mix** | HOW patterns show clear winner | 0.8+ |

### Approval Flow

```
Agents generate suggestions
         ↓
Suggestions stored in `campaign_suggestions` table
         ↓
Client notified via dashboard
         ↓
Client approves/rejects/modifies
         ↓
Approved suggestions applied
```

**Status:** NOT IMPLEMENTED — Requires multi-agent architecture

---

## Decisions Pending CEO Approval

These rules need explicit sign-off before implementation:

| # | Rule | Options | Recommendation | Status |
|---|------|---------|----------------|--------|
| 1 | Default replenishment mode | `full` / `smart` / `manual` | `smart` | PENDING |
| 2 | Auto-apply campaign suggestions | Yes / No (require approval) | No (require approval) | PENDING |
| 3 | Min conversions for CIS refinement | 10 / 20 / 50 | 20 | PENDING |
| 4 | Campaign pause threshold | 0.5% / 1% / 2% reply rate | 1% after 100 leads | PENDING |
| 5 | Lead carryover to month 2 | All / Active only / None | Active only | PENDING |

---

## Cross-References

| Topic | Document |
|-------|----------|
| Credit system | [`../business/TIERS_AND_BILLING.md`](../business/TIERS_AND_BILLING.md) |
| Lead sourcing | [`ENRICHMENT.md`](ENRICHMENT.md) |
| Campaign lifecycle | [`../business/CAMPAIGNS.md`](../business/CAMPAIGNS.md) |
| CIS patterns | [`../business/CIS.md`](../business/CIS.md) |
| Onboarding (month 1) | [`ONBOARDING.md`](ONBOARDING.md) |
| Outreach execution | [`OUTREACH.md`](OUTREACH.md) |

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
