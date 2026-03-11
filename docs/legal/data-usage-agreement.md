# Agency OS — Data Usage Agreement

**Version:** 1.0 (Draft)
**Effective Date:** [TO BE SET ON LAUNCH]
**Last Updated:** 2026-03-11
**Directive:** #175

> This Data Usage Agreement ("DUA") is referenced in the Agency OS onboarding process. It forms part of your agreement with Agency OS and should be read together with the Terms of Service and Privacy Policy.

> **LEGAL REVIEW REQUIRED** before publication. This is a working draft for legal counsel review.

---

## 1. What This Agreement Covers

This DUA explains:
- What data Agency OS collects about you, your business, and your prospects
- How that data is used, stored, and protected
- Your rights and controls over that data
- How long data is retained
- Who has access and which third-party processors are used

---

## 2. Data We Collect About You (the Agency)

### 2.1 Onboarding — Website Analysis

When you submit your website URL for ICP extraction:
- We scrape publicly available content from your website (text, headings, meta descriptions, service descriptions)
- We extract social media URLs (LinkedIn, Instagram, Facebook, Twitter/X) from your site
- We use AI (Claude API, Anthropic) to generate your Ideal Customer Profile from scraped content
- **Stored in:** `clients` table (Supabase), `agency_service_profile` table
- **Retention:** Duration of subscription + 30 days post-cancellation
- **Consent:** Explicit — you provide your website URL and initiate the scrape

### 2.2 Onboarding — LinkedIn Connection

When you connect your LinkedIn account(s) via Unipile:
- We store a Unipile account ID (not your LinkedIn credentials)
- Your LinkedIn credentials are held by Unipile, not Agency OS
- We use your connected account(s) to send LinkedIn connection requests and messages to Prospects
- We do **not** read your LinkedIn inbox, connections list, or profile data
- **Stored in:** `unipile_accounts` table
- **Retention:** Until you revoke the connection or cancel
- **Consent:** Explicit — you complete Unipile's hosted OAuth flow

[LEGAL REVIEW REQUIRED — LinkedIn Terms of Service compliance for automated outreach via Unipile]

### 2.3 Onboarding — CRM Connection

When you connect your CRM (HubSpot):
- We perform a read-only audit of your CRM to identify existing clients and active deals
- Data read: contact records, deal records, deal values, engagement history, line items
- Purpose: Build your exclusion list (we never contact your existing clients)
- **Stored in:** `agency_crm_configs` table (connection config only); exclusion list stored in Supabase
- **Retention:** Connection config retained until revoked; exclusion list refreshed on each CRM sync
- **Consent:** Explicit — you complete HubSpot OAuth and are shown requested scopes

---

## 3. Data We Collect About Prospects

### 3.1 Discovery (T0 — Google My Business)

Collected via Bright Data Web Scraper API from Google Maps public listings:
- Business name
- Physical address and postcode
- Phone number
- Website URL
- GMB category
- Star rating and review count
- Google Place ID

**Source:** Public Google Maps listings
**Stored in:** `business_universe` table, `leads` table
**Consent basis:** [LEGAL REVIEW REQUIRED — whether scraping public GMB data requires notification under APP 5]

### 3.2 Verification (T1 — ABN Lookup)

Collected via Australian Business Register (data.gov.au) free API:
- ABN (11-digit identifier)
- Legal entity name
- All registered trading names (ASIC business names)
- ABN status (active/cancelled)
- GST registration status
- Entity type (company, trust, individual, partnership, etc.)
- Registered state and postcode

**Source:** Australian Business Register (government public data)
**Stored in:** `business_universe` table
**Consent basis:** Public government register — no consent required for business entities. [LEGAL REVIEW REQUIRED — sole trader ABN records that may identify individuals]

### 3.3 Supplemental GMB/SERP Data (T1.5a)

If phone or website missing after T0, collected via Bright Data SERP API:
- Phone number
- Website URL
- Business address
- Trading hours

