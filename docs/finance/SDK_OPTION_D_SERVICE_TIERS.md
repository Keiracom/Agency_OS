# SDK Option D: Tiered Service Levels

**Document Type:** Financial Analysis
**Option:** D — Service Tier Model (Customer Choice)
**Date:** January 19, 2026
**Currency:** AUD

---

## 1. Executive Summary

**Concept:** Create explicit service tiers within each subscription. Customers choose (and pay for) their desired level of AI personalization.

**Example:** Velocity base ($5,000/mo) includes standard enrichment. "Velocity Intelligence" add-on (+$1,000/mo) unlocks SDK for all Hot leads.

**Margin Protection:** Guaranteed — Customer pays for SDK
**Customer Impact:** Tiered — Customers choose their experience
**Recommendation:** FUTURE UPSELL OPPORTUNITY, not primary solution

---

## 2. How It Works

### Service Level Matrix

| Lead Category | Base Package | Intelligence Add-on |
|---------------|--------------|---------------------|
| Cold (ALS 20-34) | Email only | Email only |
| Cool (ALS 35-59) | Email + LinkedIn | Email + LinkedIn |
| Warm (ALS 60-84) | Email + LinkedIn + Voice | Email + LinkedIn + Voice |
| Hot (ALS 85+) Standard | All channels, template content | All channels, template content |
| Hot (ALS 85+) SDK | ❌ Not included | ✅ SDK research + personalization |

### Package Structure

**Base Packages (Current pricing):**
| Tier | Price | Hot Treatment |
|------|-------|---------------|
| Ignition | $2,500/mo | Standard (no SDK) |
| Velocity | $5,000/mo | Standard (no SDK) |
| Dominance | $7,500/mo | Standard (no SDK) |

**Intelligence Add-ons:**
| Add-on | Price | What It Unlocks |
|--------|-------|-----------------|
| Ignition Intelligence | +$500/mo | SDK for all Hot leads |
| Velocity Intelligence | +$1,000/mo | SDK for all Hot leads |
| Dominance Intelligence | +$1,500/mo | SDK for all Hot leads |

---

## 3. Financial Model

### Revenue Uplift (If 30% Adopt Add-on)

**Velocity Tier Example:**

| Customer Segment | Count | Revenue |
|------------------|-------|---------|
| Velocity Base only | 70% | $5,000 × 0.70 = $3,500 |
| Velocity + Intelligence | 30% | $6,000 × 0.30 = $1,800 |
| **Blended Average** | | **$5,300** |

### COGS for Intelligence Customers

| Tier | Leads | SDK Leads (all Hot) | SDK Cost | Other COGS | Total |
|------|-------|---------------------|----------|------------|-------|
| Ignition + Intel | 1,250 | 125 | $723 | $1,098 | $1,821 |
| Velocity + Intel | 2,250 | 225 | $1,301 | $1,867 | $3,168 |
| Dominance + Intel | 4,500 | 450 | $2,602 | $3,476 | $6,078 |

### Margin by Customer Type

**Velocity Example:**

| Customer Type | Revenue | COGS | Margin |
|---------------|---------|------|--------|
| Velocity Base | $5,000 | $2,168 | **56.6%** |
| Velocity + Intelligence | $6,000 | $3,168 | **47.2%** |

### Blended Margin (30% Adoption)

| Tier | Blended Revenue | Blended COGS | Blended Margin |
|------|-----------------|--------------|----------------|
| Ignition blend | $2,650 | $1,258 | **52.5%** |
| Velocity blend | $5,300 | $2,468 | **53.4%** |
| Dominance blend | $7,950 | $4,224 | **46.9%** |

---

## 4. Pricing Page Update

### Current Pricing Page

```
┌─────────────────────────────────────────────────────────────┐
│ IGNITION        VELOCITY         DOMINANCE                  │
│ $2,500/mo       $5,000/mo        $7,500/mo                 │
│                                                             │
│ 1,250 leads     2,250 leads      4,500 leads               │
│ 1 LinkedIn      3 LinkedIn       5 LinkedIn                │
│ 10 meetings     25 meetings      60 meetings               │
└─────────────────────────────────────────────────────────────┘
```

### Proposed Pricing Page

