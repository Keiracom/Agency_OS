# SDK & Smart Prompts — Agency OS

**Purpose:** SDK-enhanced content generation and Smart Prompt personalization system.
**Status:** IMPLEMENTED
**Last Updated:** 2026-01-22

---

## Overview

The content generation system uses two complementary approaches:

1. **Smart Prompts** — Inject ALL enriched lead data into AI prompts for personalized content. Used for standard email, SMS, voice, and LinkedIn generation.

2. **SDK Agents** — Claude Agent SDK with web research tools for deep personalization. Used only for specific high-value scenarios (onboarding, Hot lead enrichment, reply handling, meeting prep).

**Key Insight:** SDK is for reasoning, not scraping. We already paid to enrich lead data — Smart Prompts use that data. SDK is reserved for cases where real-time research adds value.

---

## Code Locations

### Smart Prompts System

| Component | File | Purpose |
|-----------|------|---------|
| Smart Prompts Engine | `src/engines/smart_prompts.py` | Context builders + prompt templates |
| Content Engine | `src/engines/content.py` | Email/SMS/LinkedIn/Voice generation |
| Voice Engine | `src/engines/voice.py` | Voice KB generation |

### SDK Agents

| Component | File | Purpose |
|-----------|------|---------|
| SDK Eligibility | `src/agents/sdk_agents/sdk_eligibility.py` | Gate functions (should_use_sdk_*) |
| Enrichment Agent | `src/agents/sdk_agents/enrichment_agent.py` | Deep web research for Hot leads |
| Email Agent | `src/agents/sdk_agents/email_agent.py` | SDK-enhanced email for Hot leads |
| Voice KB Agent | `src/agents/sdk_agents/voice_kb_agent.py` | Voice knowledge base for Hot leads |
| ICP Agent | `src/agents/sdk_agents/icp_agent.py` | ICP extraction during onboarding |
| SDK Tools | `src/agents/sdk_agents/sdk_tools.py` | Web search/fetch tools for agents |
| Exports | `src/agents/sdk_agents/__init__.py` | Public API |

### Supporting Services

| Component | File | Purpose |
|-----------|------|---------|
| SDK Usage Service | `src/services/sdk_usage_service.py` | Cost tracking per agent/client |
| AI Spend Limiter | `src/services/send_limiter.py` | Daily spend enforcement |
| Anthropic Client | `src/integrations/anthropic.py` | Claude API wrapper |

### Orchestration

| Component | File | Purpose |
|-----------|------|---------|
| Stale Lead Refresh | `src/orchestration/flows/stale_lead_refresh_flow.py` | JIT Apify refresh before outreach |
| Outreach Flow | `src/orchestration/flows/outreach_flow.py` | Routes Hot leads to SDK |
| Enrichment Flow | `src/orchestration/flows/enrichment_flow.py` | Tiered SDK enrichment |

---

## Data Flow

### Smart Prompt Content Generation

```
Lead/Pool Lead in DB
    ↓
build_full_lead_context(db, lead_id)
    ↓
┌─────────────────────────────────────────────┐
│  Context Dict                               │
│  ├── person: name, title, seniority, tenure │
│  ├── company: name, industry, size, funding │
│  ├── signals: hiring, funded, new_in_role   │
│  ├── score: ALS score and tier              │
│  ├── research: pain_points, icebreakers     │
│  └── engagement: touches, objections        │
└─────────────────────────────────────────────┘
    ↓
build_client_proof_points(db, client_id)
    ↓
┌─────────────────────────────────────────────┐
│  Proof Points Dict                          │
│  ├── metrics: "50% faster", "3x ROI"        │
│  ├── named_clients: ["Acme", "BigCorp"]     │
│  ├── testimonials: quotes + authors         │
│  ├── ratings: G2, Capterra, Trustpilot      │
│  └── differentiators: unique selling points │
└─────────────────────────────────────────────┘
    ↓
format_lead_context_for_prompt()
format_proof_points_for_prompt()
    ↓
SMART_EMAIL_PROMPT template
    ↓
Claude API (via spend limiter)
    ↓
{"subject": "...", "body": "..."}
```

### SDK Agent Routing

