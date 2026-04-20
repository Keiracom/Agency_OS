# Pipeline Stage Audit — Stages 5-8

**Date:** 2026-04-15
**Agent:** build-3
**Run:** D2 validation run (20 domains, dental + water + legal + fitness + building materials)
**Scope:** prospect_scorer.py, stage6_enrich.py, cohort_runner _run_stage7, email_waterfall.py, mobile_waterfall.py, contactout_enricher.py, verify_fills.py, funnel_classifier.py (Stage 11 card gate)

---

## Stage 5 — SCORE

### What It Does

Deterministic 4-dimension formula (budget 0-25 / pain 0-25 / reachability 0-25 / fit 0-25 = composite 0-100). Viability filter drops media/directory domains. Gate: composite >= 30 to continue; composite >= 60 to unlock Stage 6.

### D2 Results

| Domain | Composite | Budget | Pain | Reach | Fit | Viable |
|--------|-----------|--------|------|-------|-----|--------|
| buildmat.com.au | 84 | 14 | 20 | 25 | 25 | True |
| dentalaspects.com.au | 76 | 21 | 5 | 25 | 25 | True |
| purewatersystems.com.au | 76 | 21 | 10 | 25 | 20 | True |
| dentistsclinic.com.au | 72 | 17 | 5 | 25 | 25 | True |
| criminaldefencelawyers.com.au | 71 | 11 | 10 | 25 | 25 | True |
| brydens.com.au | 71 | 16 | 10 | 25 | 20 | True |
| twl.com.au | 71 | 21 | 10 | 20 | 20 | True |
| glenferriedental.com.au | 69 | 14 | 5 | 25 | 25 | True |
| puretec.com.au | 69 | 14 | 10 | 25 | 20 | True |
| hartsport.com.au | 69 | 19 | 5 | 25 | 20 | True |
| hillsirrigation.com.au | 66 | 11 | 10 | 20 | 25 | True |
| theorthodontists.com.au | 65 | 10 | 10 | 25 | 20 | True |
| localfitness.com.au | 49 | 9 | 10 | 5 | 25 | **False** (directory) |

### Diagnoses

| ID | Finding | Evidence |
|----|---------|----------|
| S5-D1 | Fit score double-counts organic base. `strong_organic_base` (+5, kw>500) AND `meaningful_organic` (+5, kw>100) both fire for any domain with >500 keywords — same underlying signal earns 10 points with two labels. | prospect_scorer.py L238-241: separate `if organic_kw > 500` and `if organic_kw > 100` blocks both add to `fit`. Every domain with kw>500 shows both `strong_organic_base` and `meaningful_organic` in breakdown. |
| S5-D2 | Pain is under-weighted for high-GMB-rating domains. Dental practices with 4.8-4.9 stars and 300-600 reviews score pain=5 (only `many_page2_keywords`). Real pain exists (large kw decay: dentalaspects has 364 lost kws in Apr alone) but decaying keyword count has zero pain signal. | D2: dentalaspects pain=5 despite 364 lost kws; glenferriedental pain=5 despite 435 pos_11_20 kws. prospect_scorer.py L167-192: no signal for `is_down`/`is_lost` keyword velocity. |
| S5-D3 | ETV sweet spot logic awards MORE points to mid-percentile (0.25-0.75 = +3) than top-quarter (>0.75 = +1). A high-ETV domain is penalised. The intent is to target businesses not already dominating — but the calibration inverts the budget signal: top-quarter ETV is a STRONGER affordability indicator. | prospect_scorer.py L155-163: `etv_sweet_spot` = 3, `etv_top_quarter` = 1. |
| S5-D4 | Viability filter is keyword-only against `industry_category`. A directory that Gemini labels "Fitness Directory" gets caught. But one labelled "Sports Equipment Retail" (also a directory) would pass. Filter is brittle — relies entirely on Gemini industry label accuracy. | prospect_scorer.py L249-259. localfitness dropped correctly, but coverage is label-dependent. |
| S5-D5 | Gate at 30 (pass_gate) vs 60 (Stage 6) creates a dead zone: domains scoring 30-59 reach Stage 7 (Gemini, ~$0.01-0.02 cost) but not Stage 6. Gate at 30 is generous — in D2, all viable prospects scored 65+. | cohort_runner.py L243-245: composite < 30 drops; stage6 gates at 60. All 12 viable D2 domains scored >= 65. |

