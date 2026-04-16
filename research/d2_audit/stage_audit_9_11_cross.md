# Pipeline Audit: Stages 9–11 + Cross-Stage Analysis

**Run:** D2 Validation Run — 2026-04-15T20:17 UTC  
**Domains:** 20 input / 12 reached Stage 9 / 7 cards produced  
**Auditor:** build-2 (claude-sonnet-4-6)  
**Date:** 2026-04-15

---

## Stage 9 — SOCIAL

### What it does

Scrapes DM LinkedIn posts and company LinkedIn posts via Bright Data. Facebook deferred. Gated on at least one LinkedIn URL being present (DM or company). Hardcoded cost $0.027/domain ($0.002 DM + $0.025 company).

### D2 Data

| Metric | Value |
|--------|-------|
| Domains that ran Stage 9 | 12 |
| Domains with at least one post | 6 |
| Domains with zero posts (but ran) | 6 |
| DM posts retrieved (any domain) | 1 domain got DM posts |
| Company posts retrieved | 6 domains got 5 company posts each |
| Cost per domain | $0.027 USD ($0.042 AUD) |
| Total cost D2 | $0.324 USD on 12 domains |
| Wall clock (sum across domains) | 304.83s total / 25.40s avg |

### What we extract

`dm_posts` (list[dict], up to 5), `dm_posts_count`, `company_posts` (list[dict], up to 5), `company_posts_count`. The raw Bright Data response contains richer fields — post text, date, reactions, comments, share count, media type — but only a slice is captured (capped by `[:max_posts]`). No engagement metrics (reaction counts, comment counts) are surfaced to BU individually.

### What we discard (GOV-8)

The company profile scraper (`gd_l1vikfnt1wgvvqz95w`) response likely contains: employee count, specialties, headquarters, founding year, website, follower count, recent hires. None of these are extracted. The raw `company` dict is destructured only for `updates`/`posts`. This is a GOV-8 violation — API response data not written to BU.

The DM post scraper returns per-post: reaction count, comment count, repost count, post URL, media attachments. These are stored in the raw post dicts but are not surfaced in the card's `signals_summary` and not used by Stage 10 for sentiment or engagement scoring.

### How Stage 10 uses social data

Stage 10 receives `dm_posts` and `company_posts` and instructs Gemini to reference them in outreach. The `dm_post_reference` field in the messaging output shows this works when posts exist:

- puretec.com.au: referenced company AFL/NRL post
- purewatersystems.com.au: referenced PFAS water quality post
- twl.com.au: referenced DM LinkedIn Pulse article (2023 — stale)

When DM posts = 0 and company posts = 0 (6 of 12 domains), the MSG prompt falls through to the default "warm-professional Australian tone" path. The Stage 10 outreach for those domains is indistinguishable from what Stage 7 already produced.

### Zero-activity signal

No-LinkedIn-activity (DM has no posts in 30 days) is itself a signal. A dormant DM is harder to reach via LinkedIn but more receptive to cold email. This is not captured anywhere as a scored attribute. Stage 5 scores `has_social: 5` as binary. A DM who posts weekly is meaningfully different from one who last posted in 2023 (`twl.com.au` example above).

### Company posts vs DM posts — outreach value

Company posts have higher yield (6/12 domains got them vs 1/12 for DM posts in D2). However for personalised outreach, DM posts are higher value — they show personal priorities, tone, recent activities. Company posts are good for "I noticed your company recently announced X" openers but are more generic. The current prompt does not distinguish between the two source types when building the timeline hook.

### Diagnoses

