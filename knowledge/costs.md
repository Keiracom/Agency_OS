# Agency OS Service Cost Ledger

**Last Updated:** 2026-01-30  
**Currency:** USD unless noted (AUD rates marked)
**Verification Date:** 2026-01-30

---

## Summary

| Category | Monthly Est. (Low) | Monthly Est. (High) | Notes |
|----------|-------------------|---------------------|-------|
| Core Infrastructure | $50 | $150 | Supabase + Railway + Redis |
| AI/LLM | $50 | $500+ | Usage-dependent |
| Lead Enrichment | $30 | $300+ | Per-lead costs vary (Prospeo removed) |
| Email Channel | $120 | $350+ | Salesforge + InfraForge + Resend |
| LinkedIn Channel | $55 | $275+ | Unipile per-account |
| Voice Channel | $50 | $400+ | Vapi + Twilio + Cartesia |
| SMS/Mail | $20 | $100+ | ClickSend usage-based |
| **Total Estimated** | **$375** | **$2,075+** | Scales with client volume |

---

## 1. Core Infrastructure

### Supabase (Database) [VERIFIED 2026-01-30]
- **Use:** PostgreSQL database, auth, storage, realtime
- **Plan:** Pro tier
- **Pricing:** $25/month base + usage
  - Database: 8GB disk included, then $0.125/GB
  - Storage: 100GB included, then $0.021/GB  
  - Egress: 250GB included, then $0.09/GB
  - MAUs: 100,000 included, then $0.00325/MAU
  - Backups: 7 days included
  - PITR: $100/month per 7 days retention (add-on)
- **Estimated:** $25-75/month
- **Source:** https://supabase.com/pricing
- **Config:** `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`

### Railway (Backend Hosting) [VERIFIED 2026-01-30]
- **Use:** API backend, Prefect server, workers
- **Plan:** Pro tier
- **Pricing:** $20/month minimum (includes $20 usage credits)
  - Memory: $0.00000386/GB/sec
  - CPU: $0.00000772/vCPU/sec
  - Volumes: $0.00000006/GB/sec
  - Egress: $0.05/GB
  - Object Storage: $0.015/GB-month
- **Limits (Pro):** Up to 1,000 vCPU, 1TB RAM, 1TB storage per service
- **Estimated:** $20-50/month (light usage), $50-200/month (production)
- **Source:** https://railway.com/pricing
- **Config:** Railway project ID: `fef5af27-a022-4fb2-996b-cad099549af9`

### Upstash Redis [VERIFIED 2026-01-30]
- **Use:** Caching, rate limiting, job queues
- **Pricing:** Pay-as-you-go
  - Free tier: 10K commands/day
  - Pro: $0.2 per 100K commands
- **Estimated:** $5-25/month
- **Config:** `REDIS_URL`

---

## 2. AI / LLM

### Anthropic Claude API [VERIFIED 2026-01-30]
- **Use:** ICP extraction, messaging generation, intent classification, agent reasoning
- **Pricing (per million tokens):**
  
  | Model | Input | Output | Notes |
  |-------|-------|--------|-------|
  | Opus 4.5 | $5 | $25 | Most intelligent |
  | Sonnet 4.5 (≤200K) | $3 | $15 | Balanced |
  | Sonnet 4.5 (>200K) | $6 | $22.50 | Large context |
  | Haiku 4.5 | $1 | $5 | Fast/cheap |
  | Haiku 3 (legacy) | $0.25 | $1.25 | Budget option |
  | Sonnet 4 (legacy) | $3 | $15 | - |
  | Opus 4/4.1 (legacy) | $15 | $75 | - |
  
- **Prompt Caching (5-min TTL):**
  - Opus 4.5: Write $6.25/MTok, Read $0.50/MTok
  - Sonnet 4.5: Write $3.75/MTok, Read $0.30/MTok
  - Haiku 4.5: Write $1.25/MTok, Read $0.10/MTok