**Source:** Google Search/Maps results (public)
**Stored in:** `leads` table

### 3.4 LinkedIn Company Data (T2 — Bright Data)

Collected via Bright Data LinkedIn Company Scraper:
- Company LinkedIn URL
- Company size (employee range)
- Industry
- Follower count
- Company description
- Specialties
- Headquarters location
- Founded year
- Company website

**Source:** Public LinkedIn company pages
**Stored in:** `leads` table, `business_universe` table
**Consent basis:** [LEGAL REVIEW REQUIRED — LinkedIn ToS on automated data collection; Privacy Act APP 3 on sensitive information]

### 3.5 Decision Maker Data (T2.5 — Bright Data LinkedIn Profile)

Collected via Bright Data LinkedIn People Scraper:
- Decision maker full name
- Current job title
- LinkedIn profile URL
- Location
- Professional summary
- Employment history (current role focus)
- Connections count
- Education (name/institution only)

**Source:** Public LinkedIn profiles
**Stored in:** `business_decision_makers` table
**Retention:** 90 days from enrichment; re-verified at campaign time
**Mobile:** Never stored — live lookup at campaign time only (T5)
**Consent basis:** [LEGAL REVIEW REQUIRED — APP 3; LinkedIn profile scraping; whether public profiles imply consent to commercial contact]

### 3.6 Email (T3 — Leadmagic)

Collected via Leadmagic Email Finder API:
- Work email address
- Email confidence score (0-100)
- Email type (work/personal/generic)
- First name, last name
- LinkedIn URL (cross-reference)