| ID | Severity | Finding |
|----|----------|---------|
| S9-D1 | HIGH | 50% of Stage 9 runs return zero posts (6/12) despite charging $0.027. When company_posts = 0 and dm_posts = 0, cost was spent for no yield — no personalization improvement over Stage 7 baseline. Root cause: company LinkedIn URL present but Bright Data scraper returned empty `updates`/`posts` key. |
| S9-D2 | MEDIUM | GOV-8: company profile scraper response used only for posts. Company metadata (follower count, employee count, specialties, founding year) discarded. These are zero-cost fields on an already-paid API call. |
| S9-D3 | MEDIUM | No-activity is not a scored signal. DM with 0 posts in 30 days vs DM who posts weekly — treated identically in Stage 5 scoring and Stage 10 outreach strategy. |
| S9-D4 | LOW | `twl.com.au` DM post referenced was from January 2023 — 3+ years old. The `days=30` filter only applies to DM scraper but the post returned is outside that window, suggesting the BD scraper is returning cached/stale data or the days filter is not enforced server-side. |
| S9-D5 | LOW | DM posts engagement data (reaction count, comment count) captured in raw dict but not surfaced for BU or Stage 10. High-engagement posts are better timeline hooks and indicate DM actively monitors their feed. |

### Prescriptions

| ID | Action | Effort |
|----|--------|--------|
| S9-P1 | Add zero-post early exit guard: if both scrapers return empty, skip cost increment and log `stage9_yield: "zero"`. Do not charge $0.027 if nothing was retrieved. | S |
| S9-P2 | Extract and store company profile metadata: `company_followers`, `company_employees_on_li`, `company_specialties`, `company_founded` from the profile scraper response alongside posts. Write to BU. | S |
| S9-P3 | Compute and store `dm_activity_signal`: `"active"` if dm_posts_count > 0, `"company_only"` if company_posts_count > 0 but dm_posts_count = 0, `"dormant"` if both = 0. Pass to Stage 10 so MSG prompt can adapt channel strategy. | S |
| S9-P4 | Pass `dm_activity_signal` into Stage 5 scoring as a reachability sub-component. Active DM (posts weekly) should score higher on reachability than dormant DM. | M |
| S9-P5 | Add date filter validation: if any returned post has `date` older than `days * 2`, log a warning and surface `stage9_data_freshness: "stale"` on the card. | S |

### Improvements (non-blocking)

- Expose post engagement metrics (`top_post_reactions`, `top_post_comments`) in `signals_summary` for dashboard display
- When `dm_activity_signal = "dormant"`, Stage 10 MSG prompt should switch primary channel recommendation from LinkedIn to email
- `max_posts=5` is reasonable but `days=30` may be too short for lower-activity professionals; consider `days=90` for DM scraper with a recency flag on posts

---

## Stage 10 — VR+MSG (Enhanced VR + Messaging)

### What it does

Two sequential Gemini 2.5-flash calls: (1) structured vulnerability report using signal context from Stages 3–8; (2) four-channel outreach assets (email, LinkedIn note, phone KB, SMS) personalised against VR + Stage 9 posts. Gated in `_run_stage10` on `email_data.get("email")`.

### D2 Data

| Metric | Value |
|--------|-------|
| Domains that ran Stage 10 | 12 |
| Domains with email (correct gate) | 7 |
| Domains without email that still ran Stage 10 | 5 (D2 pre-fix artifact) |
| Stage 10 f_status = "success" | 12/12 |
| Stage 10 f_status = "partial" or "failed" | 0 |
| Wall clock avg | 25.88s |
| Wall clock total | 310.57s across 12 domains |

### Email gate — D2 pre-fix artifact

**The gate code in the current repo is correct** (`if not email_data.get("email"): return domain_data`). However, the D2 run executed at 20:17 UTC against a version predating the email waterfall rewrite commits (22:37–23:14 UTC). The 5 no-email domains that ran Stage 10 in D2 produced VR reports but no cards (`lead_pool_eligible=False`). Those Gemini calls were wasted spend.

The **correct gate question** remains open: should Stage 10 run for ALL non-dropped domains, with Stage 11 deciding card eligibility? Arguments:

- VR report has independent BU value even without email. A domain with verified LinkedIn and a score of 75 but no email found yet is still a warm lead that can be worked via LinkedIn.
- Running Stage 10 for email-less domains and surfacing the VR+LinkedIn outreach in BU gives the customer more to act on.
- Cost: 2 Gemini calls per domain is the dominant cost driver in Stage 10. Running on email-less domains means ~$0.05–0.08 additional spend per domain. At current email resolution rate (~58%, 7/12 non-dropped), this adds ~35% more Gemini cost.

