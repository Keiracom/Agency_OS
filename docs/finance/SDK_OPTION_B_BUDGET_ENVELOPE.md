> ⚠️ **DEPRECATED (FCO-002):** SDK has been replaced by Smart Prompts as of 2026-02-05.
> For current margin calculations, see: `MARGIN_RECALCULATION_POST_SIEGE.md`
> This document is retained for historical reference only.

# SDK Option B: Monthly Budget Envelope

**Document Type:** Financial Analysis
**Option:** B — Budget Envelope Model
**Date:** January 19, 2026
**Currency:** AUD

---

## 1. Executive Summary

**Concept:** Each client gets a fixed monthly SDK budget. System uses SDK until budget exhausted, then falls back to standard processing.

**Example:** Velocity client has $150/month SDK budget. Once 124 Hot leads processed with SDK ($1.21 each), remaining Hot leads use standard flow.

**Margin Protection:** Guaranteed — SDK spend is capped
**Customer Impact:** Variable — Early leads get SDK, late leads don't
**Recommendation:** GOOD as backup safeguard, not primary solution

---

## 2. How It Works

### SDK Budget Allocation

| Subscription Tier | Monthly SDK Budget | Expected SDK Calls | Buffer |
|-------------------|--------------------|--------------------|--------|
| Ignition | $75 | 62 Hot leads | +10% |
| Velocity | $150 | 124 Hot leads | +10% |
| Dominance | $300 | 248 Hot leads | +10% |

### Budget Consumption Flow

```
Hot lead arrives for SDK enrichment
    ↓
Check client.sdk_budget_remaining >= $1.21
    ↓
YES: Process with SDK, deduct $1.21
NO:  Process with standard Claude (fallback)
    ↓
Log to sdk_usage_log table
```

---

## 3. Implementation

### Database Changes

```sql
-- Add SDK budget columns to clients table
ALTER TABLE clients ADD COLUMN sdk_monthly_budget DECIMAL(10,2);
ALTER TABLE clients ADD COLUMN sdk_budget_remaining DECIMAL(10,2);
ALTER TABLE clients ADD COLUMN sdk_budget_reset_at TIMESTAMP;

-- Usage tracking (already exists from Phase 1)
-- sdk_usage_log table tracks all SDK calls

-- Index for fast budget checks
CREATE INDEX idx_clients_sdk_budget ON clients(id, sdk_budget_remaining);
```

### Code Change: SDKBrain Budget Check

```python
# src/integrations/sdk_brain.py

async def run(
    self,
    prompt: str,
    tools: list[dict],
    client_id: UUID | None = None,
    **kwargs
) -> SDKBrainResult:
    """Run SDK with budget check."""

    # Check client budget if client_id provided
    if client_id:
        budget_ok = await self._check_client_budget(client_id)
        if not budget_ok:
            return SDKBrainResult(
                success=False,
                error="SDK_BUDGET_EXHAUSTED",
                fallback_required=True,
            )

    # Existing SDK processing...
    result = await self._execute_sdk(prompt, tools, **kwargs)

    # Deduct from client budget
    if client_id and result.success:
        await self._deduct_budget(client_id, result.cost_aud)

    return result

async def _check_client_budget(self, client_id: UUID) -> bool:
    """Check if client has SDK budget remaining."""
    async with get_db_session() as db:
        result = await db.execute(
            text("""
                SELECT sdk_budget_remaining
                FROM clients
                WHERE id = :client_id
            """),
            {"client_id": str(client_id)}
        )
        row = result.fetchone()
        return row and row.sdk_budget_remaining > 1.50  # Min call cost
```

### Code Change: Scout Engine Fallback

