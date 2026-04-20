# FM Pipeline Recommendation — 100 Facilities Managers, AU

**Date:** 2026-04-19
**Callsign:** elliot
**Directive:** FM-PATH-ADVICE
**Status:** Advice only — no code

---

## Step 1 — Recommended Pipeline

### Overview

ContactOut search-first pipeline. No GMB discovery (FMs don't own businesses on Google Maps). No ABN lookup. No Gemini comprehension. Inverted from Pipeline F at every stage.

**Target:** 100 Facilities Managers with LinkedIn URL + email + phone
**Input list:** ~500 companies across 8 sectors (overshoot 5x for yield)
**Output:** Single CSV

---

### Stage 1 — Company List Assembly (MANUAL + DFS)

**What:** Build a target list of ~500 AU companies across the 8 sectors Dave specified (multi-site retail, aged care, hospitals, universities, industrial/manufacturing, hotels/shopping centres, logistics, fitness chains).

**Tool:** Manual curation + DataForSEO `domain_metrics_by_categories` for sector discovery.

**Rationale:** Pipeline F uses GMB discovery — that finds SMBs with physical shopfronts. FMs work at enterprises, chains, and institutions. These don't appear in GMB search for "facilities manager." Instead, we need domain lists by industry. DFS category codes give us organic-ranked AU domains per sector.

**Rejected:** GMB discovery (FMs aren't GMB-listed businesses), LinkedIn Recruiter search (Dave doesn't have a Recruiter seat), Apollo (dead reference).

**Cost:** DFS `domain_metrics_by_categories` = $0.10 + $0.001/domain AUD per category call. 8 sectors × 1 call = $0.81 AUD. Manual curation cost = $0 (Dave or bot compiles known names: Bunnings, Mirvac, IRT Group, Ramsay Health, etc.).

**Yield:** ~500 companies. No drop-off — input is curated, not discovered.

---

### Stage 2 — DM Discovery via ContactOut Search

**What:** For each company, search ContactOut for "Facilities Manager" + company name + "Australia".

**Tool:** ContactOut `/v1/people/search` (uses SEARCH credits, 2,447 available)

**Rationale:** This is the critical inversion from Pipeline F. Pipeline F discovers domains first, then finds DMs via LinkedIn company page scraping + Gemini extraction. For this job, we START with the DM title and SEARCH for people directly. ContactOut search accepts title + company + location — no LinkedIn URL needed. Returns profiles with LinkedIn URL, full name, title, company, experience.

**Rejected:** Bright Data LinkedIn People dataset (slower, ~24h turnaround for dataset snapshots, more expensive). LinkedIn Sales Navigator (no seat). Gemini comprehension (no website to comprehend — we need people, not companies).

**Cost:** 1 search credit per page (25 results). At 500 companies, ~500-1000 search credits. Budget: 1,000 credits × 1 credit each = 1,000 SEARCH credits consumed of 2,447 available. $0 AUD incremental (credits already purchased).

**Yield:** Based on ContactOut test data (ceo:contactout_search_endpoint): 2-10 results per company for common titles. "Facilities Manager" is a standard title. Expect ~60-70% company hit rate = 300-350 companies with FM results. Multiple FMs per large company. Expected: 400-600 raw FM profiles from 500 companies.

---

### Stage 3 — Dedupe + Filter

**What:** Deduplicate by LinkedIn URL. Filter to senior/head FM roles where multiple per company. Limit to 1-2 per company to reach 100 without over-concentrating.

**Tool:** Python script (in-memory, no API calls)

**Cost:** $0

**Yield:** ~300 unique FMs → select top ~150 for enrichment (overshoot for enrichment attrition)

---

### Stage 4 — Email Enrichment

**What:** Get verified email for each FM.

**Tool chain (waterfall):**
1. **Hunter email-finder** (free tier: 25/mo, or paid) — input: full name + company domain. Returns email + confidence score.
2. **Leadmagic** ($0.015/email, 2,494 credits available) — fallback for Hunter misses.
3. **Prospeo** (find_email MCP tool available) — tertiary fallback.

**Why NOT ContactOut email:** 0 email credits. Purchasing would work but Dave hasn't actioned the top-up.

**Rejected:** ContactOut enrich for email (0 credits). ZeroBounce (verification only, not discovery — and likely inactive). Gemini extraction from websites (slow, unreliable for enterprise contact pages).

**Cost:**
- Hunter: $0 (free tier) or ~$0.015 AUD/lookup if paid
- Leadmagic: $0.015 × 150 = $2.33 AUD (if all fall to Leadmagic)
- Prospeo: ~$0.03/lookup as last resort
- Blended estimate: $2.50 AUD total

**Yield:** Estimate with wide confidence interval: 40-85%. D2.2 showed 74% ContactOut email match but on 12 SMBs, not enterprise FMs. Enterprise FM email footprint is untested — could be better (corporate domains well-indexed) or worse (FMs less publicly listed than CEOs/owners). Will re-baseline after first 20 processed. Conservative planning: 60% = 90 emails from 150 attempts; expand company list if short.

---

### Stage 5 — Phone Enrichment

**What:** Get direct phone/mobile for each FM.

**Tool chain:**
1. **ContactOut enrich** (uses PHONE credits, 608 available) — input: LinkedIn URL from Stage 2. Returns phone.
2. **Leadmagic mobile** ($0.077/lookup) — fallback.

**Rationale:** ContactOut phone credits are available (608) and we already have LinkedIn URLs from Stage 2. This is the cheapest path to AU mobiles. D2.2 showed 100% AU mobile hit rate on ContactOut (3/3 DMs).

**Cost:**
- ContactOut phone: 150 lookups × 1 phone credit = 150 credits consumed (608 available). $0 incremental.
- Leadmagic fallback: $0.077 × 30 (est. misses) = $2.31 AUD
- Blended: ~$2.50 AUD total

**Yield:** ContactOut AU mobile rate was 100% in small sample, 50% in 20-sample test. Conservative for enterprise: 50-60%. With Leadmagic fallback: ~70-80%. Expect: 105-120 phones from 150 attempts.

---

### Stage 6 — CSV Assembly

**What:** Merge all data into final CSV: Full Name, Title, Company, LinkedIn URL, Email, Phone, Sector.

**Tool:** Python script

**Cost:** $0

**Yield:** 100 complete records (LinkedIn + email + phone). If yield is short, go back to Stage 2 and expand company list.

---

### Summary Table

| Stage | Tool | Cost/unit AUD | Units | Total AUD | Yield |
|-------|------|--------------|-------|-----------|-------|
| 1. Company list | DFS categories + manual | $0.10/call | 8 | $0.81 | 500 companies |
| 2. DM discovery | ContactOut search | $0 (prepaid) | 1,000 credits | $0 | 400-600 FMs |
| 3. Dedupe/filter | Python | $0 | — | $0 | 150 selected |
| 4. Email | Hunter + Leadmagic | ~$0.017/avg | 150 | $2.50 | 100-115 emails |
| 5. Phone | ContactOut phone + Leadmagic | ~$0.017/avg | 150 | $2.50 | 105-120 phones |
| 6. CSV | Python | $0 | — | $0 | 100 complete |
| **TOTAL** | | | | **~$5.81 AUD** | **100 records** |

**Cost per complete FM record: ~$0.06 AUD**

**Wall-clock time:** Realistic: 5-10 hours day-spread. Manual curation of company list: 30 min if Dave provides sector anchors, 4-6 hours if bot researches from scratch (verified AU presence + active facilities across 8 sectors). ContactOut search at 1000 calls × 5-10s = 1.5-3 hours. Email + phone enrichment: 1-2 hours. Dave should plan day-spread, not half-day.

---

### Risks + Failure Modes

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| "Facilities Manager" title not standard at target companies | Medium | Also search: "Facility Manager", "FM", "Building Services Manager", "Property Manager", "Maintenance Manager" — multiple title variants per company |
| ContactOut search returns 0 for some companies | Low-Medium | Enterprise companies well-covered in ContactOut DB. Fallback: LinkedIn company page scrape via Bright Data ($0.0015/profile) |
| Email credits exhausted mid-run | Low | Leadmagic has 2,494 credits — more than enough as primary + fallback |
| Phone credits exhausted | Low | 608 available, need ~150. Ample headroom |
| Duplicate FMs across company subsidiaries | Medium | Dedupe by LinkedIn URL resolves this cleanly |
| **Blocklist inversion** (Aiden catch) | **High if missed** | Our domain_blocklist.py (1515 entries) now blocks hospitals, retail chains, education, fitness chains — exactly the sectors Dave wants. One-shot script must NOT import or call `is_blocked()`. Pipeline F patterns leak this gate. |

---

### What's Different vs Pipeline F

| Dimension | Pipeline F | FM Job |
|-----------|-----------|--------|
| Discovery | GMB → domain → company | Company list → people search |
| ICP | SMBs with websites | Enterprises, chains, institutions |
| DM finding | Website scrape → Gemini → LinkedIn verify | Direct title search via ContactOut |
| ABN lookup | Yes (AU business verification) | No (enterprises don't need ABN proof) |
| Comprehension | Gemini F3a/F3b | None needed |
| Scoring (CIS/ALS) | Yes (12-stage scoring) | No (all FMs are targets) |
| Email path | ContactOut → Hunter → Leadmagic | Hunter → Leadmagic → Prospeo (no CO email credits) |
| Output | Supabase cards + outreach flow | Single CSV, one-shot |

---

## Step 2 — Rejected Alternatives

### Alt A — Pipeline F with Inverted Filters

**Design:** Run Pipeline F as-is but change discovery to target enterprise domains and DM title to "Facilities Manager."

**Rejected because:**
- Pipeline F starts with GMB discovery — FMs aren't on Google Maps
- ABN lookup, Gemini comprehension, CIS scoring are all wasted stages for this job
- Pipeline F writes to Supabase pipeline tables — unnecessary for a CSV deliverable
- Pipeline F has no title-based search — it discovers DMs by scraping LinkedIn company pages, which is expensive ($0.0015/profile via Bright Data) and slow (24h dataset turnaround)
- Cost would be ~$0.56/card (D2.2 rate) × 100 = $56 AUD vs $5.81 AUD recommended path. 10x more expensive for worse discovery.

### Alt B — Bright Data LinkedIn People Dataset

**Design:** Use Bright Data's LinkedIn People dataset to find FMs by title + location + industry. Skip ContactOut entirely.

**Rejected because:**
- Bright Data dataset snapshots take 12-24 hours to deliver (vs ContactOut search in seconds)
- Cost is $0.0015/profile but you need to search broadly first — dataset discovery queries are priced separately
- No email/phone in Bright Data people profiles — still need ContactOut/Hunter/Leadmagic for enrichment
- ContactOut search gives us the same data (name, title, company, LinkedIn URL) in real-time at $0/incremental (prepaid credits)

### Alt C — Manual LinkedIn Search + Scraping

**Design:** Manually search LinkedIn for "Facilities Manager" in each sector, export results, scrape profiles.

**Rejected because:**
- LinkedIn rate-limits manual search to ~100 results per query
- No API access without Sales Navigator ($99/mo USD) or Recruiter ($170/mo USD)
- Scraping LinkedIn directly violates ToS and risks account ban
- ContactOut search is a legal API that returns the same data

---

## Step 3 — Open Questions for Dave

1. **Company list source:** Do you have a list of target companies, or should I build one from DFS category data + manual research? A seed list of 10-20 anchor companies per sector would speed this up significantly.

2. **Hunter paid tier:** Are we on Hunter's free plan (25 searches/mo) or paid? If free, Leadmagic becomes the primary email source. Not a blocker — just changes the waterfall priority.

3. **Title variants:** Is "Facilities Manager" the exact title, or should we also search "Property Manager", "Building Services Manager", "Maintenance Manager", "Operations Manager"? Broader titles = more results but lower precision.

4. **ContactOut email credits:** If you purchase email credits from Sami before we start, ContactOut becomes the email source too (two-step: search → enrich with email). This would simplify the pipeline and likely improve email hit rate from 65-75% to 74%+ (matching D2.2 validation data). ~500 credits would cover this job. Not a blocker — Hunter + Leadmagic work without it.

5. **Dedup against existing BU:** Should we exclude companies already in `business_universe`? Or is this job completely separate from Pipeline F prospects?

6. **Timeline:** When does the client need the CSV? If same-day, I start immediately. If 2-3 days, I can run broader title variants and cherry-pick.

7. **Output schema (Aiden flag):** CSV columns currently: Name, Title, Company, LinkedIn URL, Email, Phone, Sector. Does the test-and-tag client also need: site count, primary facility address, FM seniority/reporting level? Cheap to add if known at search time.
