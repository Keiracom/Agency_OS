---
name: parallel-scoring
description: Spawn multiple Opus 4.5 scoring agents to process knowledge items in parallel. Use when you have 100+ items to score and want to leverage the subscription rather than API calls.
---

# Parallel Scoring with Opus Agents

## When to Use
- Bulk scoring of knowledge items (100+ items)
- Leveraging existing Opus subscription vs pay-per-token
- Need higher intelligence than Haiku for nuanced scoring

## Architecture

```
Elliot (Orchestrator)
    │
    ├── scorer-agent-1 (items 0-49)
    ├── scorer-agent-2 (items 50-99)
    ├── scorer-agent-3 (items 100-149)
    └── scorer-agent-4 (items 150-199)
```

Each agent:
1. Queries Supabase for batch of items
2. Scores each item (business + learning)
3. Determines action type
4. Updates metadata in DB
5. Reports summary

## Spawning Pattern

```python
# Spawn 4 agents with different offsets
for i in range(4):
    sessions_spawn(
        task=f"""Score knowledge items for Agency OS relevance.
        
Query elliot_knowledge table for 50 unscored items.
Use OFFSET {i * 50} to get different items than other agents.

For each item, score 0-100 on:
1. Business relevance - cold email, sales automation, lead gen, B2B, SaaS
2. Learning relevance - LLM memory, multi-agent, orchestration, reasoning

Determine action type: evaluate_tool, research, absorb, competitive_intel, skip

Update metadata.scoring with scores and action_type.
Report summary when done.""",
        label=f"scorer-agent-{i+1}"
    )
```

## Scoring Criteria

### Business Score (0-100)
- 80+: Directly relevant to Agency OS (cold email tools, sales automation, competitor)
- 50-79: Tangentially relevant (general SaaS, B2B patterns)
- <50: Not business relevant

### Learning Score (0-100)
- 80+: Directly helps Elliot improve (agent patterns, memory, orchestration)
- 50-79: General AI/LLM knowledge
- <50: Not learning relevant

### Action Types
| Type | Criteria |
|------|----------|
| evaluate_tool | Software/library we might integrate |
| research | Topic worth deep diving |
| absorb | Pattern/technique to internalize |
| competitive_intel | Competitor information |
| skip | Not actionable |

## Database Update

```python
metadata = {
    **existing_metadata,
    'scoring': {
        'business_score': 85,
        'learning_score': 20,
        'action_type': 'evaluate_tool',
        'reasoning': 'Cold email automation tool, direct competitor analysis needed',
        'scored_by': 'opus-agent',
        'scored_at': '2026-01-30T12:23:00Z'
    }
}
```

## Cost Comparison

| Method | Cost | Intelligence | Speed |
|--------|------|--------------|-------|
| Haiku API | $0.25/1M tokens | Good | Fast |
| Opus agents (subscription) | Included | Best | Parallel |

## When to Use Which
- **Haiku API:** Quick scoring, budget-conscious, simple criteria
- **Opus agents:** Complex scoring, nuanced decisions, subscription available
