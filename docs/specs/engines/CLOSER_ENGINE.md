# Closer Engine — Reply Handling

**File:** `src/engines/closer.py`  
**Purpose:** Process replies and classify intent  
**Layer:** 3 - engines

---

## Intent Classification

| Intent | Description | Action |
|--------|-------------|--------|
| `meeting_request` | Wants to book a meeting | Create meeting, notify client |
| `interested` | Positive but not ready | Continue sequence |
| `question` | Has questions | Queue for human response |
| `not_interested` | Polite decline | Pause sequence |
| `unsubscribe` | Explicit opt-out | Mark unsubscribed, stop all |
| `out_of_office` | Auto-reply OOO | Retry after return date |
| `auto_reply` | Generic auto-reply | Ignore, continue sequence |

---

## Reply Flow

```
Inbound reply (webhook)
        │
        ▼
┌─────────────────┐
│ Match to lead   │
│ (email/phone)   │
└─────────────────┘
        │
        ├── No match ──► Log, ignore
        │
        └── Matched
                │
                ▼
┌─────────────────┐
│ Classify intent │
│ (Reply Agent)   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Execute action  │
│ based on intent │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Notify client   │
│ (if needed)     │
└─────────────────┘
```

---

## Reply Agent Integration

Uses Pydantic AI Reply Agent for classification:

```python
class ReplyClassification(BaseModel):
    intent: IntentType
    confidence: float
    extracted_info: dict  # meeting times, questions, etc.
    suggested_response: str | None
```

---

## Meeting Extraction

When `intent = meeting_request`, extract:
- Proposed times (if mentioned)
- Timezone indicators
- Urgency level
- Preferred contact method

---

## Client Notification

| Intent | Notification |
|--------|--------------|
| meeting_request | Immediate (email + in-app) |
| interested | Daily digest |
| question | Immediate (needs response) |
| not_interested | Daily digest |
| unsubscribe | Daily digest |

---

## API

```python
class CloserEngine:
    async def process_reply(
        self,
        db: AsyncSession,
        channel: ChannelType,
        sender: str,  # email or phone
        content: str,
        metadata: dict
    ) -> ProcessResult:
        """
        Process inbound reply and take appropriate action.
        
        Args:
            db: Database session
            channel: email, sms, linkedin
            sender: Sender identifier
            content: Reply content
            metadata: Channel-specific data (message_id, etc.)
            
        Returns:
            ProcessResult with intent, actions taken
        """
        ...
    
    async def classify_intent(
        self,
        content: str,
        context: LeadContext
    ) -> ReplyClassification:
        """Classify reply intent using AI."""
        ...
```

---

## Webhook Sources

| Channel | Provider | Webhook |
|---------|----------|---------|
| Email | Postmark | Inbound email |
| SMS | Twilio | Inbound SMS |
| LinkedIn | HeyReach | Message reply |
| Voice | Vapi | Call outcome |
