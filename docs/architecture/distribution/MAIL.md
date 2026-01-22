# Direct Mail Distribution Architecture

**Status:** 🔴 SPEC ONLY (Not Implemented)
**Provider:** ClickSend (Australian postal service)
**Rate Limit:** 1000/day (ClickSend capacity)
**Last Updated:** January 22, 2026

---

## Executive Summary

Direct mail is an optional channel not included in the default 5-step sequence. Used for high-value prospects (enterprise, executive) as a differentiation tactic. Physical mail stands out in a digital-first world.

---

## Current State

| Component | Status | Notes |
|-----------|--------|-------|
| ClickSend mail API | 🟡 | Integration started |
| Mail engine | 🔴 | Not implemented |
| Outreach flow integration | 🔴 | Not wired |
| Address verification | 🔴 | Not implemented |
| Template design | 🔴 | Not designed |

---

## When to Use Direct Mail

### Trigger Conditions

Direct mail is triggered for high-value prospects:

```python
def should_send_direct_mail(lead: Lead) -> bool:
    """
    Determine if lead qualifies for direct mail.
    """
    return (
        lead.als_score >= 90                    # Ultra-hot
        or lead.company_employee_count >= 500   # Enterprise
        or lead.title in EXECUTIVE_TITLES       # C-suite
        or lead.deal_value_estimate >= 50000    # High value
    )
```

### Use Cases

1. **Enterprise Pursuit** — Multi-touch before big meeting
2. **Executive Outreach** — Bypass gatekeepers
3. **Re-engagement** — Wake dormant high-value leads
4. **Event Follow-up** — Post-conference touchpoint

---

## Mail Types

### 1. Postcards

| Spec | Value |
|------|-------|
| Size | A5 (148 × 210 mm) |
| Weight | 300gsm |
| Print | Full color both sides |
| Cost | ~$1.50 AUD |
| Delivery | 3-5 business days |

### 2. Letters

| Spec | Value |
|------|-------|
| Envelope | C5 window |
| Paper | 100gsm |
| Print | B&W or color |
| Cost | ~$2.50 AUD |
| Delivery | 3-5 business days |

### 3. Packages

For ultra-high-value prospects:
- Branded merchandise
- Personalized gifts
- Custom packaging

Cost: $20-50+ AUD

---

## Address Requirements

### Verification

Before sending, verify:
1. Address is complete (street, city, state, postcode)
2. Address is deliverable (DPID check)
3. Lead is in Australia (international mail = 3x cost)

```python
async def verify_postal_address(address: dict) -> dict:
    """
    Verify Australian postal address.

    Uses Australia Post DPID lookup.
    """
    return {
        'valid': True,
        'dpid': '12345678',
        'standardized': {
            'line1': '123 Example St',
            'line2': 'Level 5',
            'city': 'Sydney',
            'state': 'NSW',
            'postcode': '2000',
            'country': 'Australia',
        }
    }
```

### Data Source

Address from enrichment:
- `lead.company_hq_address`
- `lead.company_hq_city`
- `lead.company_hq_state`
- `lead.company_hq_postcode`
- `lead.company_hq_country`

**Note:** Many leads won't have complete addresses. Direct mail only possible when address is verified.

---

## Content Templates

### Postcard Template

**Front:**
- Eye-catching headline
- Brand logo
- QR code to landing page

**Back:**
- Personalized message
- Call to action
- Contact details

```python
MAIL_POSTCARD_PROMPT = """
Write postcard copy for:

Lead: {first_name} {last_name}
Title: {title}
Company: {company_name}
Pain point: {main_pain_point}

Front headline (max 10 words): Bold, curiosity-driven
Back message (max 100 words): Personalized, value-focused
CTA: Visit landing page or call
"""
```

### Letter Template

```python
MAIL_LETTER_PROMPT = """
Write a formal business letter for:

Lead: {first_name} {last_name}
Title: {title}
Company: {company_name}
Previous touches: {touch_summary}
Reason for mail: {trigger_reason}

Structure:
1. Opening (personalized reference)
2. Value proposition (their specific challenge)
3. Social proof (similar company result)
4. CTA (specific next step)
5. Sign-off

Max 300 words.
"""
```

---

## ClickSend Integration

```python
# src/integrations/clicksend.py

class ClickSendClient:
    async def send_postcard(
        self,
        to_address: dict,
        front_image_url: str,
        back_content: str,
    ) -> dict:
        """
        Send postcard via ClickSend.
        """

    async def send_letter(
        self,
        to_address: dict,
        content_html: str,
        return_address: dict,
    ) -> dict:
        """
        Send letter via ClickSend.
        """
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `src/engines/mail.py` | Mail sending logic |
| `src/services/address_verification_service.py` | Address validation |
| Templates in `src/templates/mail/` | Postcard/letter designs |

---

## Verification Checklist

- [ ] ClickSend mail API integrated
- [ ] Address verification works
- [ ] Postcard template designed
- [ ] Letter template designed
- [ ] Mail engine implemented
- [ ] Trigger conditions defined
- [ ] Cost tracking implemented

---

## Configuration

### Environment Variables

```bash
CLICKSEND_USERNAME=xxx
CLICKSEND_API_KEY=xxx
```

### Settings

```python
# src/config/settings.py

mail_enabled: bool = False  # Feature flag
mail_postcard_cost_aud: float = 1.50
mail_letter_cost_aud: float = 2.50
mail_min_lead_score: int = 90
```

---

## Costs

| Item | Cost |
|------|------|
| Postcard (AU) | $1.50 AUD |
| Letter (AU) | $2.50 AUD |
| International | 3x domestic |

Expected usage: 5-10% of leads
- Velocity (2,250 leads): ~150 mail pieces
- Cost: ~$225-375 AUD/month

---

## Priority

**LOW** — Direct mail is a nice-to-have differentiator, not a core channel.

Implement after:
1. ✅ Email (core)
2. 🟡 Voice (core)
3. 🟡 LinkedIn (core)
4. 🟡 SMS (core)
5. 🔴 **Mail (optional)**
