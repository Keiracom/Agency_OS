# SDK Quick Reference Card

**For developers implementing SDK Brain in Agency OS**

---

## When to Use SDK Brain

| Scenario | Use SDK? | Model |
|----------|----------|-------|
| **ICP extraction (onboarding)** | ✅ Yes | Sonnet |
| Hot lead enrichment (ALS ≥ 85) | ✅ Yes | Sonnet |
| Hot lead email writing | ✅ Yes | Sonnet |
| Voice call KB generation | ✅ Yes | Sonnet |
| Complex objection handling | ✅ Yes | Sonnet |
| Intent classification | ❌ No | Haiku |
| Cold/Warm lead email | ❌ No | Haiku |
| ALS scoring | ❌ No | None (algorithm) |

---

## File Locations

```
NEW FILES:
src/integrations/sdk_brain.py              # Core wrapper
src/agents/sdk_agents/base_sdk_agent.py    # Base class
src/agents/sdk_agents/sdk_tools.py         # Tools
src/agents/sdk_agents/icp_agent.py         # ICP extraction (onboarding)
src/agents/sdk_agents/enrichment_agent.py  # Lead research
src/agents/sdk_agents/email_agent.py       # Emails
src/agents/sdk_agents/voice_kb_agent.py    # Voice prep
src/agents/sdk_agents/objection_agent.py   # Objections

MODIFY:
src/engines/icp_scraper.py  # Add SDK for ICP analysis
src/engines/scout.py        # Route Hot leads to SDK
src/engines/content.py      # Route Hot leads to SDK
src/engines/voice.py        # Add KB generation
src/engines/closer.py       # Route objections to SDK
src/config/settings.py      # Add SDK config
```

---

## Cost Limits (AUD)

| Limit Type | Ignition | Velocity | Dominance |
|------------|----------|----------|-----------|
| Daily SDK budget | $50 | $100 | $200 |
| **Per ICP extraction** | $1.00 | $1.00 | $1.00 |
| Per enrichment | $1.50 | $1.50 | $1.50 |
| Per email | $0.50 | $0.50 | $0.50 |
| Per voice KB | $2.00 | $2.00 | $2.00 |
| Per objection | $0.50 | $0.50 | $0.50 |

---

## SDK Brain Usage Pattern

```python
from src.integrations.sdk_brain import SDKBrain, SDKBrainConfig
from src.agents.sdk_agents.sdk_tools import WEB_SEARCH_TOOL

# 1. Configure
config = SDKBrainConfig(
    model="claude-sonnet-4-20250514",
    max_turns=10,
    max_cost_aud=1.50,
)

# 2. Initialize
sdk = SDKBrain(config=config)

# 3. Run
result = await sdk.run(
    prompt="Research this lead...",
    tools=[WEB_SEARCH_TOOL],
    output_schema=EnrichmentOutput,
    system="You are a research assistant...",
)

# 4. Check result
if result["success"]:
    data = result["data"]
    cost = result["cost_aud"]
else:
    error = result["error"]
```

---

## ALS-Based Routing

```python
# In any engine that might use SDK:

async def process_lead(lead: Lead, db: AsyncSession):
    """Route to SDK or standard processing based on ALS."""

    if lead.als_score >= 85:  # Hot lead
        # Use SDK Brain
        result = await sdk_enrichment_agent.enrich(lead)
    else:
        # Use standard enrichment
        result = await standard_enrichment(lead)

    return result
```

---

## Environment Variables

```bash
# Add to config/RAILWAY_ENV_VARS.txt

# SDK Feature Flags
SDK_BRAIN_ENABLED=true
SDK_MIN_ALS_SCORE=85

# SDK Cost Limits (AUD)
SDK_DAILY_LIMIT_IGNITION=50.0
SDK_DAILY_LIMIT_VELOCITY=100.0
SDK_DAILY_LIMIT_DOMINANCE=200.0

# SDK Model Selection
SDK_DEFAULT_MODEL=claude-sonnet-4-20250514
SDK_CLASSIFICATION_MODEL=claude-3-5-haiku-20241022
```

---

## Kill Switch

**Immediate disable (all clients):**
```bash
railway variables --service agency-os --set "SDK_BRAIN_ENABLED=false"
railway redeploy --service agency-os --yes
```

**Per-client disable:**
```sql
UPDATE clients SET sdk_brain_enabled = false WHERE id = 'client-uuid';
```

---

## Debugging

**Check SDK spend:**
```python
from src.integrations.redis import ai_spend_tracker

# Get today's SDK spend
spent = await ai_spend_tracker.get_spend()
remaining = await ai_spend_tracker.get_remaining()
print(f"Spent: ${spent:.2f}, Remaining: ${remaining:.2f}")
```

**Check SDK usage logs:**
```sql
SELECT
    agent_type,
    model_used,
    SUM(cost_aud) as total_cost,
    AVG(turns) as avg_turns,
    COUNT(*) as calls
FROM sdk_usage_log
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY agent_type, model_used;
```

---

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `AISpendLimitError` | Daily budget exceeded | Wait for reset or increase limit |
| `Cost limit exceeded` | Per-call limit hit | Reduce max_turns or max_cost |
| `Turn limit reached` | Agent looped too long | Improve prompt or increase limit |
| `Unknown tool` | Tool not in registry | Add to TOOL_REGISTRY |
| `Output parsing failed` | Claude returned bad JSON | Add retry or fallback |

---

## Testing

**Run SDK tests:**
```bash
# Unit tests (mocked)
pytest tests/agents/sdk_agents/ -v

# Integration tests (mocked)
pytest tests/integration/test_sdk_flow.py -v

# E2E tests (real API - requires TEST_MODE)
TEST_MODE=true pytest tests/e2e/test_sdk_e2e.py -v
```

**Cost validation:**
```bash
# Run cost tracking tests
pytest tests/cost/test_sdk_costs.py -v
```
