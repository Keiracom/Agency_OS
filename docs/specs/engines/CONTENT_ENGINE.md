# Content Engine — AI Content Generation

**File:** `src/engines/content.py`  
**Purpose:** Generate personalized outreach content  
**Layer:** 3 - engines

---

## Content Agent Integration

Uses Pydantic AI Content Agent for generation:

```python
class ContentRequest(BaseModel):
    lead_id: UUID
    channel: ChannelType
    template_type: str  # initial, follow_up_1, etc.
    personalization_level: str  # low, medium, high

class GeneratedContent(BaseModel):
    subject: str | None  # For email
    body: str
    personalization_used: list[str]
    word_count: int
    estimated_read_time: int  # seconds
```

---

## Content Types by Channel

| Channel | Content Types |
|---------|---------------|
| Email | Subject + body (50-150 words) |
| SMS | Short message (≤160 chars) |
| LinkedIn | Connection note (≤300 chars) or message |
| Voice | Conversation script |
| Mail | Letter body (200-400 words) |

---

## Personalization Variables

| Variable | Source | Example |
|----------|--------|---------|
| `{first_name}` | Lead | "Sarah" |
| `{company}` | Lead | "Acme Agency" |
| `{title}` | Lead | "Marketing Director" |
| `{industry}` | Lead org | "Digital Marketing" |
| `{recent_news}` | Enrichment | "Congrats on the new office" |
| `{mutual_connection}` | LinkedIn | "We both know John Smith" |
| `{pain_point}` | ICP | "scaling lead generation" |

---

## Template Structure

```python
class EmailTemplate:
    name: str
    subject_variants: list[str]  # A/B testing
    body_structure: str  # Markdown with variables
    cta_type: str  # meeting_request, soft_ask, value_add
    
    # Constraints
    min_words: int = 50
    max_words: int = 150
    required_personalization: list[str] = ["first_name", "company"]
```

---

## Spend Limiting

All AI generation goes through spend limiter:

```python
async def generate(self, request: ContentRequest) -> GeneratedContent:
    # Check daily spend
    if await self.redis.get_daily_ai_spend() > DAILY_LIMIT:
        raise AISpendLimitExceeded()
    
    # Generate content
    result = await self.content_agent.generate(request)
    
    # Track spend
    await self.redis.increment_ai_spend(result.tokens_used)
    
    return result
```

---

## API

```python
class ContentEngine:
    async def generate_email(
        self,
        db: AsyncSession,
        lead_id: UUID,
        template_type: str = "initial"
    ) -> EmailContent:
        """Generate personalized email content."""
        ...
    
    async def generate_sms(
        self,
        db: AsyncSession,
        lead_id: UUID
    ) -> SMSContent:
        """Generate short SMS message."""
        ...
    
    async def generate_linkedin_message(
        self,
        db: AsyncSession,
        lead_id: UUID,
        message_type: str = "connection"
    ) -> LinkedInContent:
        """Generate LinkedIn message or connection note."""
        ...
    
    async def generate_voice_script(
        self,
        db: AsyncSession,
        lead_id: UUID
    ) -> VoiceScript:
        """Generate voice call conversation script."""
        ...
```

---

## WHAT Pattern Integration (Phase 16)

Content generation uses learned patterns:

```python
async def get_effective_patterns(
    self,
    client_id: UUID,
    channel: ChannelType
) -> ContentPatterns:
    """
    Get patterns that have led to conversions.
    
    Returns:
        - Effective subject lines
        - Winning CTAs
        - Optimal message length
        - Pain points that resonate
    """
    ...
```
