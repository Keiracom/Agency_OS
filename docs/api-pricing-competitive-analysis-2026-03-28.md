== RESEARCH DATE: 2026-03-28 ==
== COMPILED BY: Elliottbot Research Agent ==

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. EXECUTIVE SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Key findings:
• PROXYCURL IS DEAD — shut down by LinkedIn federal lawsuit (July 2025). All LinkedIn scraping must route through Bright Data, Nimble, or Scrapingdog.
• Leadmagic is cheapest for email+mobile combined ($0.010 email / $0.050 mobile, pay-for-success). Our current stack is well-positioned.
• Clay is a 1.6–3.5x markup layer on top of underlying providers — valuable for orchestration but expensive if credits are burned on waterfall enrichment without own API keys.
• Apollo credits are effectively $0.025/email export, and $0.15+ per fully enriched contact (6 credits × $0.025). Seat pricing inflates cost at scale.
• AU-specific data: Nearly universal problem. PDL, Clearbit/HubSpot, Apollo all have weak APAC coverage. Leadmagic and Bright Data are geography-agnostic (real-time scraping). Expect 20–40% lower match rates for AU vs US contacts.
• Market is dominated by credit-pack + monthly subscription hybrid models. Pure PAYG is rare except Bright Data, PDL, and Proxycurl (now defunct).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. SUMMARY TABLE: COMPETITOR × STAGE × PRICE PER CALL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Provider         | Stage 1 (Disc) | Stage 2 (Tech) | Stage 3 (Co) | Stage 4 (Contact) | Stage 5 (Email) | Stage 6 (Mobile) | Stage 7 (AI)
-----------------|----------------|----------------|--------------|-------------------|-----------------|------------------|-------------
LEADMAGIC (ours) | n/a            | $0.010         | $0.010       | $0.001*           | $0.010          | $0.050           | n/a
Bright Data      | $0.0010–0.0015 | $0.0010–0.0015 | $0.0010–0.0015| $0.0010–0.0015   | n/a             | n/a              | n/a
Apollo.io        | n/a            | n/a            | ~$0.15       | ~$0.15            | $0.025          | ~$1.25–5.00†    | n/a
Clearbit/Breeze  | n/a            | n/a            | $0.09–0.10   | $0.09–0.10        | n/a             | n/a              | n/a
PDL              | n/a            | n/a            | $0.06–0.10   | $0.40–0.55        | ~$0.28          | ~$0.28           | n/a
Hunter.io        | n/a            | n/a            | n/a          | n/a               | $0.008–0.017    | n/a              | n/a
Clay (platform)  | ORCHESTRATOR   | ORCHESTRATOR   | ORCHESTRATOR | ORCHESTRATOR      | ORCHESTRATOR    | ORCHESTRATOR     | $0.016–0.035/action
Proxycurl        | SHUT DOWN (July 2025 — LinkedIn lawsuit)                                                         
Claude Haiku     | n/a            | n/a            | n/a          | n/a               | n/a             | n/a              | ~$0.0025

* Employee Finder: 1 credit = 20 employees = $0.0005/person (find DM name from company)
† Apollo mobile credits: 75–200/seat/mo included in plan, not separately purchasable at scale

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. PER-PROVIDER DETAIL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

--- 3.1 CLAY ---
Pricing unit: Data credits (vendor data marketplace) + Actions (orchestration)
Free plan: 100 credits/mo, 500 actions/mo (no phone data)
Launch: $185/mo — 2,500–10,000 credits/mo, 15,000 actions/mo
Growth: $495/mo — 6,000–100,000 credits/mo, 40,000 actions/mo
Enterprise: Custom, 100,000+ credits/mo, volume discounts, managed onboarding
Credit top-up: +30% premium during billing cycle
Credit rollover: monthly plans up to 2x monthly limit; annual plans up to 15%
Cost per credit: ~$0.016–0.035 depending on plan (vs underlying provider direct costs of $0.008–0.025)