**Recommendation:** Keep the email gate but add a softer path: if DM LinkedIn URL is verified (match_type != no_match), run Stage 10 outreach with LinkedIn + phone channels only, skipping email/SMS. This recovers outreach value for the direct_match cases (dentalaspects, glenferriedental both had verified LinkedIn but no email).

### VR quality — hallucination check

VR reports in D2 are data-backed on the numeric claims. Checked against Stage 4 signals:

- ETV figures match `rank_overview.dfs_organic_etv` exactly
- Keyword counts match `dfs_organic_keywords`
- Backlink claims reference `backlinks` data
- GMB health fields (`rating`, `review_count`) match Stage 4 `gmb` data correctly

One concern: competitor names. The VR prompt receives `stage4_signals.competitors` (10 entries) but the VR system prompt does not explicitly instruct Gemini to cite competitor names in vulnerabilities. In D2, no VR report referenced specific competitor domains. This is missed context — a competitor running ads against a no-ads domain is a concrete, specific vulnerability that would sharpen the outreach.

### Outreach personalisation — does it work?

When company posts exist: the `dm_post_reference` field was populated in 6/12 domains. The timeline hook structure (lead with something they did/said) was followed. Quality assessment:

- Strong: brydens.com.au (golf day post), purewatersystems.com.au (PFAS post)
- Acceptable: criminaldefencelawyers.com.au (legal how-to post)
- Weak: twl.com.au DM post from January 2023 — 3 years old, not a timeline hook

When posts = 0 (6/12 domains including all 3 dental groups), the outreach falls back to data-only hooks (keyword losses, no-ads gap). This is still specific and avoids generic clichés but loses the "I noticed you recently" warmth that makes outreach land.

### Banned clichés — is the filter working?

Reviewed outreach across all 7 cards. No instances of banned phrases found: no "reaching out", "touch base", "game-changer", "leverage", "circle back", "synergies", "low-hanging fruit", "hope you're well". The filter appears to be working via system prompt instruction. However, "quick question" equivalents like "Would it be worth a quick 5 minutes" appear (orthodontists card) — a borderline case.

### Signal data Stage 10 does NOT use

| Stage | Available Data | Not Passed to Stage 10 |
|-------|---------------|------------------------|
| Stage 2 | ABN, Facebook URL, company LinkedIn URL | ABN not in signal_ctx |
| Stage 4 | 10 competitor domains with their DFS data | Competitors array not highlighted in VR prompt |
| Stage 4 | Keyword delta (is_new, is_up, is_down, is_lost) | Trend data is passed but only via stage4_signals blob — Gemini extracts it if present |
| Stage 6 | Historical rank (6 months of ETV/keyword trends) | Passed via stage6_enrich but VR prompt does not instruct use of trend data |
| Stage 8 | Email confidence score | Email tier/confidence passed but not used for personalization |

The historical rank trend (Stage 6) is particularly underused. A domain that has lost 40% of keywords over 6 months is a materially different prospect to one that has grown 20%. The VR prompt receives `enrich` data in `signal_ctx` but the system prompt makes no mention of it, so Gemini deprioritises it.

### 4-channel quality assessment

| Channel | Quality | Issue |
|---------|---------|-------|
| Email | Good | Subject lines specific, body under 100 words, timeline hook present when posts available |
| LinkedIn note | Good | Under 300 chars, references specific data |
| Phone KB | Good | Pattern interrupt is domain-specific, not a generic script |
| SMS | Acceptable | Specific but mechanical — reads like the email trimmed to 160 chars, not a distinct tone |

SMS channel does not feel distinct from email. It should be more casual/direct (first-name only, no company reference). The objection handles in phone KB are verbose — some exceed what a rep can hold in a call.

### Diagnoses

