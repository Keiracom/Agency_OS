# LinkedIn Engine — LinkedIn Automation

**File:** `src/engines/linkedin.py`  
**Purpose:** LinkedIn outreach via HeyReach  
**Layer:** 3 - engines

---

## HeyReach Integration

HeyReach provides:
- Proxy rotation (avoid LinkedIn detection)
- Connection request automation
- Message automation
- Webhook callbacks

---

## LinkedIn Flow

```
Lead selected for LinkedIn (Cool+ tier)
        │
        ▼
┌─────────────────┐
│ Check LinkedIn  │
│ URL exists      │
└─────────────────┘
        │
        ├── No URL ──► Skip
        │
        └── Has URL
                │
                ▼
┌─────────────────┐
│ Check connection│
│ status          │
└─────────────────┘
        │
        ├── Already connected ──► Send message
        │
        └── Not connected ──► Send connection request
                                    │
                                    ▼
                            ┌─────────────────┐
                            │ Wait for        │
                            │ acceptance      │
                            │ (webhook)       │
                            └─────────────────┘
                                    │
                                    ▼
                            ┌─────────────────┐
                            │ Send follow-up  │
                            │ message         │
                            └─────────────────┘
```

---

## Rate Limiting

| Action | Limit | Period |
|--------|-------|--------|
| Connection requests | 17 | per day per seat |
| Messages | 50 | per day per seat |

---

## Seat Allocation by Tier

| Tier | HeyReach Seats |
|------|----------------|
| Ignition | 1 |
| Velocity | 3 |
| Dominance | 5 |

---

## Message Templates

Connection request note (max 300 chars):
```
Hi {first_name}, I noticed {company} is doing great work in {industry}. 
I'd love to connect and share some insights on client acquisition 
that might be valuable. - {sender_name}
```

Follow-up message:
```
Thanks for connecting, {first_name}! 

I work with agencies like {company} to help them predictably 
acquire new clients. Would you be open to a quick chat about 
what's working in your space?
```

---

## API

```python
class LinkedInEngine:
    async def send_connection(
        self,
        db: AsyncSession,
        lead_id: UUID,
        seat_id: str
    ) -> SendResult:
        """Send connection request via HeyReach."""
        ...
    
    async def send_message(
        self,
        db: AsyncSession,
        lead_id: UUID,
        seat_id: str,
        message_type: str = "follow_up"
    ) -> SendResult:
        """Send message to connected lead."""
        ...
    
    async def check_connection_status(
        self,
        linkedin_url: str,
        seat_id: str
    ) -> ConnectionStatus:
        """Check if already connected."""
        ...
```

---

## Cost

- **HeyReach:** $122/seat/month
