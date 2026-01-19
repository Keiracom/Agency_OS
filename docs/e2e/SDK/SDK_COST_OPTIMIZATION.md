# SDK Cost Optimization Cheatsheet

**Goal: Reduce SDK costs by 55% from worst-case to optimized**

---

## Summary

| Optimization | Savings | Effort | Priority |
|--------------|---------|--------|----------|
| Model Routing | 70-90% on simple tasks | Low | 🔴 Do First |
| Prompt Caching | 50-90% on repeated context | Medium | 🔴 Do First |
| Batch Processing | 50% on async tasks | Low | 🟡 Do Second |
| Template Augmentation | 40-60% on emails | Medium | 🟡 Do Second |
| Selective Usage | 30-50% on lead volume | Low | 🟢 Do Third |

---

## 1. Model Routing (70-90% savings)

### The Problem
Using Sonnet ($3/$15 per MTok) for everything, including simple tasks.

### The Solution
Route simple tasks to Haiku ($0.80/$4 per MTok).

### Implementation

```python
# src/agents/sdk_agents/sdk_config.py

MODEL_ROUTING = {
    # Simple tasks → Haiku
    "intent_classification": "claude-3-5-haiku-20241022",
    "sentiment_analysis": "claude-3-5-haiku-20241022",
    "template_selection": "claude-3-5-haiku-20241022",
    "simple_extraction": "claude-3-5-haiku-20241022",

    # Complex tasks → Sonnet
    "deep_research": "claude-sonnet-4-20250514",
    "email_writing": "claude-sonnet-4-20250514",
    "voice_kb_generation": "claude-sonnet-4-20250514",
    "objection_handling": "claude-sonnet-4-20250514",
}

def get_model_for_task(task_type: str) -> str:
    return MODEL_ROUTING.get(task_type, "claude-sonnet-4-20250514")
```

### Cost Impact

| Task | Before (Sonnet) | After (Haiku) | Savings |
|------|-----------------|---------------|---------|
| Classification (500 tokens) | $0.011 | $0.003 | 73% |
| Simple extraction | $0.015 | $0.004 | 73% |

---

## 2. Prompt Caching (50-90% savings)

### The Problem
Sending same context (ICP, industry, company) with every request.

### The Solution
Use Anthropic's prompt caching to store repeated context.

### Implementation

```python
# src/agents/sdk_agents/base_sdk_agent.py

from anthropic import Anthropic

class CachedSDKBrain:
    """SDK Brain with prompt caching."""

    def __init__(self):
        self.client = Anthropic()
        self._cache = {}

    async def run_with_cache(
        self,
        prompt: str,
        cached_context: str,  # This gets cached
        cache_key: str,
    ):
        """Run with cached context."""

        # Use cache_control to mark cacheable content
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": cached_context,
                        "cache_control": {"type": "ephemeral"}  # Cache for 5 min
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=messages,
        )

        return response
```

### What to Cache

| Context Type | Cache Duration | Reuse Across |
|--------------|----------------|--------------|
| ICP profile | 5 min | All leads in campaign |
| Industry research | 5 min | All leads in industry |
| Company profile | 5 min | All contacts at company |
| Objection frameworks | 5 min | All objections in campaign |

### Cost Impact

| Scenario | Without Cache | With Cache | Savings |
|----------|---------------|------------|---------|
| ICP context (5000 tokens) × 100 leads | $2.33 | $0.23 | 90% |
| Company context × 5 contacts | $0.12 | $0.03 | 75% |

---

## 3. Batch Processing (50% savings)

### The Problem
Processing leads one-by-one in real-time.

### The Solution
Use Anthropic Batch API for async tasks (50% discount).

### When to Use

| Task | Batch? | Reasoning |
|------|--------|-----------|
| Daily enrichment | ✅ Yes | Not time-sensitive |
| Nightly classification | ✅ Yes | Can wait until morning |
| Real-time response | ❌ No | Needs instant reply |
| Voice KB before call | ❌ No | Time-sensitive |

### Implementation

```python
# src/orchestration/tasks/batch_tasks.py

from anthropic import Anthropic

async def batch_enrich_leads(lead_ids: list[UUID]):
    """Batch process leads for enrichment."""
    client = Anthropic()

    # Prepare batch
    requests = []
    for lead_id in lead_ids:
        lead = await get_lead(lead_id)
        requests.append({
            "custom_id": str(lead_id),
            "params": {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": build_prompt(lead)}]
            }
        })

    # Submit batch (50% cheaper, 24hr turnaround)
    batch = client.batches.create(requests=requests)

    # Poll for completion
    while batch.status != "completed":
        await asyncio.sleep(60)
        batch = client.batches.retrieve(batch.id)

    # Process results
    return batch.results
```

### Cost Impact

| Volume | Real-time Cost | Batch Cost | Savings |
|--------|---------------|------------|---------|
| 100 leads × $0.78 | $78.00 | $39.00 | 50% |
| 500 leads × $0.78 | $390.00 | $195.00 | 50% |

---

## 4. Template Augmentation (40-60% savings)

### The Problem
Generating full emails from scratch every time.

### The Solution
Use templates with AI-filled placeholders.

### Before (Full Generation)