| ID | Severity | Finding |
|----|----------|---------|
| S10-D1 | HIGH | Email gate too strict — 5 domains in D2 (3 dental, hillsirrigation, hartsport) had verified LinkedIn DM URLs, good scores, and social data but got no outreach assets. Stage 11 marks them ineligible for lead pool. Customer sees no actionable asset for these domains. |
| S10-D2 | HIGH | Stage 6 historical trend data is passed but not instructed in VR prompt. 6-month keyword trajectory is a powerful urgency signal — a declining domain is more receptive to services than a stable one. Gemini ignores it without explicit instruction. |
| S10-D3 | MEDIUM | Competitor context not used in VR. Stage 4 provides 10 named competitors with their ad/organic data. A finding like "Your top competitor [X] is running 47 paid keywords against your 0" would be more compelling than a generic no-ads vulnerability. |
| S10-D4 | MEDIUM | SMS channel is a trimmed email, not a distinct channel. Tone and structure should be conversational/punchy, not formal. |
| S10-D5 | LOW | Stale post reference (twl.com.au, 2023 post) used as timeline hook. Without a date filter on posts selected for MSG prompt, Gemini will use whatever post it finds regardless of recency. |
| S10-D6 | LOW | Two sequential Gemini calls cannot be parallelised (MSG needs VR output) but there is no timeout guard between them. If VR call stalls, MSG call is never attempted and f_status = "partial" leaves no outreach on the card. |

### Prescriptions

| ID | Action | Effort |
|----|--------|--------|
| S10-P1 | Add LinkedIn-only gate path: if no email but verified LinkedIn URL exists, run Stage 10 with reduced prompt (LinkedIn note + phone KB only). Write outreach to BU and card. | M |
| S10-P2 | Add 6-month trend instruction to VR prompt: "If historical_rank data is present, characterise the trajectory (growing/stable/declining) and use it to justify urgency." | S |
| S10-P3 | Inject top competitor into VR prompt: extract `competitors[0]` domain from Stage 4 and pass as named variable in VR user prompt with their organic/paid summary. | S |
| S10-P4 | Rewrite SMS system prompt instruction to enforce casual first-name tone, max 1 sentence, specific number. No company sign-off. | S |
| S10-P5 | Filter posts passed to MSG prompt to `date >= today - 30 days`. If all posts fail the filter, set `dm_post_reference = null` and use data-only hook path. | S |
| S10-P6 | Add timeout guard between VR and MSG calls (60s each). If VR times out, skip MSG and mark f_status = "partial_vr_timeout". | S |

---

## Stage 11 — CARD ASSEMBLY

### What it does

Assembles all pipeline stage outputs into a single card dict. Applies binary `lead_pool_eligible` gate: requires `dm_name`, `email`, `scores`, and `vr_report` (actually checks stage7_analyse, not stage10). Cards written to `cards.json` and `results.json`. All non-dropped domains get a Stage 11 record. Dropped domains (dropped_at = stage3 or stage5) do not get Stage 11.

### D2 Data

| Metric | Value |
|--------|-------|
| Domains reaching Stage 11 | 12 |
| lead_pool_eligible = True | 7 |
| lead_pool_eligible = False | 5 |
| Missing field "email" only | 5 (all no-email domains) |
| Missing field "dm_name" | 0 |
| Stage 11 avg timing | 0.0s (pure Python, no I/O) |

### Gate analysis — what `lead_pool_eligible` requires

From `assemble_card()`:

```python
if not dm.get("name"):   missing.append("dm_name")
if not email_data.get("email"):  missing.append("email")
if not stage5_scores:   missing.append("scores")
if not stage7_analyse:  missing.append("vr_report")
```

`dm_verified` is NOT gated — a card can be `lead_pool_eligible=True` with `dm_verified=False`. In D2, 4 of 7 eligible cards have `dm_verified=False`. The customer receives outreach copy for a DM whose identity has not been confirmed beyond Stage 3 Gemini inference.

`email_tier` is NOT checked — a card can be eligible with a Stage 3 scrape-extracted email (lower confidence) or a Leadmagic email at $0.077 cost, treated identically. The outreach contains no signal to the customer about email quality.

### Cards missing that would help customers act

| Missing Field | Impact |
|---------------|--------|
| `dm_verified` flag visible in outreach | Customer doesn't know if DM identity is confirmed or inferred |
| `email_tier` / `email_confidence` | Customer can't prioritise by email quality |
| `company_followers` (Stage 9 LinkedIn) | Would indicate company's audience reach |
| `dm_activity_signal` | Customer would know whether to lead with LinkedIn or email |
| `competitor_running_ads` | Immediate talking point for the call |
| `6m_trend` (growing/declining/stable) | Urgency calibration for the customer |