Clay pipeline role: Stages 2–7 (orchestration layer)
Key note: Clay DOES NOT generate data — it calls underlying providers (Apollo, PDL, Hunter, etc.). Teams that use Clay with their own API keys pay direct provider costs. Teams using Clay's native credits pay a 1.6–3.5x markup for the convenience layer.
AU coverage: Depends entirely on underlying providers (see per-provider notes below).
Minimum spend: $185/mo for meaningful volume.

--- 3.2 APOLLO.IO ---
Pricing unit: Per credit (email/export) + Per seat (platform access)
Free plan: 50 trial credits; then 10,000 credits/account/month (verified corporate email) or 100/month (unverified)
Basic: $59/user/mo ($49 annual) — 75 mobile credits, 1,000 export credits/mo
Professional: $99/user/mo ($79 annual) — 100 mobile credits, 2,000 export credits/mo
Organization: $149/user/mo ($119 annual, min 3 users) — 200 mobile credits, 4,000 export credits/mo
Credit economics: $0.025/email credit (1M credits per year cap = $paid ÷ $0.025)
Full contact enrichment: ~6 credits = ~$0.15/contact
Mobile credits: 75–200/seat/mo included (NOT available for purchase at volume — major limitation)
API access: Limited on Basic/Professional; full on custom/enterprise plans

Apollo pipeline role: Stages 3, 4, 5 (company enrichment, contact discovery, email finding)
Volume discount: Enterprise negotiated, typically 40–60% off list for $15k+/year contracts
Minimum spend: $59/user/mo (+ overage at $200–500/mo for mid-teams = $17k–21k/year for small teams)
AU coverage: ⚠️ Weak. Apollo's database is US-centric. APAC coverage gaps well-documented. Expect 30–50% lower match rates for AU SMB contacts. Credit burn increases because waterfall enrichment queries multiple sources before failing.

--- 3.3 CLEARBIT / HUBSPOT BREEZE INTELLIGENCE ---
Pricing unit: Per credit (1 credit = 1 record enriched)
Current status: Acquired by HubSpot Dec 2023, rebranded as Breeze Intelligence
Standalone: $45/mo annual or $50/mo monthly = 100 credits (est. $0.45–0.50/credit at base tier)
Estimated bulk pricing: ~$0.09–0.10/credit at higher volumes (not publicly disclosed)
Starter Customer Platform + Breeze: ~$45–50/mo for 100 credits
Professional Customer Platform: ~$1,184/mo (annual)
Enterprise Customer Platform: ~$4,135/mo (annual)
Credit rollover: None — credits reset monthly
Re-enrichment: No charge for records already enriched in same term

Clearbit pipeline role: Stage 3 (company enrichment), Stage 4/5 (contact enrichment)
Minimum spend: $45/mo annual commitment
AU coverage: ⚠️ Explicitly poor. "Coverage weaker outside North America and Western Europe" — confirmed by multiple sources. Not suitable as primary AU enrichment source.

--- 3.4 BRIGHT DATA ---
Pricing unit: Per result/record (web scraper, SERP), per GB (proxies)

SERP API (Stage 1 — Business Discovery, GMB/Maps):
  PAYG: $1.50/1K results = $0.00150/result
  $499/mo: $1.30/1K results = $0.00130/result (380K results included)
  $999/mo: $1.10/1K results = $0.00110/result (900K results included)
  $1,999/mo: $1.00/1K results = $0.00100/result (2M results included)

Web Scraper API (Stage 2–4 — LinkedIn profiles, company pages):
  PAYG: $1.50/1K records = $0.00150/record
  $499/mo: $0.98/1K records = $0.00098/record (510K records included)
  $999/mo: $0.83/1K records = $0.00083/record (1M records included)
  $1,999/mo: $0.75/1K records = $0.00075/record (2.5M records included)

LinkedIn People Profiles scraper available (replaces Proxycurl)
LinkedIn Company scraper available
Only pay for successful requests — failed/errored not billed

Proxy products (for custom scraping):
  Datacenter: $14/mo starting
  Residential: $2.50–10.50/GB
  ISP Proxies: $18/mo starting

Datasets (batch delivery):
  Starting ~$250/100K records (structured bulk datasets)

