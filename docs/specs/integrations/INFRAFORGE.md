# InfraForge Integration

> **Note:** InfraForge is used via external API calls (dashboard/manual). No code wrapper exists in this repo.
> Domain/mailbox provisioning is done through InfraForge dashboard, then exported to Salesforge/Warmforge for warmup.

**File:** External API (no wrapper in repo)
**Purpose:** Email domain and mailbox provisioning
**Phase:** 18 (Email Infrastructure)
**Ecosystem:** InfraForge (domains) → Warmforge (warmup) → Salesforge (sending)

---

## Capabilities

- Domain provisioning
- Mailbox creation
- DNS record management
- Dedicated IP allocation
- SPF/DKIM/DMARC setup

---

## Usage Pattern

```python
class InfraForgeClient:
    def __init__(self, api_key: str):
        self.client = httpx.AsyncClient(
            base_url="https://api.infraforge.io/v1",
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def provision_domain(
        self,
        domain: str,
        client_id: str
    ) -> DomainResult:
        """Provision new email domain."""
        response = await self.client.post(
            "/domains",
            json={
                "domain": domain,
                "client_id": client_id,
                "setup_dns": True
            }
        )
        return DomainResult(**response.json())
    
    async def create_mailbox(
        self,
        domain_id: str,
        email_prefix: str,
        display_name: str
    ) -> MailboxResult:
        """Create mailbox on provisioned domain."""
        response = await self.client.post(
            f"/domains/{domain_id}/mailboxes",
            json={
                "email_prefix": email_prefix,
                "display_name": display_name
            }
        )
        return MailboxResult(**response.json())
    
    async def get_dns_records(
        self,
        domain_id: str
    ) -> list[DNSRecord]:
        """Get required DNS records for domain."""
        response = await self.client.get(
            f"/domains/{domain_id}/dns-records"
        )
        return [DNSRecord(**r) for r in response.json()["records"]]
    
    async def verify_dns(
        self,
        domain_id: str
    ) -> DNSVerification:
        """Check if DNS records are properly configured."""
        response = await self.client.post(
            f"/domains/{domain_id}/verify-dns"
        )
        return DNSVerification(**response.json())
```

---

## DNS Records Required

| Record | Type | Purpose |
|--------|------|---------|
| SPF | TXT | `v=spf1 include:infraforge.io ~all` |
| DKIM | TXT | Domain signing key |
| DMARC | TXT | `v=DMARC1; p=quarantine; rua=...` |
| MX | MX | Receive replies |

---

## Tier Infrastructure Allocation

| Tier | Domains | Mailboxes | Dedicated IPs |
|------|---------|-----------|---------------|
| Ignition | 2 | 3 | 1 |
| Velocity | 3 | 6 | 1 |
| Dominance | 5 | 11 | 2 |

---

## Provisioning Flow

```
Client signs up
      │
      ▼
┌─────────────────┐
│ Provision       │
│ domains         │ ──► 2-5 domains based on tier
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Get DNS         │
│ records         │ ──► Return to client
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Client adds     │
│ DNS records     │ ──► Manual step
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Verify DNS      │
│ (polling)       │ ──► Check every hour
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Create          │
│ mailboxes       │ ──► 3-11 based on tier
└─────────────────┘
      │
      ▼
┌─────────────────┐
│ Export to       │
│ Warmforge       │ ──► Start warmup (free with Salesforge)
└─────────────────┘
```

---

## Cost

- **Per dedicated IP:** ~$99/month
- **Per domain:** ~$10/month
- **Per mailbox:** ~$5/month