### Fields computed but not actionable

| Field | Assessment |
|-------|-----------|
| `entity_type_hint` | "Individual Sole Trader" vs "Australian Private Company" — useful for BU targeting but not surfaced in outreach or scored |
| `staff_estimate_band` | Present in card but not used in scoring or outreach personalisation |
| `historical_rank` (full 6-month array) | Entire array in card — high data volume, customer dashboard needs trend chart not raw array |
| Full `signals` blob via `stage4_signals` | Not in card (only `signals_summary`) — this is correct |

### BU write — which domains write to BU

All 12 non-dropped domains get a Stage 11 card written to `results.json`. Domains dropped at Stage 3 (8 domains) and Stage 5 (1 domain) do not get a Stage 11 card and do not write to BU. This is a GOV-8 gap: the enrichment data collected for those domains (Stage 2 SERP results, Stage 3 identity attempt) is not persisted to BU.

### Diagnoses

| ID | Severity | Finding |
|----|----------|---------|
| S11-D1 | HIGH | `dm_verified=False` cards enter lead pool without flag. 4 of 7 D2 cards have unverified DM. Customer may call the wrong person or an outdated contact. |
| S11-D2 | HIGH | `email_tier` and `email_confidence` not surfaced at card level. Cards should show at minimum "email_quality: verified|likely|unverified" for customer prioritisation. |
| S11-D3 | HIGH | Domains dropped at Stage 3/5 (9 domains in D2) write nothing to BU. Stage 2 SERP data, GMB URL, ABN, and any signals collected are lost. These are real businesses — the data has retention and re-targeting value. |
| S11-D4 | MEDIUM | No card quality tier. Binary eligible/ineligible creates a flat lead pool. A card with verified DM + verified email + social posts is not distinguished from a card with inferred DM + hunter email + no posts. Both ship as equally "ready". |
| S11-D5 | MEDIUM | `historical_rank` ships as raw 6-month array. Dashboard must compute trend itself. Card should include a pre-computed `rank_trend: "growing|stable|declining"` and `rank_trend_magnitude` (% ETV change over 3 months). |
| S11-D6 | LOW | `stage7_analyse` check for `vr_report` field uses presence of the whole stage7 dict, not the actual `vulnerability_report` subkey. If stage7 ran but VR is null, card is still eligible. |

### Prescriptions

| ID | Action | Effort |
|----|--------|--------|
| S11-P1 | Add `dm_quality` field to card: `"verified"` if `_dm_verified=True`, `"inferred"` otherwise. Surface in outreach template as context note. Gate HOT pool (composite >= 85) on `dm_quality="verified"`. | S |
| S11-P2 | Add `email_quality` field: map tier/source to `"verified"` (Leadmagic verify pass), `"likely"` (Hunter L2), `"extracted"` (Stage 3 scrape), `"unresolved"`. | S |
| S11-P3 | Write dropped domain minimal BU record: for every domain that exits at Stage 3/5, write a `status: "dropped"` record with domain, drop_reason, stage2 SERP data, and any Stage 3 partial output. | M |
| S11-P4 | Add `card_tier` field: `"A"` = verified DM + verified email + social posts; `"B"` = verified or inferred DM + email + no posts; `"C"` = eligible but all fields minimal. | S |
| S11-P5 | Precompute `rank_trend` from `historical_rank` array: compare most recent 3 months ETV vs previous 3 months. Store as `rank_trend: "growing|stable|declining"` and `rank_trend_delta_pct`. | S |
| S11-P6 | Tighten VR presence check: `if not stage7_analyse.get("vulnerability_report"): missing.append("vr_report")` | XS |

---

## Cross-Stage Analysis

### 1. Data Flow Gaps — Where Data Gets Lost