### Prescriptions

| ID | Action | Priority |
|----|--------|----------|
| S5-P1 | Remove `meaningful_organic` branch (L238-241 in prospect_scorer.py) — consolidate into `strong_organic_base` (>500) and `moderate_organic_base` (100-500). Net fit max = 25 unchanged, no double-counting. | HIGH |
| S5-P2 | Add `kw_decay_velocity` pain signal: if `is_lost + is_down > 0.4 * count` (>40% of keywords declining), award +5 pain. Data already available in `rank_overview` from Stage 4. | MEDIUM |
| S5-P3 | Invert ETV weighting: top-quarter = +3, sweet-spot = +2, low-presence = +1. High ETV means more ad spend potential = stronger budget signal. | LOW |
| S5-P4 | Raise Stage 5 pass gate from 30 to 50. Given all D2 survivors score 65+, a 30 gate is effectively dead weight — domains 30-49 are not producing viable leads. Saves Stage 6 + Stage 7 cost on marginal domains. | MEDIUM |

### Downstream Impact

Stage 5 scores feed Stage 6 gate (>=60) and Stage 11 card assembly. The double-counting bug inflates fit scores by up to +5 for high-kw domains, potentially promoting marginal domains over the Stage 6 gate. Fix is low-risk: capped at 25 so no domain currently below the gate would cross it, but calibration becomes honest.

---

## Stage 6 — ENRICH (DFS historical rank)

### What It Does

Single DFS `historical_rank_overview` call per domain if composite >= 60. Returns 6 months of monthly keyword count + ETV + position distribution. Cost: $0.106/domain (USD).

### D2 Results

All 12 viable domains scored >= 65 and all returned 6 months of data. Stage 6 enrichment ran for every eligible domain. Timing was absorbed into the async pipeline. Cost per domain: $0.106 (wired correctly).

### Diagnoses

| ID | Finding | Evidence |
|----|---------|----------|
| S6-D1 | Stage 6 data is NOT passed to Stage 7 (Gemini). cohort_runner `_run_stage7` receives `f3a_output` (Stage 3) and `signal_bundle` (Stage 4) only. Stage 6 historical trend data is collected and stored but never injected into the Gemini prompt. | cohort_runner.py L268-278: `gemini.call_f3b(f3a_output=identity, signal_bundle=signals)` — no `stage6` param. dentalaspects D2: VR mentions "keyword decay" from Stage 4 `is_down` data, but the 6-month ETV decline (59,762 Nov → 39,684 Apr = -34% in 5 months) is never surfaced. |
| S6-D2 | The trend data is high-signal but Stage 11 card only surfaces `historical_rank` as raw list. No computed trend metric (e.g. ETV 3-month delta, kw decay rate) is derived or stored. Downstream consumers (dashboard, outreach personalisation) get raw monthly arrays, not actionable numbers. | funnel_classifier.py L92: `"historical_rank": (stage6_enrich or {}).get("historical_rank")` — raw passthrough, no transformation. |
| S6-D3 | Gate at composite >= 60 is correct given $0.106 cost. All 12 viable D2 domains cleared it (min 65). However, gate creates a hard cliff: a domain scoring 59 gets no trend data but a domain at 60 gets 6 months. With fix S5-P2 raising pain scores, some previously-59 domains may now legitimately deserve Stage 6. | stage6_enrich.py L20, 43-44. |
| S6-D4 | 1.19s timing reported in the directive brief but D2 does not show Stage 6 timing separately — it is baked into total pipeline timing. Cannot confirm whether Stage 6 ran async-parallel with Stage 7 or sequentially. | cohort_runner pipeline sequence: Stage 6 runs before Stage 7 in the linear per-domain flow. |