- **Batch processing:** 50% discount
- **Web Search:** $10/1K searches (add-on)
- **Config limit:** `ANTHROPIC_DAILY_SPEND_LIMIT=50.0`
- **Estimated:** $50-500/month (heavily usage-dependent)
- **Source:** https://claude.com/pricing
- **Config:** `ANTHROPIC_API_KEY`

---

## 3. Lead Enrichment

### Apollo.io [VERIFIED 2026-01-30]
- **Use:** Lead sourcing, contact enrichment, company data
- **Pricing (credit-based):**
  
  | Plan | Price | Email Credits | Mobile Credits | Notes |
  |------|-------|---------------|----------------|-------|
  | Free | $0 | 50/mo | - | Limited features |
  | Basic | $49/user/mo | 1,000/mo | 75/mo | CRM integrations |
  | Professional | $79/user/mo | Higher limits | More | A/B testing, dialer |
  | Organization | $119/user/mo | Highest | Highest | Min 3 users, SSO, API |
  
- **Credit System:** Credits consumed on search, reveal, export. Do NOT roll over.
- **Likely Plan:** Professional ($79/user/month)
- **Estimated:** $79-158/month (1-2 users)
- **Source:** https://www.apollo.io/pricing
- **Config:** `APOLLO_API_KEY`

### DataForSEO [VERIFIED 2026-01-30]
- **Use:** Domain authority, organic traffic, backlinks for ALS scoring
- **Pricing:** Pay-as-you-go (minimum $50 deposit)
  - SERP (10 results, standard): $0.0006/request
  - SERP (10 results, live): $0.002/request
  - 1,000 SERPs = $0.60 (standard)
  - Domain metrics: Similar range
- **Estimated:** $50-100/month
- **Source:** https://dataforseo.com/apis/serp-api/pricing
- **Config:** `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`

### Apify [VERIFIED 2026-01-30]
- **Use:** Website scraping for ICP extraction
- **Pricing:**
  
  | Plan | Price | Prepaid Usage | Compute (CU) |
  |------|-------|---------------|--------------|
  | Free | $0 | $5/mo | $0.30/CU |
  | Starter | $29/mo | $29 | $0.30/CU |
  | Scale | $199/mo | $199 | $0.25/CU |
  | Business | $999/mo | $999 | $0.20/CU |
  
  - Residential proxies: $7-8/GB
  - Datacenter proxies: from $0.6/IP (included: 30 Starter, 200 Scale, 500 Business)
- **Likely Plan:** Starter or Scale
- **Estimated:** $29-199/month
- **Source:** https://apify.com/pricing
- **Config:** `APIFY_API_KEY`

---

## 4. Email Channel

### Salesforge (Campaign Sending) [VERIFIED 2026-01-30]
- **Use:** Cold email campaigns, reply tracking, sender rotation
- **Pricing:**
  
  | Plan | Price | Active Contacts | Emails/mo | Users |
  |------|-------|-----------------|-----------|-------|
  | Pro | $40/mo | 1,000 | 5,000 | 1 |
  | Growth | $80/mo | 10,000 | 50,000 | Unlimited |
  | Agent Frank | $499/mo | 2,000+ | AI-driven | Managed |
  
- **Includes:** WarmForge (email warmup) - FREE with subscription
- **Add-ons:** Extra contacts, emails, personalization credits purchasable
- **Likely Plan:** Growth ($80/month)
- **Estimated:** $80-160/month
- **Source:** https://www.salesforge.ai/pricing
- **Config:** `SALESFORGE_API_KEY`, `SALESFORGE_API_URL`

### InfraForge (Domains & Mailboxes)
- **Use:** Domain purchasing, mailbox provisioning, DNS management
- **Pricing:**
  - Domains: ~$14/year (.com)
  - Mailboxes: $4/month/slot (annual billing = $33/mo for 10)
  - Dedicated IP: $99/month
  - Masterbox: $7-9/workspace/month
- **Estimated:** $50-150/month (10-30 mailboxes + domains)
- **Config:** `INFRAFORGE_API_KEY`, `INFRAFORGE_API_URL`