```
┌─────────────────────────────────────────────────────────────┐
│ IGNITION         VELOCITY          DOMINANCE                │
│ $2,500/mo        $5,000/mo         $7,500/mo                │
│                                                             │
│ 1,250 leads      2,250 leads       4,500 leads              │
│ 1 LinkedIn       3 LinkedIn        5 LinkedIn               │
│ 10 meetings      25 meetings       60 meetings              │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ 🧠 ADD INTELLIGENCE                                         │
│                                                             │
│ +$500/mo         +$1,000/mo        +$1,500/mo               │
│                                                             │
│ • AI deep research for Hot leads                            │
│ • Personalized emails referencing real company news         │
│ • Custom voice AI knowledge bases                           │
│ • Expected +25-40% reply rate improvement                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Implementation

### Database Changes

```sql
-- Add service level to clients
ALTER TABLE clients ADD COLUMN service_level VARCHAR(20) DEFAULT 'base';
-- Values: 'base', 'intelligence'

-- Add intelligence pricing
ALTER TABLE clients ADD COLUMN intelligence_addon_price DECIMAL(10,2);
```

### Subscription Flow Change

```python
# src/integrations/paddle.py

async def create_subscription(
    self,
    client_id: UUID,
    tier: str,
    intelligence_addon: bool = False,
) -> dict:
    """Create subscription with optional intelligence add-on."""

    base_price = TIER_PRICES[tier]
    addon_price = INTELLIGENCE_ADDON_PRICES[tier] if intelligence_addon else 0

    total_price = base_price + addon_price

    # Create Paddle subscription
    subscription = await self.paddle.create_subscription(
        customer_id=...,
        items=[
            {"price_id": BASE_PRICE_IDS[tier]},
            *([{"price_id": INTELLIGENCE_PRICE_IDS[tier]}] if intelligence_addon else []),
        ],
    )

    # Update client record
    async with get_db_session() as db:
        await db.execute(
            text("""
                UPDATE clients
                SET service_level = :level,
                    intelligence_addon_price = :addon
                WHERE id = :client_id
            """),
            {
                "client_id": str(client_id),
                "level": "intelligence" if intelligence_addon else "base",
                "addon": addon_price if intelligence_addon else None,
            }
        )
        await db.commit()

    return subscription
```

### SDK Eligibility Check

```python
# src/agents/sdk_agents/sdk_eligibility.py

async def should_use_sdk_brain_tiered(
    client_id: UUID,
    lead_data: dict,
) -> tuple[bool, str]:
    """
    Check SDK eligibility based on service level.

    Returns:
        Tuple of (eligible, reason)
    """
    # Check client service level
    async with get_db_session() as db:
        result = await db.execute(
            text("SELECT service_level FROM clients WHERE id = :id"),
            {"id": str(client_id)}
        )
        row = result.fetchone()
        service_level = row.service_level if row else "base"

    # Gate 1: Must be Hot
    als_score = lead_data.get("als_score", 0)
    if als_score < 85:
        return False, "not_hot"

    # Gate 2: Must have Intelligence add-on
    if service_level != "intelligence":
        return False, "no_intelligence_addon"

    return True, "eligible"
```

---

## 6. Sales & Marketing Implications

### Pros for Sales

| Benefit | Impact |
|---------|--------|
| Upsell opportunity | +$500-1,500/mo per customer |
| Clear value proposition | "Pay for AI research" |
| Competitive differentiation | "We offer AI tiers" |
| Customer choice | Self-select based on needs |

### Cons for Sales

| Issue | Impact |
|-------|--------|
| Pricing complexity | Two decisions instead of one |
| Base package feels "incomplete" | "Why don't I get AI?" |
| Comparison shopping harder | Competitors don't tier this way |
| Support burden | "What's the difference?" |

### Marketing Messaging

**For Base Package:**
> "Agency OS uses proven multi-channel outreach with personalized templates. Our AI-powered ALS scoring ensures your hottest leads get priority across email, LinkedIn, SMS, voice, and direct mail."

**For Intelligence Add-on:**
> "Upgrade to Agency OS Intelligence for next-level personalization. Our AI agents research each Hot lead in real-time, finding recent news, funding announcements, and hiring signals to craft hyper-personalized outreach that gets responses."

---

## 7. Customer Experience Comparison

### Base Customer Journey

```
Hot lead arrives
    ↓