### Prescriptions

| ID | Action | Priority |
|----|--------|----------|
| S6-P1 | Pass Stage 6 historical data to Stage 7 Gemini. In `_run_stage7`, merge `domain_data.get("stage6", {}).get("historical_rank")` into signal_bundle before calling `gemini.call_f3b`. Add `historical_trend` key with last 3 months of ETV + `is_lost` counts. | HIGH — $0.106 is wasted if trend data doesn't reach the outreach. |
| S6-P2 | Compute `etv_3m_delta` and `kw_decay_rate` in Stage 6 output and store on the card. Formula: `(etv_month[-1] - etv_month[-3]) / etv_month[-3]`. This gives outreach a concrete percentage decline to cite. | MEDIUM |
| S6-P3 | After implementing S5-P2 (kw_decay_velocity pain signal), re-validate the Stage 6 gate: if decay velocity already captures the pain, confirm $0.106 is still justified by checking whether trend data adds independent signal beyond what Stage 4 already provides. | LOW |

### Downstream Impact

Stage 6 trend data is currently decorative — it costs $0.106/domain, runs correctly, but its value is trapped in the `historical_rank` raw array. Fixing S6-P1 is the highest-ROI change in the stage: same API cost, materially better outreach personalisation.

---

## Stage 7 — ANALYSE (Gemini 2.5-flash VR + outreach)

### What It Does

Gemini 2.5-flash `call_f3b` with Stage 3 identity + Stage 4 signal bundle. Produces: `vulnerability_report` (summary, strengths, vulnerabilities, gmb_health, recommended_services, urgency), `draft_email`, `draft_linkedin_note`, `draft_voice_script`, `intent_band_final`.

### D2 Results

All 12 eligible domains produced Stage 7 output. VR structure consistent across all: 6 keys present, urgency=high for STRUGGLING domains. Draft email: ~500-700 chars. Draft LinkedIn: ~200-300 chars. Draft voice present on all (not measured separately).

### Diagnoses

| ID | Finding | Evidence |
|----|---------|----------|
| S7-D1 | Draft email body contains `{{agency_contact_name}}` and `{{agency_name}}` unfilled template tokens. These are not post-processing substitution markers — they are passed raw into Salesforge/outreach as-is. If the merge step in Stage 12/outreach doesn't resolve them, prospects receive `"Hi from {{agency_name}}"`. | D2 buildmat draft: `"I'm {{agency_contact_name}} from {{agency_name}}"`. LinkedIn note: `"Cheers, {{agency_contact_name}}"`. |
| S7-D2 | Stage 7 does not receive Stage 6 trend data (confirmed in S6-D1). The VR identifies keyword decline correctly (from Stage 4 `is_down`/`is_lost` in current month) but cannot quantify the trend: "keywords are declining" vs "ETV dropped 34% over 5 months" are different personalisation levels. The latter is a harder-hitting conversation opener. | D2: dentalaspects VR says "showing concerning signs of decline" — Stage 4 has `is_lost=364` but not the 5-month trajectory. Stage 6 has the 5-month data but isn't passed in. |
| S7-D3 | Draft email subject lines are generic. D2 subjects: "Quick look at Buildmat's online presence", "Quick look at Dental Aspects' online opportunities". "Quick look" as opener is weak — it reads like a cold pitch, not a data-backed alert. | All D2 emails checked. No domain-specific hooks in subject (competitor name, specific kw count, dollar ETV). |
| S7-D4 | VR `recommended_services` field is not surfaced in D2 output samples — it's present in the schema but not verified in card or outreach. If it's populated, it should drive Salesforge campaign sequence selection. If empty, it's dead schema. | Stage 7 VR keys confirmed: `['summary', 'strengths', 'vulnerabilities', 'gmb_health', 'recommended_services', 'urgency']`. recommended_services content not extracted in D2 run analysis. |
| S7-D5 | `intent_band_final` is STRUGGLING for 9/12, TRYING for 3/12. Zero GROWING in D2. Either the gate correctly filters out growing businesses (good) or the classifier is biased toward STRUGGLING. With pain_score under-weighted (S5-D2), high-pain signals may be systematically over-reported to Gemini. | D2: STRUGGLING=9, TRYING=3, GROWING=0. |