| Data | Produced | Consumed Downstream | Gap |
|------|----------|---------------------|-----|
| Stage 2: Facebook URL | Stage 2 SERP | Stage 11 card only | Not passed to Stage 3 for identity context or Stage 10 for outreach |
| Stage 3: dm_email (extracted from website) | Stage 3 Gemini | Stage 8 waterfall L0 (post D2.1B fix) | Pre-fix: not wired. Post-fix: flows correctly |
| Stage 3: services_offered | Stage 3 Gemini (post D2.1B) | Nowhere downstream | Extracted at zero cost but never used in VR, scoring, or outreach |
| Stage 4: competitor array (10 domains) | Stage 4 DFS | Stage 10 signal_ctx | Passed but not instructed in VR/MSG prompts — Gemini deprioritises |
| Stage 4: keyword delta (is_lost, is_down) | Stage 4 DFS | Stage 10 — used in VR | Works correctly — seen in orthodontists card ("754 lost keywords") |
| Stage 6: historical_rank (6 months) | Stage 6 DFS | Stage 10 signal_ctx, Stage 11 card | Passed to signal_ctx but VR prompt gives no instruction to use it |
| Stage 9: company profile metadata | Stage 9 BD scraper | Discarded | follower count, employee count, specialties — zero marginal cost, not captured |
| Stage 9: post engagement metrics | Stage 9 BD posts | Not in card signals_summary | Reaction/comment counts for top posts not surfaced |
| Stage 11: all data for dropped domains | Stages 2-3 | Nowhere | 9 dropped domains write no BU record |

### 2. Cost Optimisation

Using D2 per-domain averages (total cost = $2.9633 USD for 20 domains, 7 cards):

| Stage | Total USD (D2) | Per Domain | Per Card | ROI Assessment |
|-------|---------------|-----------|---------|----------------|
| Stage 3 (Gemini) | ~$0.40 | $0.020 | $0.057 | HIGH — identity is prerequisite for everything |
| Stage 4 (DFS signals) | ~$1.01 | $0.078 | $0.144 | HIGH — all scoring depends on this |
| Stage 9 (BD social) | $0.324 | $0.027 | $0.046 | LOW — 50% zero yield; $0.162 wasted on empty calls |
| Stage 10 (Gemini VR+MSG) | ~$0.60 | $0.050 | $0.086 | MEDIUM — runs on no-email domains (D2 bug, now fixed) |
| Stage 8 (email waterfall) | ~$0.35 | $0.029 | $0.050 | MEDIUM — 58% resolution rate at L2 (Hunter, free) |
| Stage 6 (historical rank) | ~$0.06 | $0.005 | $0.009 | HIGH — very cheap, high analytical value if used |
| Stage 7 (Gemini intent) | ~$0.15 | $0.013 | $0.021 | MEDIUM — produces outreach Stage 10 largely supersedes |

Cost reduction opportunities:

1. **Stage 9 zero-yield guard** (S9-P1): skip cost increment when no posts returned. At D2 zero-yield rate (50%), saves ~$0.162 on 12 domains = ~$0.014/domain saved.

2. **Stage 7 scope reduction**: Stage 7 produces `draft_email`, `draft_linkedin_note`, `draft_voice_script` that Stage 10 supersedes for email-found domains. For domains that will get Stage 10 output, Stage 7 messaging is redundant. Consider making Stage 7 produce intent scoring only (no draft outreach) — outreach drafting goes to Stage 10 exclusively. Estimated 40% reduction in Stage 7 token usage.

3. **Stage 10 LinkedIn-only path** (S10-P1): cheaper than full VR+MSG (single lighter Gemini call) for no-email domains with verified LinkedIn. Recovers outreach value at reduced cost vs full skip.

4. **Stage 8 ContactOut on score gate**: ContactOut is called for every non-dropped domain regardless of score. Consider gating ContactOut on composite_score >= 50 (not just any survival past Stage 5). Low-score domains are unlikely to become cards and ContactOut is a credit spend.

### 3. Cascade Failure — Stage 3 DM Misidentification

Stage 3 Gemini infers the DM from website text, ABN/ASIC data, LinkedIn SERP results, and GMB owner information. When it gets this wrong, the error propagates:

