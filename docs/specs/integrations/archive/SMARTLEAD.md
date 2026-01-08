> **ARCHIVED:** This integration was replaced/superseded. Kept for historical reference.
> **Replaced by:** Salesforge ecosystem (Salesforge + Warmforge + InfraForge)
> **Archived:** January 8, 2026
> **Reason:** Project pivoted from Smartlead to Salesforge on January 6, 2026 for better API access and cost structure.

---

# Smartlead Integration (ARCHIVED)

**File:** `src/integrations/smartlead.py` (never implemented)
**Purpose:** Email warmup and high-volume sending
**Phase:** 19 (Email Infrastructure)
**API Docs:** https://api.smartlead.ai/docs

---

## Capabilities

- Email account warmup
- High-volume sending with rotation
- Deliverability monitoring
- Inbox placement tracking

---

## Why Smartlead (Not Instantly)

| Factor | Smartlead | Instantly |
|--------|-----------|-----------|
| API Quality | Better | Limited |
| Multi-tenant | Yes | Difficult |
| Cost (100 tenants) | ~$1,500-1,800/mo | ~$6,600-8,100/mo |
| Warmup Control | Full API | Manual |

---

## Usage Pattern

```python
class SmartleadClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://server.smartlead.ai/api/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )

    async def add_email_account(
        self,
        email: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        imap_host: str,
        imap_port: int
    ) -> AccountResult:
        """Add email account for warmup."""
        response = await self.client.post(
            "/email-accounts",
            json={
                "email": email,
                "smtp_host": smtp_host,
                "smtp_port": smtp_port,
                "smtp_username": smtp_username,
                "smtp_password": smtp_password,
                "imap_host": imap_host,
                "imap_port": imap_port,
                "warmup_enabled": True
            }
        )
        return AccountResult(**response.json())

    async def get_warmup_stats(
        self,
        account_id: str
    ) -> WarmupStats:
        """Get warmup progress and health metrics."""
        response = await self.client.get(
            f"/email-accounts/{account_id}/warmup-stats"
        )
        return WarmupStats(**response.json())

    async def send_email(
        self,
        account_id: str,
        to_email: str,
        subject: str,
        body: str,
        reply_to_message_id: str | None = None
    ) -> SendResult:
        """Send email via warmed account."""
        payload = {
            "email_account_id": account_id,
            "to": to_email,
            "subject": subject,
            "body": body
        }
        if reply_to_message_id:
            payload["in_reply_to"] = reply_to_message_id

        response = await self.client.post("/emails/send", json=payload)
        return SendResult(**response.json())
```

---

## Warmup Process

| Day | Daily Sends | Cumulative |
|-----|-------------|------------|
| 1-5 | 10 | 50 |
| 6-10 | 20 | 150 |
| 11-15 | 30 | 300 |
| 16-20 | 40 | 500 |
| 21-25 | 50 | 750 |
| 26-30 | 60 | 1050 |
| 31+ | 75 | Full |

---

## Health Metrics

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Inbox Rate | >90% | 70-90% | <70% |
| Bounce Rate | <2% | 2-5% | >5% |
| Spam Rate | <0.1% | 0.1-0.3% | >0.3% |

---

## Webhook Events

| Event | Description |
|-------|-------------|
| `email.sent` | Email sent |
| `email.delivered` | Confirmed delivery |
| `email.opened` | Email opened |
| `email.bounced` | Hard/soft bounce |
| `warmup.complete` | 30-day warmup finished |

---

## Cost

- **Base:** ~$39/month
- **Per mailbox:** Included up to limit
- **Overage:** Volume pricing
