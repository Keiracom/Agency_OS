# Agency OS - Environment Variables Checklist

> **Last Updated:** January 2, 2026  
> **Status:** 35% configured (13/37)  
> **Critical Blockers:** None ✅

Run `python scripts/check_env.py` to verify current status.

---

## ✅ Configured (13)

| Variable | Category | Status |
|----------|----------|--------|
| `SUPABASE_URL` | Infrastructure | ✅ |
| `SUPABASE_ANON_KEY` | Infrastructure | ✅ |
| `SUPABASE_SERVICE_KEY` | Infrastructure | ✅ |
| `DATABASE_URL` | Infrastructure | ✅ |
| `REDIS_URL` | Infrastructure | ✅ |
| `PREFECT_API_URL` | Infrastructure | ✅ (self-hosted on Railway) |
| `ANTHROPIC_API_KEY` | AI | ✅ |
| `RESEND_API_KEY` | Email | ✅ |
| `VERCEL_TOKEN` | Deployment | ✅ |
| `GITHUB_TOKEN` | Deployment | ✅ |
| `GOOGLE_CLIENT_ID` | Auth | ✅ |
| `GOOGLE_CLIENT_SECRET` | Auth | ✅ |

---

## ❌ Required - Missing (16)

These are needed for channels to function. Add to `config/.env` as you obtain them.

### Enrichment (Lead Sourcing)