| Stage | Cascade Effect |
|-------|---------------|
| Stage 3 wrong name | Stage 8 LinkedIn search uses wrong name → no LinkedIn URL found |
| Stage 3 wrong name | Stage 8 email waterfall uses wrong name → Hunter/Leadmagic returns wrong person's email |
| Stage 3 wrong name | Stage 10 email addresses wrong person by first name |
| Stage 3 wrong name | Stage 10 LinkedIn note sent to wrong person |
| Stage 3 wrong name | Stage 9 DM posts scraped for wrong LinkedIn profile (if URL was found) |

**Correction mechanisms in current pipeline: none.** Stage 8 LinkedIn verification (`_dm_verified=True`) checks the LinkedIn profile's company matches the domain, but does not re-check the name. A profile for "James Smith" at the right company passes `dm_verified=True` even if Stage 3 inferred "Jane Smith". The `match_confidence` score is company-level, not person-level.

**Mitigation needed:** Stage 8 LinkedIn verification should compare the BD profile's `first_name + last_name` against `stage3.dm_candidate.name` using fuzzy matching. If confidence < 0.7, flag as `dm_name_mismatch: true` and surface on card. This does not require additional API calls — the BD profile data is already fetched.

### 4. GOV-8 Compliance — Per Stage

| Stage | Data Being Discarded (not written to BU) |
|-------|------------------------------------------|
| Stage 2 | SERP raw results beyond ABN/LinkedIn/Facebook top picks |
| Stage 3 | `services_offered`, `primary_phone`, `office_address` post D2.1B (now extracted but not in signals_summary) |
| Stage 4 | Full competitor array (only 10 entries in signals, but top 3 not pre-surfaced for outreach) |
| Stage 4 | `clickstream_etv`, `clickstream_gender_distribution`, `clickstream_age_distribution` (all null in D2 — DFS not returning them) |
| Stage 6 | Historical rank raw array stored in card, no pre-computed trend |
| Stage 9 | Company profile metadata (followers, employees, specialties, founded) |
| Stage 9 | Post engagement metrics (reactions, comments, reposts) |
| Stages 2-3 | All data for dropped domains — 9 domains in D2 |

Worst violation: dropped domain data. When a domain is dropped at Stage 3 (enterprise, no DM found), Stages 1-2 have already paid for SERP/ABN/GMB data. None of that is persisted to BU. At scale (30-50% drop rate), this represents meaningful data loss.

### 5. Gate Calibration

| Gate | Stage | Current Threshold | Assessment |
|------|-------|-------------------|-----------|
| Enterprise/chain filter | Stage 3 | LLM judgment: >20 locations, chain brand, franchise | CORRECT — 6/8 drops were valid (franchise, chain). Review enterprise_or_chain false-positive rate. |
| DM not found | Stage 3 | LLM cannot identify a decision-maker | CORRECT — 1/8 drops. Hard to verify without manual review. |
| Viability filter | Stage 5 | LLM judgment: directory/aggregator/not SMB | CORRECT — 1 drop (fitness directory). |
| ALS score gate | Stage 5 | composite_score >= 20 (PRE_ALS_GATE) | TOO LOW — all 12 non-dropped domains passed. Gate is not filtering anything. With a min card score of 65 in D2, a threshold of 20 is near-zero signal. Raise to 40. |
| Stage 6 skip | Stage 6 | Runs for all non-dropped | LOW ROI TO GATE — cost $0.005/domain, high analytical value. Keep unconditional. |
| Stage 8/10 email gate | Stage 10 | email_data.get("email") | CORRECT in current code. Consider LinkedIn-only path as exception. |
| Stage 11 lead pool | Stage 11 | dm_name + email + scores + vr_report | MISSING: should also gate on composite_score >= 40 minimum. A score of 25 with email found should not be eligible. |

The PRE_ALS_GATE at 20 is the most mis-calibrated gate in the pipeline. It was likely set conservatively to avoid over-dropping. However, all non-enterprise domains in D2 scored >= 60. A gate at 40 would have the same pass rate on this data while providing meaningful protection against edge cases.

The Stage 11 lead pool gate not checking composite_score means a domain that somehow passes Stage 5 viability but has a score of 22 (below the original ALS intent) can still become a card.

### 6. Timing Bottlenecks

From D2 total timings (summed across all domains):