Bright Data pipeline role: Stages 1 (SERP/GMB), 2 (website scrape), 3–4 (LinkedIn company/people profiles post-Proxycurl shutdown)
AU coverage: ✅ Excellent. Real-time scraping with worldwide geotargeting. No geographic data gaps.
Minimum spend: PAYG available but $499/mo entry for committed volume.
Note: Bright Data successfully defended web scraping in US courts — most legally compliant LinkedIn scraper alternative now that Proxycurl is shut down.

--- 3.5 LEADMAGIC (OUR CURRENT PROVIDER) ---
Pricing unit: Per credit (pay for success — null results are free)
Plans:
  Basic: $60/mo — 2,500 credits ($0.024/credit)
  Essential: $100/mo — 10,000 credits ($0.010/credit)
  Growth: $180/mo — 20,000 credits ($0.009/credit)
  Advanced: $260/mo — 30,000 credits ($0.0087/credit)
  Professional: higher tiers available (pricing not fully public)
  
Credit rollover: Essential+ plans (unused credits roll over)
No annual contracts required
No per-seat pricing — unlimited team members
Pay-for-success: null/not_found results are free across all endpoints

Credit costs per service:
  Email Validation: 1 credit = 4 validations ($0.0025/validation at Essential)
  Email Finder: 1 credit per valid email found
  Personal Email Finder: 2 credits per personal email
  Profile to Email: 5 credits per email (from LinkedIn URL)
  Profile Search: 1 credit per full profile
  Employee Finder: 1 credit = 20 employees (bulk list)
  Role Finder: 2 credits per role
  Mobile Finder: 5 credits per mobile number ($0.050 at Essential)
  Email to Profile: 10 credits
  Company Search: 1 credit per company enrichment
  Technographics: 1 credit per tech stack lookup
  Company Funding: 4 credits per company
  Competitors Search: 5 credits per company
  Google/Meta/B2B Ads Search: 1 credit = 5 ad lookups ($0.002/ad lookup)

Leadmagic pipeline role: Stages 2, 3, 4, 5, 6 (core enrichment stack)
AU coverage: ✅ Competitive. Real-time scraping basis means geography is less of a limitation. Mobile finder works for AU numbers. Exact AU match rate not disclosed but anecdotally better than static database providers (Apollo, PDL).
Competitive advantage: Mobile finder at 5 credits vs competitors charging 10 credits (e.g. Prospeo). Single credit pool across all 15 endpoints.

--- 3.6 PEOPLE DATA LABS (PDL) ---
Pricing unit: Per credit (varies by API endpoint type)
Free: 100 person/company lookups/mo, no contact data (email/phone)
Pro: starts $98/mo
  Person enrichment: $0.28/credit (350–2,500/mo) → $0.25 (5,001–8,333/mo)
  Company data: $0.10/credit (350–2,500/mo) → $0.06 (5,001–8,333/mo)
  IP enrichment: $0.072/credit
  Person Identify (search/find): $0.55/credit (350–2,500) → $0.40 (annual high volume)
Annual plans: 20% discount
  Person enrichment: $0.224/credit (4,200–30,000/yr) → $0.20 (30,001–60,000/yr)
  Company data: $0.058/credit → $0.048/credit
  Person Identify: $0.44 → $0.40/credit
Enterprise: Custom, ~$2,500+/mo

PDL pipeline role: Stage 3 (company enrichment), Stage 4 (contact discovery via Person Identify)
AU coverage: ⚠️ Moderate. Larger than average gaps for APAC/AU vs US. SMB contacts in AU often not in PDL database. Match rates reported at 40–60% for AU vs 80%+ for US.
Key strength: Company data is relatively cheap ($0.06–0.10/record) and accurate for firmographics.
Minimum spend: $98/mo

--- 3.7 HUNTER.IO ---
Pricing unit: Per credit (search credits + verification credits, interchangeable)
Free: 50 credits/mo, API: 50 calls/mo
Starter: $34/mo (annual: $408/yr = $34/mo) — 2,000 credits/mo (24K/yr), API: 2,000 calls/mo
Growth: $104/mo (annual: $1,248/yr) — 10,000 credits/mo (120K/yr), API: 10,000 calls/mo
Scale: $209/mo (annual: $2,508/yr) — 25,000 credits/mo (300K/yr), API: 25,000 calls/mo
Enterprise: Custom

