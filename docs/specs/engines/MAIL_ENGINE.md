# Mail Engine — Direct Mail (Australia)

**File:** `src/engines/mail.py`  
**Purpose:** Physical direct mail via ClickSend  
**Layer:** 3 - engines

---

## ClickSend Integration

ClickSend provides:
- Letter printing and mailing
- Australian postal network
- Address verification
- Delivery tracking

---

## Mail Flow

```
Lead selected for Direct Mail (Hot tier only)
        │
        ▼
┌─────────────────┐
│ Verify address  │
│ (ClickSend)     │
└─────────────────┘
        │
        ├── Invalid ──► Skip, log reason
        │
        └── Valid
                │
                ▼
┌─────────────────┐
│ Generate letter │
│ content (PDF)   │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Submit to       │
│ ClickSend       │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Track delivery  │
│ (webhook)       │
└─────────────────┘
```

---

## Letter Template

**Format:** A4 single page, color  
**Elements:**
- Agency OS letterhead
- Personalized greeting
- Value proposition (2-3 paragraphs)
- Clear CTA with QR code
- Sender signature

---

## Address Requirements

| Field | Required | Validation |
|-------|----------|------------|
| company | Yes | Business name |
| address_line_1 | Yes | Street address |
| address_line_2 | No | Suite/level |
| city | Yes | City/suburb |
| state | Yes | NSW, VIC, QLD, etc. |
| postcode | Yes | 4 digits |
| country | Yes | Australia only |

---

## Rate Limiting

- **Per client:** Based on tier allocation
- **No daily limit:** Physical mail doesn't have spam concerns

---

## API

```python
class MailEngine:
    async def send(
        self,
        db: AsyncSession,
        lead_id: UUID
    ) -> SendResult:
        """
        Send direct mail letter to lead.
        
        Args:
            db: Database session
            lead_id: Target lead (must be Hot tier, Australian address)
            
        Returns:
            SendResult with tracking_id, status
        """
        ...
    
    async def verify_address(
        self,
        address: Address
    ) -> AddressVerification:
        """Verify Australian postal address."""
        ...
    
    async def handle_delivery_update(
        self,
        tracking_id: str,
        status: DeliveryStatus
    ) -> None:
        """Process delivery webhook from ClickSend."""
        ...
```

---

## Cost

- **ClickSend letter (AU):** $0.59/letter
- **Includes:** Printing, envelope, postage