| Stage | Total Wall Clock | Domains | Avg | Parallelisable? |
|-------|-----------------|---------|-----|-----------------|
| Stage 4 | 1249.47s | 13 | 96.11s | YES — already parallel within cohort (asyncio.gather) |
| Stage 3 | 1132.97s | 20 | 56.65s | YES — already parallel within cohort |
| Stage 10 | 310.57s | 12 | 25.88s | YES — parallel across domains; sequential within domain (VR→MSG) |
| Stage 9 | 304.83s | 12 | 25.40s | YES — already parallel within cohort |
| Stage 2 | 266.28s | 20 | 13.31s | YES — already parallel within cohort |
| Stage 7 | 272.33s | 12 | 22.69s | YES — already parallel within cohort |
| Stage 8 | 205.56s | 12 | 17.13s | YES — already parallel within cohort |

Wall clock of 399.2s for 20 domains with all parallelism active. The main bottleneck is Stage 4 (DFS API — external rate limit) and Stage 3 (Gemini with grounding — 3 API calls per domain). These are not reducible without API plan upgrades or reduced per-domain scope.

**Stages 9+10 sequential dependency:** In the current orchestration, Stage 9 runs before Stage 10 because Stage 10 needs the posts. This is correct. However within the Stage 9→10 chain, there is an unnecessary sequential wait: Stage 9 blocks Stage 10 even when Stage 9 yields zero posts. If Stage 9 returns `dm_posts_count=0` and `company_posts_count=0`, Stage 10 can proceed immediately with empty social context — no need to wait for Stage 9 to fully complete.

**Stage 7 + Stage 10 redundancy:** Both stages produce outreach. They run sequentially (7 then 10). Stage 10 supersedes Stage 7 for email-found domains. Consider running Stage 7 and Stage 9 in parallel (they are independent), then Stage 10 after both complete. This saves Stage 7 wall clock from blocking Stage 9 in domains where Stage 7 is already resolved.

**Across-stage parallelisation opportunity:** Stages 6 and 7 both depend on Stage 5 output but are independent of each other. They could run in parallel. Current code runs them sequentially. At ~23s for Stage 7 and ~1s for Stage 6, this is a 22s saving per domain (though at cohort level these are already parallelised across domains).

---

## Summary of All Issues by Priority

### P0 — Blocking / Data Integrity

| ID | Stage | Finding |
|----|-------|---------|
| S11-D3 | 11 | Dropped domains write no BU record — data permanently lost |
| S11-D1 | 11 | dm_verified=False cards enter lead pool without flag — customer risk |
| S10-D1 | 10 | LinkedIn-verified no-email domains get no outreach assets |

### P1 — High / Revenue Impact

| ID | Stage | Finding |
|----|-------|---------|
| S9-D1 | 9 | 50% zero-yield Stage 9 runs waste $0.027 each |
| S10-D2 | 10 | Historical trend ignored in VR — urgency signal missed |
| S10-D3 | 10 | Competitor context not used in VR — strongest specificity hook unused |
| S11-D2 | 11 | Email quality not surfaced — customer can't prioritise |
| Gate-5 | Cross | PRE_ALS_GATE at 20 filters nothing — raise to 40 |

### P2 — Medium / Quality

| ID | Stage | Finding |
|----|-------|---------|
| S9-D2 | 9 | GOV-8: company profile metadata discarded |
| S9-D3 | 9 | DM activity signal not scored or used in channel strategy |
| S10-D4 | 10 | SMS is trimmed email, not distinct channel |
| S11-D4 | 11 | No card quality tier — flat lead pool |
| S11-D5 | 11 | historical_rank ships as raw array — no pre-computed trend |
| Cross-3 | Cross | No DM name mismatch detection in Stage 8 LinkedIn verify |

### P3 — Low / Improvements

| ID | Stage | Finding |
|----|-------|---------|
| S9-D4 | 9 | Stale post (2023) used as timeline hook — date filter not enforced |
| S10-D5 | 10 | Post date filter not applied to MSG prompt |
| S11-D6 | 11 | VR presence check uses stage7 dict existence, not subkey |
| Cross-6 | Cross | Stage 6+7 could run in parallel (currently sequential within domain) |
