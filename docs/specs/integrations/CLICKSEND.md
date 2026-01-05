# ClickSend Integration

**File:** `src/integrations/clicksend.py`  
**Purpose:** Australian direct mail  
**API Docs:** https://developers.clicksend.com/

---

## Capabilities

- Letter printing and mailing
- Australian postal network
- Address verification
- Delivery tracking

---

## Usage Pattern

```python
class ClickSendClient:
    def __init__(self, username: str, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://rest.clicksend.com/v3",
            auth=(username, api_key)
        )
    
    async def send_letter(
        self,
        to_address: Address,
        from_address: Address,
        pdf_url: str
    ) -> LetterResult:
        """Send physical letter via Australian post."""
        response = await self.client.post(
            "/post/letters/send",
            json={
                "recipients": [{
                    "address_name": to_address.company,
                    "address_line_1": to_address.line_1,
                    "address_line_2": to_address.line_2,
                    "address_city": to_address.city,
                    "address_state": to_address.state,
                    "address_postal_code": to_address.postcode,
                    "address_country": "AU",
                    "return_address_id": from_address.id
                }],
                "file_url": pdf_url,
                "template_used": 0,
                "colour": 1,  # Color printing
                "duplex": 0,  # Single-sided
                "priority_post": 0  # Standard post
            }
        )
        return LetterResult(**response.json())
    
    async def verify_address(
        self,
        address: Address
    ) -> AddressVerification:
        """Verify Australian postal address."""
        response = await self.client.post(
            "/post/letters/address/verify",
            json={
                "address_line_1": address.line_1,
                "address_city": address.city,
                "address_state": address.state,
                "address_postal_code": address.postcode,
                "address_country": "AU"
            }
        )
        return AddressVerification(**response.json())
```

---

## Address Requirements

| Field | Required | Validation |
|-------|----------|------------|
| `company` | Yes | Business name |
| `line_1` | Yes | Street address |
| `line_2` | No | Suite/level |
| `city` | Yes | City/suburb |
| `state` | Yes | NSW, VIC, QLD, WA, SA, TAS, NT, ACT |
| `postcode` | Yes | 4 digits |
| `country` | Yes | AU only |

---

## Letter Specifications

| Spec | Value |
|------|-------|
| Paper | A4 |
| Color | Full color |
| Pages | 1 (single-sided) |
| Envelope | Standard DL |
| Delivery | 3-5 business days |

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `letter.queued` | In print queue |
| `letter.printed` | Printed |
| `letter.dispatched` | Sent to postal service |
| `letter.delivered` | Delivered (if tracking) |

---

## Cost

- **Per letter:** $0.59 AUD
- **Includes:** Printing, envelope, standard postage
- **Priority post:** +$0.50