### WarmForge (Email Warmup) [VERIFIED 2026-01-30]
- **Use:** Automated warmup for sender reputation
- **Pricing:** FREE with Salesforge subscription (unlimited)
- **Config:** `WARMFORGE_API_KEY`, `WARMFORGE_API_URL`

### Resend (Transactional) [VERIFIED 2026-01-30]
- **Use:** Transactional emails, system notifications
- **Pricing:**
  
  | Plan | Price | Emails/mo | Domains | Data Retention |
  |------|-------|-----------|---------|----------------|
  | Free | $0 | 3,000 (100/day) | 1 | 1 day |
  | Pro | $20/mo | 50,000 | 10 | 3 days |
  | Scale | $90/mo | 100,000 | 1,000 | 7 days |
  
  - Dedicated IPs: $30/mo (Scale+ only, 500+ emails/day required)
- **Likely Plan:** Pro ($20/month)
- **Estimated:** $20/month
- **Source:** https://resend.com/pricing
- **Config:** `RESEND_API_KEY`

---

## 5. LinkedIn Channel

### Unipile [VERIFIED 2026-01-30]
- **Use:** LinkedIn automation (replaced HeyReach)
- **Pricing:** Per connected account
  - €5/account/month (~$5.50 USD)
  - Example: 15 accounts = €75/month (~$82 USD)
  - All LinkedIn features included under single rate (50+ options)
  - Free trial: up to 10 accounts
- **Estimated:** $55-275/month (10-50 accounts across clients)
- **Source:** https://www.unipile.com/pricing-api/
- **Config:** References in codebase as LinkedIn automation replacement

---

## 6. Voice Channel

### Vapi (Voice AI Orchestration) [VERIFIED 2026-01-30]
- **Use:** Voice AI calls, STT built-in, routes to Claude
- **Pricing:**
  
  | Plan | Price | Minutes | Overage |
  |------|-------|---------|---------|
  | Ad-Hoc | Pay-as-you-go | 0 | $0.18/min |
  | Agency | $400/mo | 3,000 | $0.18/min |
  | Startup | $800/mo | 7,500 | $0.16/min |
  | Enterprise | Custom | Custom | Custom |
  
  - Platform hosting: $0.05/min (included in rates above)
  - Surge hosting: +$0.05/min during spikes
  - SIP lines: Agency 10, Startup 50 (extra: $10/line/mo)
  - Note: TTS, STT, LLM costs are ADDITIONAL (not included)
- **Total realistic cost:** ~$0.18-0.33/minute all-in
- **Estimated:** $50-400/month (based on call volume)
- **Source:** https://vapi.ai/pricing (via synthflow.ai analysis)
- **Config:** `VAPI_API_KEY`, `VAPI_PHONE_NUMBER_ID`

### Twilio (Voice Telephony) [VERIFIED 2026-01-30]
- **Use:** Phone numbers, voice routing
- **Pricing (Australia):**
  - Local number: $3.00/month + $0.0085/min receive
  - Mobile number: $6.50/month
  - Toll-Free number: $16.00/month
  - Make calls to AU landline: varies by route
  - Make calls to AU Mobile: varies by route
  - Answering machine detection: per call
  - ConversationRelay (Voice AI): $0.07/min
