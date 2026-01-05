# Email Engine — Email Outreach

**File:** `src/engines/email.py`  
**Purpose:** Send emails with threading support  
**Layer:** 3 - engines

---

## Threading Support

All follow-up emails include proper threading headers:

```python
headers = {
    "In-Reply-To": f"<{original_message_id}>",
    "References": f"<{original_message_id}>"
}
```

This ensures:
- Gmail groups messages in same thread
- Outlook shows conversation view
- Higher open rates (appears as reply)

---

## Email Flow

```
Lead selected for email
        │
        ▼
┌─────────────────┐
│ Check previous  │
│ activities      │
└─────────────────┘
        │
        ├── Has previous email ──► Get message_id for threading
        │
        └── First email ──► No threading headers
                │
                ▼
┌─────────────────┐
│ Generate        │
│ content         │ ──► Content Engine (AI)
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Send via        │
│ Resend          │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Store activity  │
│ with message_id │
└─────────────────┘
```

---

## Content Snapshot (Phase 16)

Store message details for Conversion Intelligence:

```python
content_snapshot = {
    "subject": "Re: Quick question about...",
    "body_preview": first_200_chars,
    "pain_points": ["scaling", "lead quality"],
    "cta_type": "meeting_request",
    "personalization_used": ["company_name", "recent_news"],
    "word_count": 87,
    "has_question": True
}
```

---

## Rate Limiting

- **Per domain:** 50 emails/day
- **Warmup period:** New domains start at 10/day, increase 10/day

---

## API

```python
class EmailEngine:
    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID,
        template_type: str = "initial"
    ) -> SendResult:
        """
        Send email to lead with proper threading.
        
        Args:
            db: Database session
            lead_id: Target lead
            template_type: initial, follow_up_1, follow_up_2, etc.
            
        Returns:
            SendResult with message_id, status
        """
        ...
    
    async def get_thread_context(
        self,
        db: AsyncSession,
        lead_id: UUID
    ) -> ThreadContext | None:
        """Get previous message IDs for threading."""
        ...
```

---

## Integration

**Primary:** Resend (sending)  
**Secondary:** Postmark (inbound webhooks)  
**Phase 19:** Smartlead (warmup + sending at scale)