**Source:** Leadmagic proprietary sources
**Stored in:** `business_decision_makers` table
**Retention:** 90 days from enrichment; re-verified at campaign time
**Consent basis:** [LEGAL REVIEW REQUIRED — Leadmagic's own consent basis for email data; Spam Act implications for collected emails]

### 3.7 Mobile Number (T5 — Leadmagic)

Collected via Leadmagic Mobile Finder API (Hot leads only, ALS ≥ 85):
- Direct mobile number
- Mobile confidence score
- Personal email (if available)

**Source:** Leadmagic proprietary sources
**NOT STORED** — Live lookup at campaign time only. Not cached.
**DNCR check:** All mobile numbers are checked against the Australian Do Not Call Register (via ACMA API) before any SMS or voice contact. Numbers on the DNCR are suppressed automatically.
**Consent basis:** [LEGAL REVIEW REQUIRED — Leadmagic mobile data sourcing; TCP Code; DNCR Act obligations]

### 3.8 Ad Spend Signal (T-DM0 — DataForSEO)

Collected via DataForSEO SERP API:
- Estimated ad spend
- Active ad platforms
- Keywords being bid on

**Source:** DataForSEO (aggregated from public ad auction data)
**Stored in:** `leads` table (propensity signal)
**Country:** DataForSEO infrastructure — [LEGAL REVIEW REQUIRED — cross-border data transfer; EU processors]

### 3.9 LinkedIn Posts — Decision Maker (T-DM2 — Bright Data)

Collected for Prospects with Propensity score ≥ 70:
- Last 90 days of public LinkedIn posts
- Post content, dates, engagement metrics

**Source:** Public LinkedIn posts
**Stored in:** `leads` table (temporary, for message personalisation)
**Retention:** Not retained after message generation
**Consent basis:** [LEGAL REVIEW REQUIRED — APP 3; whether aggregating and processing public posts constitutes profiling under Privacy Act]

### 3.10 X/Twitter Posts (T-DM3 — Bright Data)

Collected for Prospects with Propensity score ≥ 70:
- Last 90 days of public X/Twitter posts

**Source:** Public X posts
**Stored in:** `leads` table (temporary, for message personalisation)
**Retention:** Not retained after message generation

### 3.11 Facebook Page Posts (T-DM4 — Bright Data)

Collected for Prospects with Propensity score ≥ 70:
- Business Facebook page posts

**Source:** Public Facebook business pages
**Stored in:** `leads` table (temporary)
**Retention:** Not retained after message generation

---

## 4. ALS Scoring and Profiling

[LEGAL REVIEW REQUIRED — whether ALS scoring of individuals constitutes automated decision-making requiring disclosure under APP 1 or Privacy Act]

We calculate an Agency Lead Score (ALS) for each Prospect comprising:
- **Reachability Score** (0–100): Quality and completeness of contact data
- **Propensity Score** (0–100): AI-assessed likelihood to need your services, calibrated to your ICP

What Agencies see: Priority rank (1, 2, 3…) and a plain-English reason. Raw scores are not exposed.
What Prospects see: Nothing. Prospects are not informed of their ALS score.

The ALS algorithm and all weights are proprietary to Agency OS. No weights are published or disclosed.

---

## 5. Outreach Channels

### 5.1 Email (Salesforge)

- Outbound emails are sent from your connected warmed mailboxes via Salesforge
- Tracking: Open tracking (pixel), click tracking (link rewriting), reply detection
- All tracked emails include an unsubscribe mechanism
- Unsubscribes are recorded in a suppression list and respected globally
- Bounces are recorded and the email address is flagged as invalid
- **Consent basis:** [LEGAL REVIEW REQUIRED — Spam Act 2003 — whether B2B cold email to business email addresses requires consent; "designated commercial electronic messages" exemption]

### 5.2 LinkedIn (Unipile)

- Connection requests and messages are sent from your connected LinkedIn account(s)
- Agency OS does not log or store the content of LinkedIn messages beyond send confirmation
- LinkedIn rate limits apply: 80–100 connection requests/day, 100–150 messages/day per seat
- **Consent basis:** [LEGAL REVIEW REQUIRED — LinkedIn ToS on automated messaging; whether LinkedIn message history is "personal information" under Privacy Act]

### 5.3 Voice AI — Alex (ElevenAgents + Telnyx)

[LEGAL REVIEW REQUIRED — all voice AI items]

- Outbound calls placed via Telnyx (Australian carrier) to Prospects' business phone numbers
- AI agent "Alex" conducts the call; it is not a human
- Calls are made only during permitted hours: 9am–8pm Monday–Friday, 9am–5pm Saturday, no Sundays (TCP Code)
- **AI Disclosure:** Alex introduces itself as an AI assistant at the start of every call
- **Recording:** Calls are recorded. Recordings are stored in `voice_calls` table
- **Transcript:** Calls are transcribed. Transcripts stored in `voice_calls` table
- **Sentiment analysis:** Call sentiment is analysed by AI
- **DNCR:** Business numbers are checked against DNCR before calling
- **Consent items requiring review:**
  - Whether recording consent disclosure is required in all Australian states
  - DNCR obligations for AI-initiated calls
  - TCP Code compliance for AI voice agents
  - Whether AI disclosure at call start satisfies all applicable requirements

### 5.4 SMS (Telnyx) — ON HOLD

- Not currently active; to be enabled closer to launch
- Will require DNCR check on all numbers before sending
- Will include STOP mechanism for opt-out
- [LEGAL REVIEW REQUIRED — Spam Act and TCP Code for commercial SMS; DNCR for SMS numbers]

---

## 6. Data Storage and Security

- **Primary database:** Supabase (PostgreSQL), hosted on AWS (region: ap-southeast-2 — Sydney)
- **Encryption at rest:** Yes (Supabase default AES-256)
- **Encryption in transit:** Yes (TLS 1.2+)
- **Access controls:** Row-level security (RLS) enforced per agency tenant. No Agency can access another Agency's data.
- **Multi-tenancy isolation:** All queries are scoped by `client_id`. Cross-tenant data access is prevented at the database layer.
- **Redis cache:** Used for DNCR check caching and temporary state. Not used for persistent storage of personal information.
- [LEGAL REVIEW REQUIRED — cross-border data transfer to non-AU processors (DataForSEO, ElevenLabs, Bright Data, Leadmagic, Salesforge)]

---

## 7. Your Controls

### 7.1 Manual Mode

You can operate campaigns in Manual Mode, where every outreach action is queued for your review and approval before sending.

### 7.2 Kill Switch

You can pause or stop any campaign at any time from the dashboard.

### 7.3 Exclusion List

Your CRM exclusion list is automatically applied to all campaigns. You can also manually add businesses or individuals to your exclusion list.

### 7.4 Data Export

You can export your campaign data, lead enrichment data, and outcome records at any time from the dashboard.

### 7.5 Integration Revocation

You can revoke your LinkedIn or CRM connection at any time. Revocation immediately stops outreach via that channel.

### 7.6 Data Deletion

You may request immediate deletion of all your data by written notice. We will delete your data within 5 business days. This does not affect anonymised aggregate data used in the CIS model.

---

## 8. Retention and Deletion

| Data Type | Retention Period |
|-----------|-----------------|
| Agency account data | Duration of subscription + 30 days |
| Campaign data | Duration of subscription + 30 days |
| Prospect enrichment data | 90 days from enrichment (contact fields); GMB/ABN data indefinitely in Business Universe |
| Mobile numbers | Never stored (live lookup only) |
| Voice call recordings and transcripts | 90 days from call date |
| LinkedIn post content | Deleted after message generation |
| Suppression list (unsubscribes/opt-outs) | Retained indefinitely (legal compliance) |
| Anonymised CIS training data | Retained indefinitely (no personal identifiers) |

---

## 9. Sub-Processors

| Provider | Purpose | Country | Data Transferred |
|---------|---------|---------|-----------------|
| Supabase (AWS ap-southeast-2) | Database | Australia | All Agency and Prospect data |
| Bright Data | LinkedIn, GMB, social scraping | Israel (infrastructure global) | Prospect profile data |
| Leadmagic | Email and mobile finding | [Country TBC] | DM name, company, LinkedIn URL |
| DataForSEO | Ad spend signals | Ukraine/Global | Business name, domain |
| Salesforge | Email sending | [Country TBC] | Recipient email, message content |
| ElevenLabs/ElevenAgents | Voice AI synthesis and conversation | USA | Call transcripts, voice data |
| Telnyx | Call/SMS carrier | USA | Phone numbers, call records |
| Unipile | LinkedIn automation | France | LinkedIn account token |
| Anthropic (Claude API) | AI content generation, ICP extraction | USA | Website content, prospect signals |
| Stripe | Payment processing | USA | Agency billing data |
| HubSpot | CRM integration (read) | USA | Agency CRM records |

[LEGAL REVIEW REQUIRED — cross-border transfer mechanisms for each non-AU processor; whether standard contractual clauses or other safeguards are in place]

---

## 10. Business Universe and House Seed

### 10.1 Business Universe

Your campaign Prospects are sourced from Agency OS's Business Universe — a database of ~2.5 million verified active Australian businesses. This database is built from public government data (ABN register) and public Google My Business listings.

When your campaign runs, Agency OS selects Prospects from the Business Universe that match your ICP. Prospect data enrichment costs are covered by your subscription.

### 10.2 House Seed

Up to 10% of each campaign's lead volume may consist of "house seed" — prospects targeted for Agency OS's own business development. House seed leads are disclosed to you before each campaign launch. You may opt out of house seed inclusion upon request.

---

## 11. Changes to This Agreement

Agency OS will notify you of material changes to this DUA at least 30 days before they take effect. Continued use of the Platform constitutes acceptance. If you do not accept material changes, you may cancel your subscription before the effective date.

---

*Draft prepared: 2026-03-11 | CEO Directive #175 | [LEGAL REVIEW REQUIRED before publication]*