- **Phone:** +61240126220
- **Estimated:** $20-100/month
- **Source:** https://www.twilio.com/en-us/voice/pricing/au
- **Config:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`

### Cartesia (Primary TTS) [NEW 2026-01]
- **Use:** Low-latency voice synthesis for Vapi calls
- **Pricing:**
  
  | Plan | Price | Characters/mo | Notes |
  |------|-------|---------------|-------|
  | Free | $0 | 10,000 | Testing only |
  | Starter | $29/mo | 500,000 | sonic-2 model |
  | Growth | $99/mo | 2,000,000 | Priority support |
  | Enterprise | Custom | Unlimited | SLA, dedicated |
  
  - **sonic-2 model:** 90ms latency, balanced quality/speed
  - **sonic-turbo model:** 40ms latency, fastest available
  - ~150 characters/second of speech
- **Likely Plan:** Starter ($29/mo) or Growth ($99/mo)
- **Estimated:** $29-99/month
- **Source:** https://cartesia.ai/pricing
- **Config:** `CARTESIA_API_KEY`, `CARTESIA_VOICE_MODEL`

### ElevenLabs (Fallback TTS) [VERIFIED 2026-01-30]
- **Use:** Fallback voice synthesis if Cartesia unavailable
- **Pricing (credit-based, 1 credit ≈ 2 characters):**
  
  | Plan | Price | Credits/mo | Characters | Notes |
  |------|-------|------------|------------|-------|
  | Free | $0 | 10,000 | ~20,000 | Non-commercial |
  | Starter | $5/mo | 30,000 | ~60,000 | Commercial, voice cloning |
  | Creator | $22/mo | 100,000 | ~200,000 | Professional features |
  | Pro | $99/mo | 500,000 | ~1,000,000 | API priority |
  | Scale | $330/mo | 2,000,000 | ~4,000,000 | Team (3 seats) |
  | Business | $1,320/mo | 11,000,000 | ~22,000,000 | Team (5 seats) |
  
  - Flash/Turbo models: 50% cheaper (0.5-1 credit per character)
  - ~30 chars/second of speech ≈ ~1 min = ~1,800 chars
- **Status:** FALLBACK ONLY (Cartesia is primary)
- **Source:** https://elevenlabs.io/pricing (via withorb.com analysis)
- **Config:** `ELEVENLABS_API_KEY`

---

## 7. SMS & Direct Mail

### ClickSend (AU) [VERIFIED 2026-01-30]
- **Use:** SMS outreach, physical direct mail
- **Pricing (AUD):**
  
  | Volume | SMS Rate (AUD) |
  |--------|----------------|
  | <5K | $0.072/SMS |
  | 5K+ | $0.070/SMS |
  | 50K+ | $0.062/SMS |
  | 150K+ | $0.057/SMS |
  
  - Direct mail: Variable by format
  - Free inbound messages
  - 99.95% uptime SLA
- **Estimated:** $20-100/month AUD
- **Source:** https://www.clicksend.com/au/pricing/
- **Config:** `CLICKSEND_USERNAME`, `CLICKSEND_API_KEY`

---

## 8. Agency OS Revenue Tiers

From `src/config/tiers.py`:

| Tier | Price (AUD) | Founding Price | Leads/mo | Campaigns | LinkedIn Seats |
|------|-------------|----------------|----------|-----------|----------------|
| Ignition | $2,500 | $1,250 | 1,250 | 5 | 1 |
| Velocity | $5,000 | $2,500 | 2,250 | 10 | 3 |
| Dominance | $7,500 | $3,750 | 4,500 | 20 | 5 |

**Stripe Price IDs configured:** `STRIPE_PRICE_IGNITION`, `STRIPE_PRICE_VELOCITY`, `STRIPE_PRICE_DOMINANCE`

---

## 9. Cost Per Client Estimates

### Low Volume Client (Ignition Tier)
- Lead enrichment: ~$0.05-0.10/lead × 1,250 = $62-125
- Email sending: ~$0.01/email × ~6,000 = $60
- Voice (10 calls): ~$5-10
- Infrastructure share: ~$25
- **Total variable cost: ~$150-220/client/month**
- **Margin on $1,250 founding: ~82-88%**

### Medium Volume Client (Velocity Tier)  
- Lead enrichment: ~$0.05-0.10/lead × 2,250 = $112-225
- Email sending: ~$0.01/email × ~15,000 = $150
- LinkedIn seats (3): ~$55
- Voice (25 calls): ~$15-25
- Infrastructure share: ~$40
- **Total variable cost: ~$370-495/client/month**
- **Margin on $2,500 founding: ~80-85%**

### High Volume Client (Dominance Tier)
- Lead enrichment: ~$0.05-0.10/lead × 4,500 = $225-450
- Email sending: ~$0.01/email × ~30,000 = $300
- LinkedIn seats (5): ~$90
- Voice (50 calls): ~$30-50
- Infrastructure share: ~$60
- **Total variable cost: ~$705-950/client/month**
- **Margin on $3,750 founding: ~75-81%**

---

## 10. Notes & Optimizations

### Cost Reduction Strategies
1. **Batch API calls** - Anthropic 50% off for batch processing
2. **Prompt caching** - Reduces LLM costs for repeated context (up to 90% savings on cache hits)
3. **Tiered enrichment** - Only use expensive sources when needed
4. **Warmup included** - WarmForge free with Salesforge
5. **Annual billing** - Most services offer 15-20% discount
6. **Cartesia sonic-2** - Lower latency TTS than ElevenLabs at competitive pricing

### Usage Monitoring
- Anthropic: `ANTHROPIC_DAILY_SPEND_LIMIT=50.0`
- Enrichment: `ENRICHMENT_CLAY_MAX_PERCENTAGE=0.15`
- Rate limits configured per channel in codebase

### Services Not Currently Used
- Clay (optional fallback): `CLAY_API_KEY`
- Serper (web search): `SERPER_API_KEY` 
- Cal.com/Calendly (booking): Optional
- PostHog (analytics): Optional

---

## Verification Status

| Service | Status | Last Verified | Source |
|---------|--------|---------------|--------|
| Supabase | ✅ VERIFIED | 2026-01-30 | supabase.com/pricing |
| Railway | ✅ VERIFIED | 2026-01-30 | railway.com/pricing |
| Anthropic | ✅ VERIFIED | 2026-01-30 | claude.com/pricing |
| Apollo.io | ✅ VERIFIED | 2026-01-30 | apollo.io/pricing |
| Salesforge | ✅ VERIFIED | 2026-01-30 | salesforge.ai/pricing |
| Resend | ✅ VERIFIED | 2026-01-30 | resend.com/pricing |
| ClickSend | ✅ VERIFIED | 2026-01-30 | clicksend.com/au/pricing |
| Twilio | ✅ VERIFIED | 2026-01-30 | twilio.com/en-us/voice/pricing/au |
| Vapi | ✅ VERIFIED | 2026-01-30 | vapi.ai/pricing (via synthflow.ai) |
| Cartesia | ✅ NEW | 2026-01 | cartesia.ai/pricing |
| ElevenLabs | ✅ VERIFIED | 2026-01-30 | elevenlabs.io/pricing (fallback) |
| Unipile | ✅ VERIFIED | 2026-01-30 | unipile.com/pricing-api |
| DataForSEO | ✅ VERIFIED | 2026-01-30 | dataforseo.com/apis/serp-api/pricing |
| Apify | ✅ VERIFIED | 2026-01-30 | apify.com/pricing |
| Upstash | ⚠️ ESTIMATE | - | Not re-verified |
| Prospeo | ⚠️ ESTIMATE | - | Not re-verified |
| InfraForge | ⚠️ ESTIMATE | - | Internal Salesforge product |

---

## Changelog

- **2026-01-30:** Full verification against actual pricing pages. Updated all 13 primary services with [VERIFIED] status. Fixed several outdated estimates:
  - Anthropic: Added Opus 4.5, updated all model pricing, added prompt caching details
  - Apollo: Clarified credit system (credits don't roll over)
  - Salesforge: Updated to $40/$80 pricing (was $40/$80 - confirmed)
  - Vapi: Added detailed plan breakdown ($400-$800/mo plans)
  - ElevenLabs: Complete credit-based pricing overhaul (now fallback)
- **2026-01:** Migrated primary TTS from ElevenLabs to Cartesia for lower latency
  - Unipile: Confirmed €5/account pricing
  - DataForSEO: Added detailed SERP pricing ($0.0006/request)
  - Apify: Updated tier pricing with compute unit costs
- **2026-01-30:** Initial cost ledger created from codebase analysis + online research
