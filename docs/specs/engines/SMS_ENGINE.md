# SMS Engine — SMS Outreach

**File:** `src/engines/sms.py`  
**Purpose:** Send SMS messages with DNCR compliance  
**Layer:** 3 - engines

---

## DNCR Compliance (Australia)

**Do Not Call Register** check required before sending:

```python
async def check_dncr(self, phone: str) -> bool:
    """
    Check if phone number is on Australian DNCR.
    
    Returns True if number is on DNCR (do not contact).
    """
    # Wash against DNCR database
    result = await self.dncr_client.check(phone)
    return result.is_registered
```

---

## SMS Flow

```
Lead selected for SMS (Hot tier only)
        │
        ▼
┌─────────────────┐
│ Check DNCR      │
└─────────────────┘
        │
        ├── On DNCR ──► Skip, mark lead.dncr_checked = True
        │
        └── Clear
                │
                ▼
┌─────────────────┐
│ Generate        │
│ content         │ ──► Content Engine (short format)
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Send via        │
│ Twilio          │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Store activity  │
└─────────────────┘
```

---

## Message Constraints

| Constraint | Value |
|------------|-------|
| Max length | 160 characters (1 segment) |
| Recommended | 140 characters (leave room) |
| No links | Avoid URL shorteners (spam filters) |
| Sender ID | Australian mobile number |

---

## Rate Limiting

- **Per number:** 100 SMS/day
- **Per client:** Based on tier allocation

---

## API

```python
class SMSEngine:
    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID
    ) -> SendResult:
        """
        Send SMS to lead with DNCR check.
        
        Args:
            db: Database session
            lead_id: Target lead (must be Hot tier)
            
        Returns:
            SendResult with status
            
        Raises:
            DNCRViolation: If number is on DNCR
            TierViolation: If lead is not Hot tier
        """
        ...
    
    async def check_dncr(
        self,
        phone: str
    ) -> DNCRResult:
        """Check DNCR status for phone number."""
        ...
```

---

## Cost

- **Twilio SMS (AU):** $0.08/message outbound
- **DNCR wash:** Included in Twilio