### Prescriptions

| ID | Action | Priority |
|----|--------|----------|
| S7-P1 | Resolve `{{agency_contact_name}}` and `{{agency_name}}` tokens before card storage. Either: (a) prompt Gemini to leave a clearly-marked placeholder like `[AGENCY_NAME]` and resolve at Stage 12, or (b) define a config value for agency name and inject it into the Gemini system prompt. Option (b) is cleaner. | CRITICAL — unfilled tokens in production outreach is a deliverability and trust risk. |
| S7-P2 | After implementing S6-P1 (pass trend data to Stage 7), update the Gemini prompt to require citation of ETV trajectory in the email subject when available. Example instruction: "If ETV declined >15% over 3 months, open subject with the decline percentage." | HIGH |
| S7-P3 | Extract and surface `recommended_services` in the Stage 11 card and confirm it is used in campaign sequence selection. If not consumed downstream, remove from VR schema to reduce prompt hallucination surface. | MEDIUM |

### Downstream Impact

Stage 7 output is the primary outreach asset. Token bug (S7-D1) is a blocking production issue. Trend-citation gap (S7-D2) is a conversion rate issue. Both are fixable with no API cost change.

---

## Stage 8 — CONTACT (unified waterfall)

### What It Does

Four sub-stages run sequentially:
- **8a:** verify_fills — DFS SERP for ABN (4 variants) + DM LinkedIn URL + company LinkedIn URL. Cost: $0.008/domain flat.
- **8b:** ContactOut enrichment — `enrich_dm_via_contactout(dm_linkedin_url)` — 1 credit, returns email + mobile + identity. Only fires if dm_linkedin_url available.
- **8c:** Email waterfall — L0 contact_registry → L1 ContactOut current_match → L2 Hunter → L3 Leadmagic → L4 ContactOut stale → L5 Bright Data.
- **8d:** Mobile waterfall — L0 ContactOut → L1 HTML regex → L2 Leadmagic → L3 BD.

### D2 Results

| Metric | Value |
|--------|-------|
| Domains with email | 7/13 (54%) |
| Email source: Hunter | 7/7 hits |
| Email source: ContactOut / Leadmagic / BD | 0 |
| Emails with `verified=True` | 0 |
| Emails with `verified=None` (Hunter) | 7 |
| Domains with mobile | 0/13 (0%) |
| DM LinkedIn URL from Stage 3 | 0/13 (0%) |
| DM LinkedIn URL found by Stage 8a verify_fills | 6/13 (46%) |
| Stage 8 avg timing | 17.7s |

### Diagnoses