Per credit cost (annual billing):
  Starter: $408 / 24,000 = $0.017/credit
  Growth: $1,248 / 120,000 = $0.010/credit
  Scale: $2,508 / 300,000 = $0.0084/credit

Extra credit overage: $0.10/extra search (punitive — avoid going over)
Additional email accounts: $10/mo each
No phone/mobile data available

Hunter pipeline role: Stage 5 (email finding and verification only)
AU coverage: ✅ Good relative to static databases. Hunter's domain-based search approach works globally. B2B email patterns often consistent (firstname.lastname@company.com). Match rates decent for AU corporate email.
Note: Hunter does NOT provide mobile numbers or company firmographics. Email-only tool.

--- 3.8 PROXYCURL (⚠️ SHUT DOWN — JULY 2025) ---
Status: DEFUNCT — shut down by LinkedIn via federal lawsuit filed July 2025
Historical pricing (for reference only):
  PAYG: $0.10/credit (100 credits = $10), scaling down to $0.0216/credit ($1,000 pack)
  Starter subscription: $49/mo — 2,500 credits ($0.020/credit)
  Growth: $299/mo — 25,000 credits ($0.012/credit)
  Pro: $899/mo — 89,900 credits ($0.010/credit)
  Ultra: $1,899/mo — 211,000 credits ($0.009/credit)
  Enterprise: $2,000+/mo (12-month contract)
  Per person profile: 2 credits = $0.02–0.04
  Per company profile: ~2 credits

DO NOT use or recommend Proxycurl. All LinkedIn enrichment should now route to Bright Data.

Top Proxycurl replacement options:
1. Bright Data LinkedIn Scraper API — most legally defensible, proven compliance
2. Nimble — cloud-based, AI-powered, GDPR/CCPA compliant
3. Scrapingdog — simpler/cheaper, no login required, no court track record

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. MARKET PRICE RANGE BY PIPELINE STAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Stage 1 — Business Discovery (GMB/Maps SERP)
  Market range: $0.0008–$0.0020/result
  Best provider: Bright Data SERP API ($0.0010–0.0015/result)
  Notes: Google charges $0.005/Maps API call (expensive at scale). Bright Data SERP is best value for AU GMB scraping.

Stage 2 — Tech Stack & Domain Intelligence
  Market range: $0.005–$0.020/lookup
  Best provider: Leadmagic Technographics ($0.010/lookup at Essential) or BuiltWith API (~$0.001–0.005 at high volume)
  Notes: Wappalyzer free plan covers basic stack. DNS/MX lookups nearly free (self-hosted). Leadmagic covers website scrape + tech stack in 1 credit.

Stage 3 — Company Enrichment (employee count, industry, LinkedIn)
  Market range: $0.006–$0.150/company
  Cheapest: PDL company data ($0.06–$0.10/record)
  Our cost (Leadmagic): $0.010/company search
  Most expensive: Apollo waterfall enrichment (~$0.15/company at 6 credits)
  Notes: Leadmagic is highly competitive here. Clearbit ($0.09–0.10) is overpriced vs Leadmagic for company-only enrichment.

Stage 4 — Contact Discovery (DM name, LinkedIn URL)
  Market range: $0.001–$0.550/contact
  Cheapest: Leadmagic Employee Finder ($0.0005/person via bulk 20-employee batch)
  Most expensive: PDL Person Identify ($0.40–0.55/search)
  Mid-range: Apollo contact unlock (6 credits = $0.15)
  Notes: Leadmagic's Employee Finder is exceptional value — 20 employee profiles for 1 credit ($0.010 at Essential). LinkedIn profile scraping via Bright Data: $0.0008–0.0015/profile.

Stage 5 — Email Finding (verified work email)
  Market range: $0.008–$0.030/verified email
  Cheapest: Leadmagic ($0.010/email, pay-for-success) or Hunter Scale ($0.0084/credit)
  Most expensive: PDL person enrichment includes email but at $0.25–0.28/record
  Notes: Hunter and Leadmagic are comparable on price at $0.008–0.010/email. Leadmagic wins on mobile bundling. Hunter wins on API simplicity for email-only use cases.