```python
# src/engines/scout.py

async def enrich_hot_lead(
    self,
    db: AsyncSession,
    assignment_id: UUID,
    client_id: UUID,
) -> EngineResult:
    """Enrich Hot lead with SDK or fallback."""

    # Try SDK enrichment
    sdk_result = await self.sdk_brain.run(
        prompt=self._build_enrichment_prompt(assignment_id),
        tools=ENRICHMENT_TOOLS,
        client_id=client_id,
    )

    if sdk_result.success:
        # SDK enrichment succeeded
        return await self._save_sdk_enrichment(db, assignment_id, sdk_result)

    elif sdk_result.error == "SDK_BUDGET_EXHAUSTED":
        # Fallback to standard enrichment
        logger.info(f"SDK budget exhausted for client {client_id}, using fallback")
        return await self._standard_enrichment(db, assignment_id)

    else:
        # Other SDK error
        return EngineResult(success=False, error=sdk_result.error)

async def _standard_enrichment(
    self,
    db: AsyncSession,
    assignment_id: UUID,
) -> EngineResult:
    """Standard Claude enrichment without SDK tools."""

    # Use PersonalizationAnalysisSkill (existing, ~$0.08/call)
    skill = PersonalizationAnalysisSkill()
    result = await skill.run(...)

    return result
```

### Monthly Reset Job

```python
# src/orchestration/flows/billing_flow.py

@flow(name="reset_sdk_budgets")
async def reset_sdk_budgets_flow():
    """Monthly job to reset SDK budgets (runs 1st of month)."""

    async with get_db_session() as db:
        await db.execute(
            text("""
                UPDATE clients
                SET sdk_budget_remaining = sdk_monthly_budget,
                    sdk_budget_reset_at = NOW()
                WHERE subscription_status IN ('active', 'trialing')
            """)
        )
        await db.commit()

    logger.info("SDK budgets reset for all active clients")
```

---

## 4. Financial Model — Velocity Tier

### Expected SDK Usage (Budget Controlled)

| Scenario | Hot Leads | SDK Budget | SDK Calls | Fallback Calls |
|----------|-----------|------------|-----------|----------------|
| Light usage | 150 | $150 | 124 | 26 |
| Normal (10%) | 225 | $150 | 124 | 101 |
| Heavy (15%) | 338 | $150 | 124 | 214 |

### COGS Breakdown — Normal Usage (225 Hot)

| Component | SDK Leads (124) | Fallback Leads (101) | Total |
|-----------|-----------------|----------------------|-------|
| SDK Enrichment | 124 × $1.21 = $150 | — | $150 |
| Standard Enrichment | — | 101 × $0.08 = $8 | $8 |
| Email (SDK) | 124 × $0.25 = $31 | — | $31 |
| Email (Standard) | — | 101 × $0.03 = $3 | $3 |
| Voice KB (SDK) | 124 × $1.79 = $222 | — | $222 |
| Voice KB (Standard) | — | 101 × $0.20 = $20 | $20 |
| SMS | 225 × $0.22 = $50 | | $50 |
| Voice calls | 225 × $0.88 = $198 | | $198 |
| Direct Mail | 225 × $0.82 = $185 | | $185 |
| **Hot Lead COGS** | | | **$867** |

| Tier | Leads | Cost | Subtotal |
|------|-------|------|----------|
| Hot (above) | 225 | — | $867 |
| Warm | 563 | $1.42 | $799 |
| Cool | 900 | $0.36 | $324 |
| Cold | 562 | $0.29 | $163 |
| Infrastructure | — | — | $301 |
| **TOTAL COGS** | | | **$2,454** |

### Margin Analysis

| Metric | No SDK | Option B | Delta |
|--------|--------|----------|-------|
| Revenue | $4,000 | $4,000 | — |
| COGS | $2,168 | $2,454 | +$286 |
| Margin | 45.8% | **38.7%** | -7.1% |

---

## 5. All Tiers Financial Summary

| Tier | Revenue | COGS | SDK Budget | Margin |
|------|---------|------|------------|--------|
| Ignition | $2,500 | $1,189 | $75 | **52.4%** |
| Velocity | $4,000 | $2,454 | $150 | **38.7%** |
| Dominance | $7,500 | $4,612 | $300 | **38.5%** |

---

## 6. What Happens When Budget Exhausted

### Lead Processing Timeline

```
Month starts: Budget = $150
│
├── Week 1: 60 Hot leads → SDK enriched → Budget = $77
├── Week 2: 50 Hot leads → SDK enriched → Budget = $17
├── Week 3: 30 Hot leads → 14 SDK, 16 fallback → Budget = $0
└── Week 4: 85 Hot leads → ALL fallback
```

