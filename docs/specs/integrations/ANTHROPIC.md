# Anthropic Integration

**File:** `src/integrations/anthropic.py`  
**Purpose:** AI capabilities with spend limiting  
**API Docs:** https://docs.anthropic.com/

---

## Capabilities

- Content generation (emails, messages)
- Intent classification (reply handling)
- ICP extraction (website analysis)
- Conversation (voice AI backend)

---

## Spend Limiter (CRITICAL)

All AI calls go through spend limiter to prevent runaway costs:

```python
class AnthropicClient:
    def __init__(
        self,
        api_key: str,
        redis: RedisClient,
        daily_limit: float = 100.0  # AUD
    ):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.redis = redis
        self.daily_limit = daily_limit
    
    async def complete(
        self,
        prompt: str,
        max_tokens: int = 1000,
        model: str = "claude-3-sonnet-20240229"
    ) -> CompletionResult:
        """Generate completion with spend tracking."""
        
        # Check daily spend
        current_spend = await self.redis.get_daily_ai_spend()
        if current_spend >= self.daily_limit:
            raise AISpendLimitExceeded(
                f"Daily AI spend limit ({self.daily_limit}) exceeded"
            )
        
        # Make API call
        response = await self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Calculate and record cost
        cost = self._calculate_cost(response.usage, model)
        await self.redis.record_ai_spend(cost)
        
        return CompletionResult(
            content=response.content[0].text,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens,
            cost=cost
        )
    
    def _calculate_cost(self, usage, model: str) -> float:
        """Calculate cost in AUD."""
        # Sonnet pricing (as of Jan 2026)
        input_cost = usage.input_tokens * 0.003 / 1000  # $3/MTok
        output_cost = usage.output_tokens * 0.015 / 1000  # $15/MTok
        return (input_cost + output_cost) * 1.5  # USD to AUD
```

---

## Model Selection

| Use Case | Model | Reason |
|----------|-------|--------|
| Content generation | claude-3-sonnet | Balance of quality/cost |
| Intent classification | claude-3-haiku | Fast, cheap |
| ICP extraction | claude-3-sonnet | Needs reasoning |
| Voice conversation | claude-3-sonnet | Real-time quality |

---

## Cost (AUD, approximate)

| Model | Input | Output |
|-------|-------|--------|
| Claude 3 Opus | $22.50/MTok | $112.50/MTok |
| Claude 3 Sonnet | $4.50/MTok | $22.50/MTok |
| Claude 3 Haiku | $0.38/MTok | $1.88/MTok |

---

## Rate Limits

| Tier | Requests/min | Tokens/min |
|------|--------------|------------|
| Free | 5 | 20,000 |
| Build | 50 | 80,000 |
| Scale | 1,000 | 400,000 |

---

## Circuit Breaker

If spend limit is hit:

1. Log warning
2. Reject new AI requests
3. Alert via Sentry
4. Reset at midnight UTC

```python
async def check_circuit_breaker(self) -> bool:
    """Returns True if circuit is open (AI disabled)."""
    spend = await self.redis.get_daily_ai_spend()
    return spend >= self.daily_limit
```