```
Lead comes in
    ↓
Check ALS Score
    ↓
ALS < 85 (Not Hot) ────→ Smart Prompt Only
    ↓
ALS >= 85 (Hot)
    ↓
Check SDK Eligibility
    ↓
should_use_sdk_enrichment():
├── data_completeness < 0.5? → SDK
├── employee_count > 500? → SDK
├── title in EXECUTIVE_TITLES? → SDK
├── recently_funded (< 90 days)? → SDK
└── else → Standard enrichment
    ↓
should_use_sdk_email(): Hot → SDK email
should_use_sdk_voice_kb(): Hot → SDK voice KB
```

### Data Freshness (JIT Refresh)

```
Daily Outreach Prep Flow
    ↓
Query leads scheduled for today
    ↓
Filter: enriched_at > 7 days ago
    ↓
Batch Apify refresh (~$0.02/lead)
    ↓
Update lead_pool with fresh data
    ↓
Generate content with fresh context
```

---

## Smart Prompt Templates

### SMART_EMAIL_PROMPT

```python
"""Write a personalized cold outreach email using ALL the lead data below.

## LEAD CONTEXT
{lead_context}

## CLIENT PROOF POINTS (use 1-2 naturally)
{proof_points}

## CAMPAIGN CONTEXT
{campaign_context}

## EMAIL REQUIREMENTS
1. Subject line: Under 50 characters, specific to their situation
2. Body: Under 150 words, conversational tone
3. Use ONE specific detail about them (company signal, role, recent activity)
4. Include ONE relevant proof point (metric, client name, or case study)
5. End with a soft CTA (question, not hard ask)
6. No generic phrases ("hope this finds you well", "I wanted to reach out")
7. Sound like a real person, not a template

## OUTPUT FORMAT
Return JSON: {"subject": "...", "body": "..."}
"""
```

### SMART_VOICE_KB_PROMPT

Generates structured knowledge base for voice AI calls:
- `recommended_opener`: Personalized opening line
- `opening_hooks`: 3 conversation starters
- `pain_point_questions`: 3 discovery questions
- `objection_responses`: Timing, competitor, decision-maker, budget
- `company_context`: 2-3 sentence summary
- `do_not_mention`: Sensitive topics to avoid
- `meeting_ask`: How to ask for the meeting

---

## Context Builder Functions

### build_full_lead_context()

```python
async def build_full_lead_context(
    db: AsyncSession,
    lead_id: UUID,
    include_engagement: bool = True,
) -> dict[str, Any]:
    """
    Fetches:
    - Lead table data (all fields)
    - SDK enrichment data (if available)
    - Deep research data (if available)
    - Engagement history (optional)

    Returns:
        {
            "person": {name, title, seniority, tenure_months, ...},
            "company": {name, industry, size, funding, ...},
            "signals": {hiring, recently_funded, new_in_role, ...},
            "score": {als_score, als_tier, ...},
            "research": {pain_points, icebreakers, ...},  # if SDK enriched
            "engagement": {touches, objections, ...},
        }
    """
```

### build_full_pool_lead_context()

Same as above but for `lead_pool` table (richer Apollo data).

### build_client_proof_points()

```python
async def build_client_proof_points(
    db: AsyncSession,
    client_id: UUID,
) -> dict[str, Any]:
    """
    Fetches from client_intelligence table:
    - proof_metrics, proof_clients, proof_industries
    - testimonials, case_studies
    - G2/Capterra/Trustpilot/Google ratings
    - tagline, value_prop, differentiators
    """
```

---

## SDK Usage Strategy

| Purpose | Use SDK? | Use Instead | Rationale |
|---------|----------|-------------|-----------|
| ICP Extraction (onboarding) | YES | — | Needs live website scraping |
| Lead Enrichment | TIERED | Apollo + Apify | SDK only for sparse/exec/enterprise/funded |
| Email Generation | Hot only | Smart Prompt | Standard leads use enriched data |
| Voice KB Generation | Hot only | Smart Prompt | Standard leads use enriched data |
| SMS Content | NO | Smart Prompt | Data already in DB |
| Reply/Objection Handling | YES | — | Needs reasoning, not data lookup |
| Meeting Prep | YES | — | Deep research worth cost for booked meeting |

### Tiered SDK Enrichment Triggers