Standard enrichment (scraped data)
    ↓
Template email: "Hi {name}, as {title} at {company}..."
    ↓
Static voice script
    ↓
SMS: "Hi {name}, following up on my email..."
```

### Intelligence Customer Journey

```
Hot lead arrives
    ↓
SDK deep research:
  - Web search: "{company} recent news"
  - Careers page: "Hiring 5 SDRs"
  - LinkedIn posts: CEO mentioned "lead response"
    ↓
SDK email: "Hi Sarah, congrats on the Series B! With..."
    ↓
Custom voice KB: "Pronunciation: SAH-rah. Don't mention competitor X..."
    ↓
SMS: "Hi Sarah, saw your post about scaling outbound..."
```

---

## 8. Adoption Projections

### Conservative Estimate (Year 1)

| Month | Total Customers | Intelligence Adoption | Intel Revenue |
|-------|-----------------|----------------------|---------------|
| M1-M3 | 20 | 10% (2) | $1,400/mo |
| M4-M6 | 50 | 15% (8) | $5,600/mo |
| M7-M9 | 80 | 20% (16) | $11,200/mo |
| M10-M12 | 120 | 25% (30) | $21,000/mo |

**Year 1 Intelligence Revenue:** ~$120,000

### Aggressive Estimate (Strong positioning)

| Month | Total Customers | Intelligence Adoption | Intel Revenue |
|-------|-----------------|----------------------|---------------|
| M1-M3 | 20 | 20% (4) | $2,800/mo |
| M4-M6 | 50 | 30% (15) | $10,500/mo |
| M7-M9 | 80 | 40% (32) | $22,400/mo |
| M10-M12 | 120 | 50% (60) | $42,000/mo |

**Year 1 Intelligence Revenue:** ~$240,000

---

## 9. Competitive Analysis

### How Competitors Handle AI

| Competitor | AI Offering | Pricing Model |
|------------|-------------|---------------|
| Apollo | AI writing built-in | Included in all tiers |
| Instantly | AI warmup, writing | Included |
| Smartlead | AI personalization | Included |
| HeyReach | Basic personalization | Included |
| **Agency OS** | **Tiered AI** | **Add-on option** |

### Positioning Challenge

Most competitors INCLUDE AI personalization. Charging extra may seem:
- **Positive:** Premium, advanced, "real AI vs gimmick"
- **Negative:** Nickel-and-diming, incomplete base product

---

## 10. Pros and Cons

### Pros

| Benefit | Impact |
|---------|--------|
| Customer pays for SDK | Margin protected |
| Revenue uplift | +$500-1,500/customer |
| Clear value ladder | Sales can upsell |
| Customer self-selects | Right fit for needs |
| No artificial limits | Pay for what you want |

### Cons

| Issue | Impact |
|-------|--------|
| Pricing complexity | Longer sales cycle |
| Base feels incomplete | "Why am I missing AI?" |
| Competitors include AI | Comparison disadvantage |
| Support overhead | "What's the difference?" |
| Implementation complexity | Two code paths |
| Testing burden | Test base + intelligence |

---

## 11. Recommendation

**FUTURE UPSELL OPPORTUNITY, not primary solution.**

Option D is viable but introduces:
- Sales friction (complexity)
- Marketing challenge (competitors include AI)
- Product confusion (base feels incomplete)

**Better approach:**
1. Launch with Option C (Selective Usage) as standard for all customers
2. Position SDK as "included for your highest-intent leads"
3. If SDK proves ROI, consider Option D as premium upgrade in Year 2

---

## 12. If CEO Chooses Option D

Implementation checklist:

1. [ ] Add `service_level` column to clients table
2. [ ] Create Intelligence add-on prices in Paddle
3. [ ] Update subscription creation flow
4. [ ] Modify SDK eligibility to check service level
5. [ ] Update pricing page with tiered options
6. [ ] Create sales enablement materials
7. [ ] Train support on tier differences
8. [ ] Create upgrade/downgrade flows
9. [ ] Build dashboard showing tier distribution
10. [ ] Implement trial-to-intelligence conversion tracking

**Estimated engineering time:** 5-7 days
**Estimated sales/marketing prep:** 2-3 weeks

---

**Prepared by:** CTO Office
**Reviewed by:** CFO Office
**Date:** January 19, 2026