| ID | Finding | Evidence |
|----|---------|----------|
| S8-D1 | Stage 3 produces ZERO dm_candidate.linkedin_url values. 8a verify_fills finds LinkedIn for 6/13 via SERP, but that result feeds 8b ContactOut ONLY if the dm_linkedin resolver logic correctly chains. Check: `dm_linkedin` in `_run_stage8` is sourced from `stage8_contacts.linkedin.linkedin_url` OR `fills.dm_linkedin_url` OR `dm.linkedin_url` — in that priority order. Since `stage8_contacts` is populated AFTER this resolution, only `fills` and `dm` contribute. This creates a timing dependency: fills must complete before ContactOut can fire. | cohort_runner.py L312-317: dm_linkedin resolution. stage3 `dm_candidate.linkedin_url = None` for all 13 D2 domains. |
| S8-D2 | ContactOut 8b fires if dm_linkedin is found, but D2 results show 0 ContactOut emails resolved (all 7 email hits are Hunter). Either ContactOut returned no data for these profiles, or it wasn't called because dm_linkedin was only available from Stage 8a fills (which runs just before 8b). Confirm: if fills returns linkedin, ContactOut should fire. But Stage 8 timing (avg 17.7s) suggests ContactOut calls did run and returned empty. | D2: email_src never = 'contactout'. Stage 8a fill found LinkedIn for 6/13. ContactOut credits cost per found record only — zero cost implies either no results or no call. |
| S8-D3 | Hunter email finder returns `verified=None` — the `verified` field is never set on Hunter results in email_waterfall.py. Hunter score 95-98 (high) is used as confidence proxy, but no SMTP verification occurs. For production outreach, unverified emails risk bounce-rate issues. ZeroBounce exists in `contact_waterfall.py` (legacy F5) but is NOT wired into the current `email_waterfall.py` pipeline. | email_waterfall.py L580-596: Hunter result returned without `verified` flag. ZeroBounce: only in `src/intelligence/contact_waterfall.py` (legacy, not called by cohort_runner). |
| S8-D4 | Domain mismatch risk: puretec.com.au resolved email `arne.hornsey@puretecgroup.com`. The prospect domain is `puretec.com.au` but Hunter returned an email on `puretecgroup.com`. This is a legitimate corporate group email (parent company) but no domain-match check exists in the waterfall. If the business has rebranded or the Hunter record is stale, outreach lands on the wrong address. | D2: puretec email domain = `puretecgroup.com` vs prospect domain `puretec.com.au`. No validation logic in email_waterfall.py. |
| S8-D5 | Mobile: 0/13 resolved. Mobile waterfall L0 (ContactOut) requires `contactout_result` — which requires dm_linkedin. With 0 Stage 3 dm_linkedin values, L0 can only fire for the 6 domains where 8a found LinkedIn. L1 (HTML regex) requires `contact_data` — passed as `None` in `_run_stage8` call to `run_mobile_waterfall`. L2 (Leadmagic) requires `leadmagic_client` — also None in the call. L3 (BD) requires `brightdata_client` — also None. Result: mobile waterfall is effectively dead in the current cohort_runner wiring. | cohort_runner.py L351-358: `run_mobile_waterfall(domain=..., dm_linkedin_url=dm_linkedin, contact_data=None, contactout_result=contactout_result)` — no leadmagic_client, no brightdata_client passed. |
| S8-D6 | `dm_verified` is sourced from `stage3_identity.get("_dm_verified", False)` in `assemble_card`. In D2: `_dm_verified=True` for dentals (Gemini confirmed), `_dm_verified=None` for buildmat and hillsirrigation. But Hunter fires regardless of dm_verified status — there is no dm_verified gate on L2 Hunter as documented in email_waterfall.py code comment ("Gated on dm_verified=true to avoid confident email on unconfirmed DM"). The gate comment exists but no gating code exists. | email_waterfall.py L560-561 comment: "Gated on dm_verified=true to avoid confident email on unconfirmed DM (buildmat-style risk)". Code L563-598: no `dm_verified` check before Hunter call. buildmat.com.au: `dm_verified=None`, Hunter fired and returned `jimmy@buildmat.com.au`. |
| S8-D7 | Stage 8 timing is high: avg 17.7s, max 22.4s (hartsport). With ContactOut firing 6 times (on SERP-found LinkedIn URLs) and running sequentially with Leadmagic for 5 misses, the latency stacks. 8a verify_fills runs 3 concurrent SERP calls (ABN + DM LinkedIn + company LinkedIn) — this is correctly concurrent. But 8b-8c-8d run sequentially within a single domain's stage 8 block. | cohort_runner L295-393: single async function with sequential awaits on ContactOut, then email_waterfall, then mobile_waterfall. |

### Prescriptions