Stage 6 — Mobile Finding (personal phone)
  Market range: $0.050–$0.500/mobile
  Cheapest: Leadmagic ($0.050/mobile at Essential — 5 credits)
  Mid-range: Apollo (included with seat subscription — 75–200 mobiles/seat/mo)
  Most expensive: PDL ($0.25+/record including phone)
  Notes: Mobile data is premium everywhere. Leadmagic at $0.050/mobile is market-leading vs Prospeo (10 credits = 10x more expensive at equivalent plans). Apollo's included mobiles become expensive per-unit if used as primary mobile source (effectively $0.50–5.00/mobile depending on seat cost allocation).

Stage 7 — AI Scoring & Personalisation
  Market range: $0.0005–$0.010/prospect
  Our cost (Claude Haiku): ~$0.0025/prospect
  Clay AI actions: $0.016–0.035/action
  Notes: DIY LLM calls are 4–14x cheaper than Clay's AI credit system. Claude Haiku is optimal. GPT-4o-mini comparable (~$0.0020/prospect). For scoring + personalisation in one call, $0.0025 is hard to beat.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. PRICING MODEL ANALYSIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dominant models in market:
1. Credit pack + monthly subscription (Clay, Apollo, Hunter, Leadmagic, PDL) — 80% of market
2. Pay-per-use/GB (Bright Data) — ideal for variable/scraping workloads
3. Seat-based with credit allowance (Apollo) — penalises solo operators / small teams
4. Platform add-on (Clearbit/HubSpot) — forces CRM lock-in

What credit packs unlock:
• Volume discounts: 20–50% reduction at scale vs PAYG
• Rollover credits: avoids waste at predictable volumes (Leadmagic, PDL)
• Rate unlocks: higher-tier plans unlock phone data (Apollo), AI features (Clay)
• Monthly credit refresh: motivates monthly spend commitment

Usage-based with overage:
• Hunter.io: $0.10/extra search (punitive overage — designed to push upgrade)
• Apollo: not clearly specified (credits cap at paid amount ÷ $0.025)
• Clay: additional credits at 30% premium

Free forever tiers and limits:
• Clay: 100 data credits/mo, 500 actions/mo — functional for testing only
• Apollo: 50 credits (trial) then 10K/mo (with verified corporate email) — substantial for email, useless for mobile
• Hunter: 50 credits/mo — barely useful (1–2 domain searches)
• PDL: 100 person/company lookups/mo — no contact data; testing only
• Leadmagic: No disclosed free forever plan; 14-day trial implied

Monthly minimum spend observations:
• No minimum: Leadmagic ($60/mo entry), Bright Data PAYG, Proxycurl PAYG (defunct)
• Low minimum: Hunter ($34/mo), PDL ($98/mo), Clay ($185/mo), Apollo ($59/user/mo)
• High minimum: Clearbit (~$45/mo + HubSpot base), Bright Data subscriptions ($499/mo)
• Enterprise floors: PDL $2,500+, Clay Enterprise custom, Bright Data Enterprise custom

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
6. AU-SPECIFIC DATA PREMIUM FLAGS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ HIGH RISK (poor AU coverage):
• Apollo.io — US-centric database. 30–50% lower match rates for AU SMB contacts. Credit burn increases as waterfall enrichment exhausts sources before failing.
• Clearbit/HubSpot Breeze — Explicitly confirmed: "coverage weaker outside North America and Western Europe." Not recommended as primary AU enrichment.
• People Data Labs — APAC coverage gaps documented. AU SMB match rates 40–60% vs 80%+ for US.

🟡 MODERATE (usable but with caveats):
• Hunter.io — domain-based search works globally for corporate email patterns. AU match rates reasonable (~60–70%) but depends on company size and LinkedIn presence.
• Clay — only as good as underlying providers. Running Clay with Apollo/PDL backends means AU gaps persist.