```python
should_use_sdk = (
    data_completeness < 0.5 or           # Sparse data from Apollo/Apify
    lead.company_employee_count > 500 or  # Enterprise company
    lead.title in EXECUTIVE_TITLES or     # CEO, Founder, VP, Director
    lead.company_latest_funding_date is recent  # Funded < 90 days
)
```

**Why tiered?** SDK web search only valuable when Google results exist (press, podcasts, conferences). Average mid-market contacts have no such coverage.

---

## Key Rules

1. **SDK for Reasoning, Not Scraping** — Don't use SDK to fetch data we can get from Apollo/Apify cheaper.

2. **Smart Prompts Use ALL Data** — Every field from enrichment should be in the context. We paid for it.

3. **Hot Leads Get SDK** — ALS >= 85 triggers SDK-enhanced content generation.

4. **Tiered Enrichment** — SDK enrichment only for sparse data, executives, enterprise, or recently funded.

5. **JIT Refresh** — Stale leads (> 7 days) get Apify refresh before outreach, not SDK.

6. **Spend Limiter Enforced** — All AI calls go through `send_limiter.py` daily limit.

7. **Cost Tracking** — Every SDK call logged to `sdk_usage_log` table via `sdk_usage_service.py`.

---

## Configuration

| Setting | Location | Default | Notes |
|---------|----------|---------|-------|
| Daily AI Spend Limit | `settings.anthropic_daily_spend_limit` | $100 AUD | Enforced by send_limiter |
| SDK Enrichment Max Cost | `sdk_eligibility.py` | $1.50 | Per lead |
| SDK Email Max Cost | `sdk_eligibility.py` | $0.50 | Per email |
| SDK Voice KB Max Cost | `sdk_eligibility.py` | $2.00 | Per KB |
| Stale Lead Threshold | `stale_lead_refresh_flow.py` | 7 days | Triggers Apify refresh |
| Data Completeness Threshold | `sdk_eligibility.py` | 0.5 | Below triggers SDK |

---

## Cost Impact

| Scenario | Before (SDK everywhere) | After (Smart Prompts) |
|----------|------------------------|----------------------|
| Enrichment (1,250/month) | ~$150 | ~$40 |
| Email generation | ~$100 | ~$15 |
| Data refresh | $0 | ~$10 |
| **Monthly total** | ~$250 | ~$65 |

**75% cost reduction, same quality.**

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `lead_pool` | Enriched lead data (Apollo) |
| `leads` | Campaign-assigned leads |
| `client_intelligence` | Proof points, ratings, testimonials |
| `sdk_usage_log` | Cost tracking per agent/client |

### SDK Fields on Lead

```sql
sdk_enrichment    JSONB    -- Deep research data
sdk_signals       TEXT[]   -- Triggered signals (sparse, exec, etc.)
sdk_cost_aud      DECIMAL  -- Total SDK cost for this lead
sdk_enriched_at   TIMESTAMP
sdk_voice_kb      JSONB    -- Generated voice knowledge base
sdk_email_content JSONB    -- SDK-generated email
```

---

## Response Models

### Email Generation Result

```python
{
    "subject": "Quick question about [specific detail]",
    "body": "Hi {first_name}...",
    "tokens_used": 450,
    "cost_aud": 0.02,
    "sdk_used": False,  # or True if Hot lead
}
```

### Voice KB Result

```python
{
    "recommended_opener": "...",
    "opening_hooks": ["...", "...", "..."],
    "pain_point_questions": ["...", "...", "..."],
    "objection_responses": {
        "timing_not_now": "...",
        "using_competitor": "...",
        "not_decision_maker": "...",
        "too_expensive": "..."
    },
    "company_context": "...",
    "do_not_mention": ["..."],
    "meeting_ask": "..."
}
```

---

## Cross-References

- [`../flows/ENRICHMENT.md`](../flows/ENRICHMENT.md) — Apollo → Apify → Clay waterfall
- [`../flows/OUTREACH.md`](../flows/OUTREACH.md) — SDK routing for Hot leads
- [`../business/SCORING.md`](../business/SCORING.md) — ALS tiers (Hot = 85+)
- [`../business/TIERS_AND_BILLING.md`](../business/TIERS_AND_BILLING.md) — Credit system
- [`../../specs/engines/CONTENT_ENGINE.md`](../../specs/engines/CONTENT_ENGINE.md) — Engine spec

---

For gaps and implementation status, see [`../TODO.md`](../TODO.md).
