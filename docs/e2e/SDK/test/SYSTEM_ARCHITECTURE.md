# Agency OS System Architecture Map

**Generated:** 2026-01-19
**Purpose:** Complete system mapping for audit

---

## API Routes (17 files)

| File | Purpose | Critical for Audit |
|------|---------|-------------------|
| `leads.py` | Lead CRUD operations | **YES** |
| `pool.py` | Lead pool management | **YES** |
| `campaigns.py` | Campaign management | **YES** |
| `onboarding.py` | Client onboarding | **YES** |
| `webhooks.py` | Inbound webhooks (responses) | **YES** |
| `webhooks_outbound.py` | Outbound webhook handling | **YES** |
| `replies.py` | Reply processing | **YES** |
| `meetings.py` | Meeting booking | **YES** |
| `linkedin.py` | LinkedIn operations | **YES** |
| `health.py` | Health checks | YES |
| `admin.py` | Admin functions | YES |
| `reports.py` | Reporting | NO |
| `crm.py` | CRM integration | NO |
| `customers.py` | Customer management | NO |
| `campaign_generation.py` | Campaign generation | NO |
| `patterns.py` | Pattern learning | NO |

---

## Engines (18 files)

| File | Purpose | Layer | Critical for Audit |
|------|---------|-------|-------------------|
| `scorer.py` | ALS scoring | Core | **YES** |
| `scout.py` | Lead enrichment | Core | **YES** |
| `content.py` | Content generation | Core | **YES** |
| `email.py` | Email sending | Outreach | **YES** |
| `sms.py` | SMS sending | Outreach | **YES** |
| `voice.py` | Voice calls | Outreach | **YES** |
| `linkedin.py` | LinkedIn outreach | Outreach | **YES** |
| `mail.py` | Direct mail | Outreach | **YES** |
| `client_intelligence.py` | Client data scraping | Enrichment | **YES** |
| `icp_scraper.py` | ICP scraping | Enrichment | **YES** |
| `allocator.py` | Resource allocation | Utility | YES |
| `timing.py` | Timing optimization | Utility | YES |
| `closer.py` | Deal closing | Conversion | YES |
| `reporter.py` | Reporting | Utility | NO |
| `base.py` | Base classes | Utility | NO |
| `content_utils.py` | Content utilities | Utility | NO |
| `url_validator.py` | URL validation | Utility | NO |

---

## Integrations (22 files)

| File | Service | Purpose | Critical for Audit |
|------|---------|---------|-------------------|
| `apollo.py` | Apollo.io | Lead enrichment | **YES** |
| `apify.py` | Apify | LinkedIn/Web scraping | **YES** |
| `anthropic.py` | Anthropic | Claude AI | **YES** |
| `sdk_brain.py` | Anthropic SDK | Agent SDK | **YES** |
| `salesforge.py` | Salesforge | Email sending | **YES** |
| `twilio.py` | Twilio | SMS/Voice | **YES** |
| `clicksend.py` | ClickSend | SMS | **YES** |
| `vapi.py` | Vapi | Voice AI | **YES** |
| `elevenlabs.py` | ElevenLabs | TTS | **YES** |
| `unipile.py` | Unipile | LinkedIn automation | **YES** |
| `supabase.py` | Supabase | Database | **YES** |
| `redis.py` | Upstash Redis | Caching | YES |
| `heyreach.py` | HeyReach | LinkedIn (deprecated) | NO |
| `clay.py` | Clay | Enrichment (deprecated?) | NO |
| `postmark.py` | Postmark | Email (deprecated?) | NO |
| `resend.py` | Resend | Email (deprecated?) | NO |
| `serper.py` | Serper | Search | NO |
| `dataforseo.py` | DataForSEO | SEO data | NO |
| `dncr.py` | DNCR | Do Not Call Registry | YES |
| `sentry_utils.py` | Sentry | Error tracking | NO |
| `camoufox_scraper.py` | Camoufox | Stealth scraping | NO |

---

## Orchestration Flows (12 files)

| File | Purpose | Critical for Audit |
|------|---------|-------------------|
| `onboarding_flow.py` | Client onboarding + ICP | **YES** |
| `pool_population_flow.py` | Lead pool population | **YES** |
| `pool_assignment_flow.py` | Lead assignment to campaigns | **YES** |
| `lead_enrichment_flow.py` | Lead enrichment waterfall | **YES** |
| `outreach_flow.py` | Outreach execution | **YES** |
| `campaign_flow.py` | Campaign management | **YES** |
| `reply_recovery_flow.py` | Reply handling | **YES** |
| `intelligence_flow.py` | Conversion intelligence | YES |
| `pattern_learning_flow.py` | Pattern detection | YES |
| `pattern_backfill_flow.py` | Pattern backfill | NO |
| `enrichment_flow.py` | Enrichment (older?) | NO |

---

## Data Flow Overview

```
1. INGESTION
   └── API: leads.py, pool.py
       └── DB: lead_pool table

2. ENRICHMENT (Pre-ALS)
   └── Flow: pool_population_flow.py
       └── Integration: apollo.py → Person/Company data
       └── Integration: apify.py → LinkedIn scraping
       └── Engine: scout.py → Enrichment orchestration

3. SCORING (ALS)
   └── Engine: scorer.py
       └── Components: Title, Industry, Size, Tech, Intent, LinkedIn
       └── Output: ALS score (0-100), Tier (Hot/Warm/Cool/Cold/Dead)

4. ASSIGNMENT
   └── Flow: pool_assignment_flow.py
       └── DB: lead_assignments table
       └── Engine: allocator.py → Resource allocation

5. CONTENT GENERATION
   └── Engine: content.py
       └── Hot (85+): SDK (Sonnet) via sdk_brain.py
       └── Warm (60-84): Haiku via anthropic.py
       └── Cool (35-59): Haiku (limited)
       └── Cold (20-34): Templates only

6. OUTREACH EXECUTION
   └── Flow: outreach_flow.py
       └── Engine: email.py → salesforge.py
       └── Engine: sms.py → twilio.py / clicksend.py
       └── Engine: voice.py → vapi.py + elevenlabs.py
       └── Engine: linkedin.py → unipile.py
       └── Engine: mail.py → (PostGrid?)

7. RESPONSE HANDLING
   └── API: webhooks.py, replies.py
       └── Flow: reply_recovery_flow.py
       └── Status updates: interested, not_interested, meeting_booked, etc.

8. CONVERSION
   └── Engine: closer.py
       └── Flow: intelligence_flow.py
```

---

## ALS Tier Definitions

| Tier | Score Range | Treatment |
|------|-------------|-----------|
| **Hot** | 85-100 | SDK enrichment (if signals), SDK email, SDK voice KB |
| **Warm** | 60-84 | Haiku content, full channel access |
| **Cool** | 35-59 | Haiku content (limited), email + LinkedIn only |
| **Cold** | 20-34 | Template only, email only |
| **Dead** | <20 | No outreach |