| Variable | Purpose | Get From |
|----------|---------|----------|
| `APOLLO_API_KEY` | Lead sourcing + contact enrichment | [developer.apollo.io](https://developer.apollo.io/) |
| `APIFY_API_KEY` | Website scraping for ICP extraction | [console.apify.com](https://console.apify.com/account/integrations) |

### Email Channel

| Variable | Purpose | Get From |
|----------|---------|----------|
| `POSTMARK_SERVER_TOKEN` | Inbound reply detection via webhooks | [account.postmarkapp.com](https://account.postmarkapp.com/servers) |

### SMS Channel (ClickSend)

| Variable | Purpose | Get From |
|----------|---------|----------|
| `CLICKSEND_USERNAME` | ClickSend account username | [clicksend.com](https://dashboard.clicksend.com/) |
| `CLICKSEND_API_KEY` | ClickSend API key | Same as above → API Credentials |

**Note:** ClickSend is an Australian company (Perth) - primary SMS provider for AU market. Twilio is used for VOICE ONLY via Vapi.

### LinkedIn Channel

| Variable | Purpose | Get From |
|----------|---------|----------|
| `HEYREACH_API_KEY` | LinkedIn connection requests + messaging | [heyreach.io](https://heyreach.io) (contact for API access) |

### Voice Channel

| Variable | Purpose | Get From |
|----------|---------|----------|
| `VAPI_API_KEY` | Voice AI orchestration (includes STT) | [vapi.ai](https://vapi.ai) - $10 free credit on signup |
| `VAPI_PHONE_NUMBER_ID` | Twilio number linked in Vapi dashboard | Vapi dashboard after linking Twilio |
| `ELEVENLABS_API_KEY` | High-quality voice synthesis (TTS) | [elevenlabs.io](https://elevenlabs.io) |

### Payments (Stripe)

| Variable | Purpose | Get From |
|----------|---------|----------|
| `STRIPE_API_KEY` | Billing - secret key (sk_live_...) | [dashboard.stripe.com/apikeys](https://dashboard.stripe.com/apikeys) |
| `STRIPE_PUBLISHABLE_KEY` | Frontend Stripe.js (pk_live_...) | Same as above |
| `STRIPE_WEBHOOK_SECRET` | Webhook signature verification (whsec_...) | Stripe Dashboard → Webhooks |
| `STRIPE_PRICE_IGNITION` | Price ID for $2,500/mo tier | Create product in Stripe Dashboard |
| `STRIPE_PRICE_VELOCITY` | Price ID for $5,000/mo tier (or $2,500 founding) | Create product in Stripe Dashboard |
| `STRIPE_PRICE_DOMINANCE` | Price ID for $7,500/mo tier | Create product in Stripe Dashboard |

---

## ⚪ Optional - Missing (8)

These can be added later. System works without them.

### Enrichment (Fallback)

| Variable | Purpose | Get From |
|----------|---------|----------|
| `CLAY_API_KEY` | Waterfall enrichment when Apollo misses | [app.clay.com/settings/api](https://app.clay.com/settings/api) |

### Calendar Integration

| Variable | Purpose | Get From |
|----------|---------|----------|
| `CALCOM_API_KEY` | Meeting booking links | [app.cal.com/settings/developer](https://app.cal.com/settings/developer/api-keys) |
| `CALENDLY_API_KEY` | Alternative meeting booking | [calendly.com/integrations](https://calendly.com/integrations/api_webhooks) |

### Web Search

| Variable | Purpose | Get From |
|----------|---------|----------|
| `SERPER_API_KEY` | Google Search for ICP research | [serper.dev](https://serper.dev/) - $0.01/search |

### Monitoring

| Variable | Purpose | Get From |
|----------|---------|----------|
| `SENTRY_DSN` | Error tracking + performance | [sentry.io](https://sentry.io/) |

### Security

| Variable | Purpose | Get From |
|----------|---------|----------|
| `WEBHOOK_HMAC_SECRET` | Sign outbound webhooks | Generate: `openssl rand -hex 32` |
| `JWT_SECRET` | JWT token signing | Generate: `openssl rand -hex 64` |

### Direct Mail

| Variable | Purpose | Get From |
|----------|---------|----------|
| `LOB_API_KEY` | Physical direct mail campaigns | [dashboard.lob.com](https://dashboard.lob.com/) |

---

## 🚀 Priority Order for Launch

1. **Apollo + Apify** — Lead sourcing won't work without these
2. **Stripe (all 6 vars)** — Can't charge customers
3. **Postmark** — Won't detect email replies
4. **ClickSend (2 vars)** — SMS channel
5. **HeyReach** — LinkedIn channel
6. **Vapi + ElevenLabs** — Voice channel
7. **Lob** — Direct mail (can defer to post-launch)

---

## 💰 Recommended Plans for Testing Phase

**Goal:** Cheapest viable setup to test all channels before launch.

### Summary: ~$295-370/month during testing

| Service | Recommended Plan | Monthly Cost | Notes |
|---------|-----------------|--------------|-------|
| **Apollo** | Free | $0 | 10K email credits/mo with corporate email. Start here. |
| **Apify** | Free | $0 | $5/mo in credits (renews monthly). Enough for testing scrapers. |
| **Stripe** | Pay-as-you-go | ~1.7% + $0.30/tx | No monthly fee. 1.7% + A$0.30 per AU domestic card. |
| **Postmark** | Starter | $15/mo | 10K emails. Excellent deliverability. Free dev tier (100/mo) for initial setup. |
| **ClickSend** | Pay-as-you-go | ~$20-50/mo | ~$0.06-0.08/SMS (AU outbound). No monthly fees. Australian company. |
| **Twilio** | Pay-as-you-go | ~$5-10/mo | Voice calls ONLY (via Vapi). ~$0.01/min. NOT for SMS. |
| **HeyReach** | Starter | $79/mo | 1 LinkedIn sender. 14-day free trial with 3 accounts first. |
| **Vapi** | Pay-as-you-go | ~$50-100/mo | $0.05/min base + ~$0.08-0.15/min for STT/TTS/LLM. $10 free credit on signup. |
| **ElevenLabs** | Starter | $5/mo | 30K credits (~30 min TTS). Or use Vapi's built-in voices to skip this initially. |

### Detailed Breakdown

#### 1. Apollo (Lead Sourcing) — **FREE to start**
- **Plan:** Free tier
- **What you get:** 10,000 email credits/month (with corporate domain email)
- **Limits:** Basic filters, 2 sequences, limited API
- **Upgrade trigger:** When you need phone numbers or advanced filters → Basic $49/user/mo
- **My recommendation:** Start free. You'll know within 2 weeks if you need to upgrade.

#### 2. Apify (Web Scraping) — **FREE to start**
- **Plan:** Free tier  
- **What you get:** $5/month in platform credits (auto-renews)
- **Reality:** $5 is enough to run ~50-100 small scraping jobs
- **Upgrade trigger:** If you're running large-scale website scraping → Starter $39/mo
- **My recommendation:** Free tier is plenty for ICP extraction during testing.

#### 3. Stripe (Payments) — **FREE until you charge**
- **Plan:** Pay-as-you-go (no monthly fee)
- **Fees:** 1.7% + A$0.30 per domestic AU transaction
- **International cards:** +3.5% fee
- **Setup:** Create account, add products, get API keys immediately
- **My recommendation:** Zero cost until you process payments. Use Test Mode for dev.

#### 4. Postmark (Inbound Email) — **$15/mo**
- **Plan:** Starter (10,000 emails/month)
- **Why not free:** Free tier is only 100 emails - too limiting for real testing
- **Includes:** Inbound parsing, webhooks, analytics, templates
- **Upgrade trigger:** >10K emails → $25/mo for 25K
- **My recommendation:** $15/mo is worth it for reliable deliverability + inbound webhooks.

#### 5. ClickSend (SMS) — **~$20-50/mo usage-based**
- **Provider:** ClickSend (Australian company, Perth)
- **Plan:** Pay-as-you-go (no monthly fees)
- **Costs breakdown:**
  - Outbound SMS to AU: ~$0.06-0.08/message
  - Inbound SMS: ~$0.02/message
  - No phone number rental fees
- **Testing budget:** 500 outbound SMS = ~$35/mo
- **Why ClickSend:** Native Australian support, DNCR compliant, no minimum volumes
- **My recommendation:** Best choice for Australian SMS. Twilio is NOT used for SMS.

**Note:** Twilio is used for VOICE CALLS only (via Vapi), NOT for SMS.

#### 6. HeyReach (LinkedIn) — **$79/mo or FREE trial**
- **Plan:** Starter ($79/sender/month)
- **Free trial:** 14 days with up to 3 LinkedIn accounts (no CC required)
- **What you get:** Unlimited campaigns, unified inbox, webhooks, API
- **Upgrade trigger:** Multiple LinkedIn senders → Agency $999/mo for 50 senders
- **My recommendation:** Use the 14-day free trial first. If LinkedIn is working, commit to $79/mo.

#### 7. Vapi (Voice AI) — **$50-100/mo usage-based**
- **Plan:** Pay-as-you-go (Ad-hoc)
- **Breakdown per minute:**
  - Vapi hosting: $0.05/min
  - STT (Deepgram): ~$0.01/min
  - LLM (Claude/GPT): ~$0.02-0.10/min
  - TTS: ~$0.01-0.04/min (built-in) or ElevenLabs
  - Telephony: ~$0.01/min (uses your Twilio)
- **True cost:** ~$0.13-0.25/min all-in
- **Free credit:** $10 on signup (~40-80 test minutes)
- **My recommendation:** Use Vapi's built-in voices initially to avoid ElevenLabs cost.

#### 8. ElevenLabs (Voice TTS) — **$5/mo or SKIP**
- **Plan:** Starter ($5/mo)
- **What you get:** 30,000 credits = ~30 min of TTS
- **Alternative:** Vapi includes lower-quality TTS for free
- **My recommendation:** SKIP initially. Only add if voice quality matters for demos.

---

## 🎯 Testing Phase Budget Scenarios

### Minimum Viable (Can test all channels): ~$115/mo
| Service | Plan | Cost |
|---------|------|------|
| Apollo | Free | $0 |
| Apify | Free | $0 |
| Stripe | Free | $0 |
| Postmark | Starter | $15 |
| ClickSend | PAYG (~200 SMS) | ~$15 |
| HeyReach | Free Trial | $0 |
| Vapi | PAYG (~200 mins) | ~$50 |
| ElevenLabs | Skip | $0 |
| **Total** | | **~$80/mo** |

### Comfortable Testing (More headroom): ~$200-250/mo
| Service | Plan | Cost |
|---------|------|------|
| Apollo | Free | $0 |
| Apify | Free | $0 |
| Stripe | Free | $0 |
| Postmark | Starter | $15 |
| ClickSend | PAYG (~500 SMS) | ~$35 |
| HeyReach | Starter | $79 |
| Vapi | PAYG (~500 mins) | ~$75 |
| ElevenLabs | Starter | $5 |
| **Total** | | **~$205/mo** |

### Ready for Founding Customers: ~$350-450/mo
| Service | Plan | Cost |
|---------|------|------|
| Apollo | Basic | $49 |
| Apify | Starter | $39 |
| Stripe | Free | $0 |
| Postmark | Growth | $25 |
| ClickSend | PAYG (~1000 SMS) | ~$70 |
| HeyReach | Starter | $79 |
| Vapi | PAYG (~1000 mins) | ~$150 |
| ElevenLabs | Creator | $11 |
| **Total** | | **~$413/mo** |

---

## ⚡ Quick Start Sequence

**Week 1: Core Setup (Free)**
1. Apollo — Sign up with corporate email → Free 10K credits
2. Apify — Create account → $5 free monthly credits
3. Stripe — Create account in Test Mode → All API keys immediately
4. Postmark — Start with free Developer tier (100 emails) for initial webhooks

**Week 2: Channels ($95)**
5. Postmark — Upgrade to $15 Starter when ready to test at volume
6. HeyReach — Start 14-day free trial with your LinkedIn account
7. ClickSend — Create account, get API credentials (pay-as-you-go SMS)

**Week 3: Voice ($50-100)**
8. Vapi — Create account → $10 free credit → Test with built-in voices
9. Twilio — Buy 1 AU number for voice → Link to Vapi (voice calls ONLY)
10. ElevenLabs — Only if Vapi's built-in TTS isn't good enough

**Pre-Launch: Scale as needed**
- Upgrade Apollo if you need phone numbers
- Upgrade Apify if heavy scraping
- ClickSend scales automatically (pay per SMS)
- Upgrade HeyReach if adding more LinkedIn senders

---

## 📝 Adding Variables

Add to `config/.env`:

```bash
# Example
APOLLO_API_KEY=your_key_here
```

Then verify:

```bash
cd C:\AI\Agency_OS
python scripts/check_env.py
```

---

## 🔒 Security Notes

- Never commit `.env` files to git (already in `.gitignore`)
- Use different keys for development vs production
- Rotate keys if compromised
- Store production secrets in Railway/Vercel environment settings
- Use Stripe Test Mode keys (sk_test_...) during development