### Fallback Treatment (Non-SDK Hot Leads)

These leads still get Hot tier CHANNELS (SMS, Voice, Direct Mail), but:

| Feature | SDK Treatment | Fallback Treatment |
|---------|---------------|-------------------|
| Research depth | Multi-turn web search/fetch | Scraped data only |
| Pain points | Evidence-based, specific | Generic from industry |
| Email quality | Highly personalized | Template + basic personalization |
| Voice KB | Custom pronunciation, objections | Static campaign script |
| Personalization hooks | Researched, current | Generic |

**Quality difference:** SDK emails reference specific company news. Fallback emails use generic industry pain points.

---

## 7. Pros and Cons

### Pros

| Benefit | Impact |
|---------|--------|
| Guaranteed max SDK spend | CFO approved |
| ALS scoring unaffected | Leads scored accurately |
| Hot leads get channels | Still get SMS/Voice/Mail |
| Simple budget tracking | Dashboard can show remaining |
| Graceful degradation | System doesn't fail, just falls back |

### Cons

| Issue | Impact |
|-------|--------|
| End-of-month quality drop | Measurable |
| Unpredictable when exhausted | Could be day 15 or day 28 |
| Heavy-ICP clients penalized | More Hot leads = earlier exhaustion |
| Customer sees variability | "Why was this email better?" |
| Budget gaming potential | Pause campaigns to "save" budget |

---

## 8. Dashboard Integration

### Client-Facing Budget Widget

```
┌─────────────────────────────────────┐
│  SDK Intelligence Budget            │
│  ═══════════════════════════════    │
│  ████████████░░░░░░░░ 62% remaining │
│                                     │
│  $93 of $150 available              │
│  Resets: Feb 1, 2026                │
│                                     │
│  86 Hot leads processed with SDK    │
│  ~77 Hot leads remaining capacity   │
└─────────────────────────────────────┘
```

### Admin Monitoring

```sql
-- Daily budget consumption report
SELECT
    c.name,
    c.tier,
    c.sdk_monthly_budget,
    c.sdk_budget_remaining,
    ROUND((1 - c.sdk_budget_remaining / c.sdk_monthly_budget) * 100, 1) as pct_used,
    COUNT(DISTINCT sul.id) as sdk_calls_today
FROM clients c
LEFT JOIN sdk_usage_log sul ON sul.client_id = c.id
    AND sul.created_at > CURRENT_DATE
WHERE c.subscription_status = 'active'
GROUP BY c.id
ORDER BY pct_used DESC;
```

---

## 9. When Option B Makes Sense

- **As backup to Option C** — Hard cap if selective usage exceeds expectations
- **High-volume clients** — Where budget visibility matters
- **Conservative customers** — Who want predictable AI spend
- **Pilot phase** — Testing SDK value before full rollout

---

## 10. Recommendation

**GOOD as backup safeguard, not primary solution.**

Option B provides a hard ceiling on SDK costs but creates:
- Variable customer experience throughout month
- "Budget exhausted" scenarios that feel limiting
- Complexity in explaining why quality varies

**Better as hybrid:** Combine with Option C (Selective Usage) to use budget efficiently on highest-value leads.

---

## 11. Implementation Checklist

If CEO approves Option B (standalone or hybrid):

1. [ ] Add `sdk_monthly_budget` and `sdk_budget_remaining` to clients table
2. [ ] Add `sdk_budget_reset_at` timestamp
3. [ ] Create monthly reset Prefect job
4. [ ] Modify SDKBrain to check budget before execution
5. [ ] Add `SDK_BUDGET_EXHAUSTED` error handling to all SDK callers
6. [ ] Implement fallback paths in scout.py, content.py, voice.py, closer.py
7. [ ] Create dashboard widget for budget visibility
8. [ ] Add budget alerts (80% used, 95% used, exhausted)
9. [ ] Document fallback behavior for support team

**Estimated engineering time:** 3-4 days
**Estimated ongoing maintenance:** Minimal (monthly reset is automated)

---

**Prepared by:** CTO Office
**Reviewed by:** CFO Office
**Date:** January 19, 2026