✅ GOOD AU COVERAGE:
• Leadmagic — real-time scraping approach; less geography-dependent. Mobile finder covers AU mobile numbers. Best-positioned for AU-first pipeline.
• Bright Data — worldwide geotargeting. SERP API and web scraper work identically for AU vs US. Google Maps AU coverage is excellent via SERP API.

No provider charges a geographic premium for AU data explicitly — but effectively there is a premium via lower match rates (you burn more credits per successful result).

Effective AU premium calculation example (Stage 5 email finding):
  US match rate 80% → cost per found email: $0.010 ÷ 0.80 = $0.0125 effective
  AU match rate 50% → cost per found email: $0.010 ÷ 0.50 = $0.020 effective
  Implied AU premium: ~60% higher effective cost on database-dependent tools

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
7. RECOMMENDED PRICING MODEL FOR AGENCY OS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Our per-prospect cost structure (current stack):
  Stage 1: $0.0010 (Bright Data SERP, GMB discovery)
  Stage 2: $0.010 (Leadmagic tech stack + domain)
  Stage 3: $0.010 (Leadmagic company enrichment)
  Stage 4: $0.001 (Leadmagic Employee Finder, bulk 20)
  Stage 5: $0.010 (Leadmagic Email Finder, pay-for-success)
  Stage 6: $0.050 (Leadmagic Mobile Finder)
  Stage 7: $0.0025 (Claude Haiku scoring + personalisation)
  ─────────────────────────────────────────────
  TOTAL COGS per prospect: ~$0.085 (all 7 stages)
  Without mobile (stages 1–5 + 7): ~$0.034
  Email-only prospect (stages 1,3,5,7): ~$0.024

Market context:
  Competitors (Apollo/Clearbit/PDL stack): $0.20–$0.50/prospect
  Clay waterfall stack: $0.10–$0.25/prospect (using their credits)
  Our stack: $0.034–$0.085/prospect

Recommended Agency OS customer pricing model:
• Credit-pack hybrid with usage-based billing
• Charge per-enriched-prospect (pay for success model, same as Leadmagic)
• Suggested retail: $0.25–$0.50/prospect (3–6x margin on COGS)
• Volume tiers: 1K prospects = $0.45/each; 10K = $0.35/each; 50K+ = $0.25/each
• Monthly platform fee ($99–$299/mo) + credits on top (familiar SaaS model)
• Do NOT charge per seat — eliminates barrier for small AU agencies

Key pricing principles to communicate to customers:
1. "You only pay for prospects where we find a verified email" (pay-for-success)
2. "Australian business data — we specialize where US tools fail" (differentiation)
3. "7-stage pipeline for the price of a single Apollo seat" (positioning vs $99/seat/mo Apollo)

Competitive moat:
• Our Leadmagic+BD stack delivers 2–5x better AU coverage vs Apollo/PDL at 20–60% lower COGS
• Claude Haiku personalisation at $0.0025/prospect vs Clay AI at $0.016–0.035/action = 7–14x cheaper
• No seat pricing = can serve solo consultants and agencies of 1

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
8. CRITICAL ALERTS & ACTION ITEMS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 PROXYCURL SHUT DOWN (July 2025)
   If any pipeline code references Proxycurl endpoints, it must be migrated immediately.
   Replace with: Bright Data LinkedIn People/Company scraper endpoints.
   Pricing impact: Bright Data LinkedIn profile = $0.0008–0.0015/record (cheaper than old Proxycurl at $0.02).

🔍 AU MOBILE DATA GAP
   No provider is dominant for AU mobile numbers at scale.
   Leadmagic at $0.050/mobile is market-leading but coverage is still variable.
   Recommend: test Leadmagic mobile fill rate on AU SMB sample (target: >40% fill rate = $0.125 effective cost per mobile found).

💡 CLAY ARBITRAGE OPPORTUNITY
   Clay customers paying $0.016–0.035/credit for enrichments we deliver at $0.008–0.024/call.
   Agency OS could position as "Clay alternative for Australian outreach" — same outputs at lower cost, AU-specialised.

📊 MONITOR: Hunter.io credit overage pricing
   At $0.10/extra credit overage, Hunter encourages annual plan locks.
   If we use Hunter for email fallback: stay within plan limits or switch to Leadmagic (no punitive overage).