| ID | Action | Priority |
|----|--------|----------|
| S8-P1 | Wire ZeroBounce (or Leadmagic verify) as a post-Hunter verification step. Hunter confidence >= 70 is a good predictor, but `verified=None` is not acceptable for production sends. Add a verification step: if email_source == 'hunter' and confidence >= 70, call ZeroBounce `/v1/validate` ($0.003/call). Set `verified=True/False` based on result. | HIGH |
| S8-P2 | Implement dm_verified gate on Hunter L2. Code comment says it exists — add the actual gate: `if not stage3_identity.get("_dm_verified"): skip Hunter`. This prevents confident email attribution on unconfirmed DMs (buildmat risk). Leadmagic L3 can still fire as fallback. | HIGH |
| S8-P3 | Fix mobile waterfall wiring: pass `leadmagic_client` and `brightdata_client` into `run_mobile_waterfall` call in cohort_runner. Both clients are instantiated at pipeline startup — they just aren't passed through. Until this is fixed, mobile coverage is 0%. | CRITICAL — mobile waterfall is dead. |
| S8-P4 | Add domain-match validation to email waterfall: if resolved email domain != prospect domain (accounting for common corporate parent patterns), flag `email_domain_mismatch=True` on the EmailResult and do not short-circuit — fall through to next layer. | MEDIUM |
| S8-P5 | Investigate ContactOut 0% hit rate in D2. 6 domains had LinkedIn URLs available for 8b; 0 returned email. Either ContactOut has no AU dental coverage, or the profile format from Stage 8a SERP (`au.linkedin.com/in/`) differs from what ContactOut's `/v1/people/enrich` expects. Log raw ContactOut API responses to confirm. | MEDIUM |
| S8-P6 | Run 8b ContactOut + 8c email waterfall + 8d mobile waterfall concurrently (asyncio.gather) within the stage 8 block — ContactOut result feeds both waterfalls, so it must still complete first, but the email and mobile waterfalls can then run in parallel. Expected latency reduction: ~30-40% on domains with ContactOut miss. | LOW |

### Downstream Impact

Mobile at 0% (S8-D5/S8-P3) is the most damaging gap — voice outreach and SMS sequences are dead without a number. Hunter `verified=None` (S8-D3/S8-P1) is a deliverability risk in production. The dm_verified gate gap (S8-D6/S8-P2) means buildmat-style DM misattribution can happen silently. ContactOut 0% hit rate (S8-D2/S8-P5) means 2765 remaining credits are being consumed by profile lookups that return nothing — this is a credit burn with no return.

---

## Cross-Stage Impact Summary

| Finding | Stages Affected | Priority |
|---------|----------------|----------|
| Stage 6 data not passed to Stage 7 | S6, S7 | HIGH |
| Unfilled `{{agency_name}}` tokens in outreach | S7 | CRITICAL |
| Mobile waterfall clients not wired | S8d | CRITICAL |
| Hunter emails not SMTP-verified | S8c | HIGH |
| dm_verified gate missing on Hunter | S8c | HIGH |
| Fit score double-counting (`meaningful_organic`) | S5 | HIGH |
| ContactOut 0% hit rate (AU dental) | S8b | MEDIUM |
| KW decay velocity missing from pain score | S5 | MEDIUM |
| Stage 6 trend metrics not computed/stored | S6 | MEDIUM |
| Email domain mismatch not flagged | S8c | MEDIUM |

---

## Key D2 Numbers

- 13 domains reached Stage 5 scoring (7 blocked at Stage 1 blocklist)
- 12/13 viable post-Stage 5 (localfitness.com.au dropped as directory)
- 12/12 eligible received Stage 6 enrichment (all scored >= 65)
- 12/12 eligible received Stage 7 VR + outreach
- 7/12 received email (all from Hunter L2)
- 0/12 received mobile
- 0/12 emails SMTP-verified
- 1 domain with email domain mismatch (puretec.com.au → puretecgroup.com email)
- ContactOut hit rate: 0% despite 6 LinkedIn URLs available
- Stage 8 avg latency: 17.7s (acceptable but improvable)
