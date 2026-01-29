# Salesforge Ecosystem API Research

**Date:** 2026-01-28
**Researcher:** Subagent

## ✅ API Authentication (SOLVED)

All three services use the **same authentication method**:

```
Header: Authorization: {API_KEY}
```

**NOT** `Bearer {key}` or `X-API-Key`. Just the raw API key in the Authorization header.

### Working Examples:

```bash
# InfraForge
curl -H "Authorization: $INFRAFORGE_API_KEY" \
  "https://api.infraforge.ai/public/domains"

# WarmForge (note: basePath is /public/v1, not /public)
curl -H "Authorization: $WARMFORGE_API_KEY" \
  "https://api.warmforge.ai/public/v1/mailboxes?page=1&page_size=10"

# Salesforge
curl -H "Authorization: $SALESFORGE_API_KEY" \
  "https://api.salesforge.ai/public/v2/me"
```

### API Documentation URLs:

| Service | Swagger UI | Swagger JSON |
|---------|------------|--------------|
| InfraForge | https://api.infraforge.ai/public/swagger/index.html | https://api.infraforge.ai/public/swagger/doc.json |
| WarmForge | https://api.warmforge.ai/public/swagger/index.html | https://api.warmforge.ai/public/swagger/doc.json |
| Salesforge | https://api.salesforge.ai/public/v2/swagger/index.html | https://api.salesforge.ai/public/v2/swagger/doc.json |

---

## 📊 Current Account Status

### InfraForge (Domains & Mailboxes)
- **3 domains:** agencyxos-growth.com, agencyxos-leads.com, agencyxos-reach.com
- **6 mailboxes:** All active
  - alex@agencyxos-growth.com
  - alex@agencyxos-leads.com
  - alex@agencyxos-reach.com
  - david@agencyxos-growth.com
  - david@agencyxos-leads.com
  - david@agencyxos-reach.com
- All forwarding to: david.stephens@keiracom.com

### WarmForge (Email Warmup)
- **6 mailboxes connected**
- **Only 1 has warmup enabled:** david@agencyxos-reach.com
  - Heat Score: 90
  - 21 days warmup completed
  - Fully warmed ✅
- **5 mailboxes have warmup DISABLED:**
  - Heat Score: 47 each
  - 6 days warmup completed (then stopped)
  - Not warming ❌

### Salesforge (Campaign Sending)
- **1 workspace:** "Agency OS" (wks_b86a0iopxkzx2u3gvz9et)
- **0 mailboxes connected** ⚠️
- **0 sequences**

---

## 🔑 THE KEY DISCOVERY

**Salesforge includes UNLIMITED WarmForge warmup!**

From Salesforge pricing page:
> "Connect Unlimited Mailboxes - Unlimited Premium Warm Up powered by WarmForge. Warm up all your mailboxes before launching your sequences."

This applies to both:
- **Pro Plan:** $40/month
- **Growth Plan:** $80/month

### The Problem
Dave's mailboxes are connected to WarmForge directly (standalone) but **NOT** connected to Salesforge. This means:
1. Limited warmup slots in WarmForge (currently only 1)
2. Missing out on unlimited warmup included with Salesforge

---

## 💰 Pricing Options

### Option A: Use Salesforge (RECOMMENDED)
If Dave has/gets a Salesforge subscription:

| Plan | Monthly | Annual | Warmup Slots |
|------|---------|--------|--------------|
| Pro | $40/mo | $40/mo billed annually (2 months free) | **UNLIMITED** |
| Growth | $80/mo | $80/mo billed annually (2 months free) | **UNLIMITED** |

**Action:** Connect mailboxes to Salesforge → warmup becomes free

### Option B: WarmForge Standalone
If only using WarmForge without Salesforge:

| Slots | Monthly Cost | Quarterly Cost |
|-------|--------------|----------------|
| 1 | Included free | Included free |
| 6 (what Dave needs) | $50/mo | $150/quarter |

Pricing: $10/month per warmup slot, billed quarterly

---

## ⚠️ Previous Mistakes

1. **Wrong auth method:** Tried `Bearer {key}` and `X-API-Key` - neither works
2. **Wrong WarmForge base path:** API is at `/public/v1`, not `/public`
3. **Missing connection:** Mailboxes not connected to Salesforge

---

## 📋 ACTION ITEMS FOR DAVE

### Immediate (Enable Warmup for All 6 Mailboxes)

**If you have a Salesforge subscription:**
1. Log into Salesforge: https://app.salesforge.ai
2. Go to your "Agency OS" workspace
3. Connect all 6 mailboxes from InfraForge
4. Warmup should automatically become unlimited through WarmForge

**If you DON'T have Salesforge:**
1. Log into WarmForge: https://app.warmforge.ai
2. Go to Billing/Subscription
3. Buy 5 additional warmup slots ($50/month, billed quarterly = $150)
4. Enable warmup on the remaining 5 mailboxes

### Recommended Path
Get Salesforge Pro ($40/mo) which includes:
- Unlimited mailbox warmup (saves the $50/mo WarmForge cost)
- 1000 active contacts
- 5000 emails/month
- Email validation
- AI personalization

**Net savings:** If you were going to pay $50/mo for WarmForge slots anyway, Salesforge Pro at $40/mo gives you that PLUS the email campaign platform.

---

## 🔧 API Quick Reference

### InfraForge Endpoints
- `GET /domains` - List domains
- `GET /mailboxes` - List mailboxes
- `GET /credits/balance` - Check credits
- `POST /domains` - Buy domains

### WarmForge Endpoints
- `GET /v1/mailboxes?page=1&page_size=10` - List mailboxes
- `GET /v1/mailboxes/{address}` - Get mailbox details
- `PATCH /v1/mailboxes/{address}` - Update mailbox (enable/disable warmup)
- `POST /v1/mailboxes/connect-smtp` - Connect new mailbox
- `GET /v1/mailboxes/{address}/warmup/stats?from=2025-01-01&to=2025-01-28` - Warmup stats

### Salesforge Endpoints
- `GET /me` - Validate API key
- `GET /workspaces` - List workspaces
- `GET /workspaces/{id}/mailboxes` - List connected mailboxes
- `GET /workspaces/{id}/sequences` - List sequences
- `GET /workspaces/{id}/contacts` - List contacts

---

## Environment Variables

All properly configured in `~/.config/agency-os/.env`:

```bash
INFRAFORGE_API_KEY=7c7d4a1...
INFRAFORGE_API_URL=https://api.infraforge.ai/public

WARMFORGE_API_KEY=56ed3e4...
WARMFORGE_API_URL=https://api.warmforge.ai/public  # Note: add /v1 for API calls

SALESFORGE_API_KEY=245da5d...
SALESFORGE_API_URL=https://api.salesforge.ai/public/v2
```