```
Prompt: "Write a cold email to Marcus at GrowthStack about our lead solution."

Output: Full 150-word email
Tokens: ~200 input + ~300 output = 500 tokens
Cost: $0.015
```

### After (Template Augmentation)

```
Prompt: "Fill in only the [BRACKETS]:

Hi {first_name},

[HOOK: 1 sentence referencing: {research_context}]

I help {industry} companies like {company} {value_prop}.

[PROOF: 1 stat relevant to {industry}]

Worth a chat?

{sender}"

Output: Just the bracketed parts (~50 words)
Tokens: ~150 input + ~100 output = 250 tokens
Cost: $0.006
```

### Implementation

```python
# src/agents/sdk_agents/email_agent.py

TEMPLATES = {
    "cold_outreach": """
Hi {first_name},

[HOOK]

I help {industry} companies like {company} {value_prop}.

[PROOF]

Worth a quick chat this week?

{sender}
""",
    "follow_up": """
Hi {first_name},

[CALLBACK: Reference previous email/interaction]

[NEW_VALUE: One new reason to connect]

Still interested in chatting?

{sender}
"""
}

async def generate_with_template(
    template_name: str,
    lead: Lead,
    research: dict,
) -> str:
    """Generate email using template augmentation."""
    template = TEMPLATES[template_name].format(
        first_name=lead.first_name,
        company=lead.company,
        industry=lead.organization_industry,
        value_prop=campaign.value_prop,
        sender=sender.name,
    )

    # Only generate the bracketed sections
    result = await sdk_brain.run(
        prompt=f"Fill in the [BRACKETED] sections only:\n\n{template}\n\nContext: {research}",
        output_schema=BracketedOutput,
    )

    return result
```

### Cost Impact

| Approach | Tokens | Cost | Savings |
|----------|--------|------|---------|
| Full generation | 500 | $0.015 | — |
| Template augmentation | 250 | $0.006 | 60% |

---

## 5. Selective Usage (30-50% savings)

### The Problem
Using SDK Brain for ALL Hot leads.

### The Solution
Use SDK Brain only for highest-intent Hot leads.

### Selection Criteria

```python
# src/agents/sdk_agents/sdk_config.py

def should_use_sdk_brain(lead: Lead) -> bool:
    """Only use SDK for highest-intent Hot leads."""

    # Must be Hot (ALS 85+)
    if lead.als_score < 85:
        return False

    # Priority signals (any one qualifies)
    priority_signals = [
        lead.recent_funding_date and (
            datetime.now() - lead.recent_funding_date
        ).days < 90,                           # Funded in last 90 days
        lead.hiring_count and lead.hiring_count >= 3,  # Actively hiring
        lead.tech_stack_match and lead.tech_stack_match > 0.8,  # Strong fit
        lead.linkedin_engagement_score and lead.linkedin_engagement_score > 70,
        lead.source == "referral",             # High-value source
        lead.company_employee_count and 50 <= lead.company_employee_count <= 500,  # Sweet spot
    ]

    return any(priority_signals)
```

### Cost Impact

| Approach | Hot Leads Processed | Cost |
|----------|---------------------|------|
| All Hot leads (100%) | 338 | $264 |
| Top 50% by intent | 169 | $132 |

**Savings: 50%**

---

## Combined Optimization Example

### Velocity Tier (2,250 leads/month)

| Cost Category | Worst Case | Optimized | Technique |
|---------------|------------|-----------|-----------|
| Enrichment (SDK) | $408 | $132 | Selective (50%) + Caching |
| Email Writing | $53 | $16 | Template augmentation |
| Classification | $14 | $2 | Haiku + Batch |
| Objections | $8 | $4 | Template augmentation |
| Voice KB | $393 | $157 | Caching + Lighter prompts |
| **SDK Total** | **$876** | **$311** | **65% reduction** |

### Monthly Margin Impact

| Scenario | COGS | Margin |
|----------|------|--------|
| No SDK | $1,775 | 64.5% |
| SDK Worst Case | $2,651 | 47.0% |
| **SDK Optimized** | **$2,086** | **58.3%** |

---

## Implementation Priority

### Week 1: Model Routing + Haiku for Classification
- Immediate 70%+ savings on simple tasks
- Low effort, high impact

### Week 2: Prompt Caching
- 50-90% savings on repeated context
- Requires cache key design

### Week 3: Template Augmentation
- 40-60% savings on emails
- Requires template library

### Week 4: Batch Processing
- 50% savings on async tasks
- Requires job scheduling

### Week 5: Selective Usage
- 30-50% savings on lead volume
- Requires intent scoring

---

## Monitoring

### Key Metrics to Track

```sql
-- Daily SDK cost by optimization
SELECT
    DATE(created_at) as date,
    agent_type,
    model_used,
    AVG(cached_tokens::float / NULLIF(input_tokens, 0)) as cache_hit_rate,
    AVG(cost_aud) as avg_cost,
    SUM(cost_aud) as total_cost
FROM sdk_usage_log
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at), agent_type, model_used
ORDER BY date DESC, total_cost DESC;
```

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Daily SDK cost | >$150 | >$250 |
| Avg cost per enrichment | >$0.60 | >$1.00 |
| Cache hit rate | <50% | <30% |
| Margin (Velocity) | <55% | <50% |
