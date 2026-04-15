# Pipeline F v2.1 — Inter-Module Data Contracts Audit

**Audit date:** 2026-04-14
**Auditor:** build-2 (read-only, zero code changes)
**Source branch:** directive/f-refactor-01

## Methodology

For each Stage N → Stage N+1 boundary:
1. Read the `return` statement (or equivalent dict construction) in Stage N's module.
2. Read every `.get()` call in Stage N+1 that consumes Stage N's output.
3. Compare field names verbatim.

All file:line references below are to the exact source lines read.

---

## Stage 1 → Stage 2

Stage 1 (discover loop) writes into the pipeline list via `_new_domain()`:

```python
# cohort_runner.py:104-124
return {
    "domain": domain,
    "category": category,
    "stage2": None,      # populated by Stage 2
    ...
}
```

Stage 2 (`_run_stage2`) reads:
```python
# cohort_runner.py:136
result = await run_serp_verify(dfs, domain_data["domain"])
```

### Stage 1 → Stage 2
| Field | Written by Stage 1 | Read by Stage 2 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| `domain` | `_new_domain()` cohort_runner.py:105 | `domain_data["domain"]` cohort_runner.py:136 | YES | None |
| `category` | `_new_domain()` cohort_runner.py:106 | Not read by Stage 2 | N/A — consumed later | None |

**No mismatches at this boundary.**

---

## Stage 2 → Stage 3

Stage 2 (`run_serp_verify`) return dict — `serp_verify.py:161-168`:
```python
return {
    "serp_business_name": biz_name,
    "serp_abn": _extract_abn(q_abn),
    "serp_company_linkedin": _extract_company_linkedin(q_li),
    "serp_dm_candidate": _extract_dm_candidate(q_dm),
    "serp_facebook_url": _extract_facebook_url(q_fb),
    "_cost": dfs.total_cost_usd - cost_before,
}
```

Stage 3 (`_run_stage3`) reads from `domain_data["stage2"]` via `serp` variable — `cohort_runner.py:149`:
```python
serp = domain_data.get("stage2") or {}
```
Then `gemini_client.py:81-89` reads from `serp_data` (the same dict):
```python
if serp_data.get("serp_business_name"):
if serp_data.get("serp_abn"):
if serp_data.get("serp_company_linkedin"):
if serp_data.get("serp_dm_candidate"):
```

### Stage 2 → Stage 3
| Field | Written by Stage 2 | Read by Stage 3 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| `serp_business_name` | serp_verify.py:162 | gemini_client.py:82 | YES | None |
| `serp_abn` | serp_verify.py:163 | gemini_client.py:84 | YES | None |
| `serp_company_linkedin` | serp_verify.py:164 | gemini_client.py:85 | YES | None |
| `serp_dm_candidate` | serp_verify.py:165 | gemini_client.py:86 | YES | None |
| `serp_facebook_url` | serp_verify.py:166 | **NOT read** by Stage 3 | WRITTEN, NEVER READ at Stage 3 | LOW — Facebook deferred to post-launch by design |
| `_cost` | serp_verify.py:167 | `result.get("_cost", 0)` cohort_runner.py:138 | YES (consumed in wrapper, not passed to Gemini) | None |

**One unused field:** `serp_facebook_url` is written by Stage 2 but not consumed by Stage 3 Gemini prompt. This is intentional (doc comment: "Facebook deferred to post-launch") but it IS consumed later in Stage 11 via `stage2_verify.get("serp_facebook_url")` — funnel_classifier.py:68.

---

## Stage 3 → Stage 4

Stage 3 (`call_f3a`) returns `result` dict where `domain_data["stage3"] = result.get("content") or {}` — `cohort_runner.py:165-166`.

Stage 3 content schema (comprehend_schema_f3a.py:19-51):
```
business_name, location{suburb,state,...}, industry_category, entity_type_hint,
staff_estimate_band, is_enterprise_or_chain, website_reachable, primary_phone,
primary_email, social_urls{linkedin,facebook,instagram},
dm_candidate{name, role, linkedin_url}
```
Plus internal verification fields added by `_verify_dm`: `_dm_verified`, `_dm_verification_note`, `_dm_corrected_from`, `_entity_name`.

Stage 4 (`_run_stage4`) reads from `domain_data["stage3"]`:
```python
# cohort_runner.py:186
biz = domain_data.get("stage3", {}).get("business_name")
```
And passes to `build_signal_bundle` — `dfs_signal_bundle.py:26-32` — which takes only `domain` and `business_name`. Stage 3 output is otherwise NOT passed into Stage 4.

### Stage 3 → Stage 4
| Field | Written by Stage 3 | Read by Stage 4 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| `business_name` | comprehend_schema_f3a.py:20 | `domain_data.get("stage3", {}).get("business_name")` cohort_runner.py:186 | YES | None |
| All other Stage 3 fields | comprehend_schema_f3a.py:21-51 | **NOT read** by Stage 4 | Written, not consumed at this boundary | NONE — Stage 4 is a DFS-only signal fetch; Stage 3 fields are consumed by Stages 5, 7, 8, 11 |

**No contract mismatches.** Stage 4 only needs `business_name` for GMB/brand SERP queries.

---

## Stage 4 → Stage 5

Stage 4 (`build_signal_bundle`) return dict — `dfs_signal_bundle.py:170-183`:
```python
return {
    "domain": domain,
    "rank_overview": rank_overview_clean,
    "competitors": competitors_list,
    "keywords": keywords_list,
    "technologies": tech_list,
    "gmb": gmb,
    "backlinks": backlinks,
    "brand_serp": brand_serp_data,
    "indexed_pages": indexed,
    "ads_domain": ads_domain,
    "ads_competitors": ads_competitors,
    "cost_usd": round(dfs.total_cost_usd, 6),
}
```

Stage 5 (`score_prospect`) reads from `signal_bundle` — `prospect_scorer.py:83-93`:
```python
ro = signal_bundle.get("rank_overview") or {}
gmb = signal_bundle.get("gmb") or {}
ads_domain = signal_bundle.get("ads_domain") or {}
indexed = signal_bundle.get("indexed_pages") or 0
organic_etv = ro.get("dfs_organic_etv") or 0
organic_kw = ro.get("dfs_organic_keywords") or 0
paid_kw = ro.get("dfs_paid_keywords") or 0
gmb_rating = gmb.get("gmb_rating") or 0
gmb_reviews = gmb.get("gmb_review_count") or 0
is_running_ads = ads_domain.get("is_running_ads") or False
```
And later:
```python
tech = signal_bundle.get("technologies") or []       # prospect_scorer.py:101
pos_11_20 = ro.get("dfs_organic_pos_11_20") or 0    # prospect_scorer.py:185
signal_bundle.get("gmb")                              # prospect_scorer.py:202 (truthiness check)
```

Stage 5 also reads Stage 3 output (`f3a_output`) — `prospect_scorer.py:107-210`:
```python
f3a_output.get("abn") or f3a_output.get("serp_abn")   # prospect_scorer.py:107
f3a_output.get("entity_type_hint")                      # prospect_scorer.py:114
f3a_output.get("staff_estimate_band")                   # prospect_scorer.py:103
f3a_output.get("primary_phone")                         # prospect_scorer.py:196
f3a_output.get("primary_email")                         # prospect_scorer.py:198
f3a_output.get("dm_candidate")                          # prospect_scorer.py:205
f3a_output.get("social_urls")                           # prospect_scorer.py:209
f3a_output.get("is_enterprise_or_chain", False)         # prospect_scorer.py:217
f3a_output.get("industry_category")                     # prospect_scorer.py:249
```

### Stage 4 → Stage 5 (signal_bundle fields)
| Field | Written by Stage 4 | Read by Stage 5 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| `rank_overview` | dfs_signal_bundle.py:172 | `signal_bundle.get("rank_overview")` prospect_scorer.py:83 | YES | None |
| `gmb` | dfs_signal_bundle.py:175 | `signal_bundle.get("gmb")` prospect_scorer.py:84 | YES | None |
| `ads_domain` | dfs_signal_bundle.py:180 | `signal_bundle.get("ads_domain")` prospect_scorer.py:85 | YES | None |
| `indexed_pages` | dfs_signal_bundle.py:179 | `signal_bundle.get("indexed_pages")` prospect_scorer.py:86 | YES | None |
| `technologies` | dfs_signal_bundle.py:174 | `signal_bundle.get("technologies")` prospect_scorer.py:101 | YES | None |
| `competitors` | dfs_signal_bundle.py:173 | **NOT read** by Stage 5 | Written, never read by Stage 5 | LOW — passed to Stage 7 Gemini context |
| `keywords` | dfs_signal_bundle.py:173 | **NOT read** by Stage 5 | Written, never read by Stage 5 | LOW — passed to Stage 7 Gemini context |
| `backlinks` | dfs_signal_bundle.py:176 | **NOT read** by Stage 5 | Written, never read by Stage 5 | LOW — passed to Stage 7 Gemini context |
| `brand_serp` | dfs_signal_bundle.py:177 | **NOT read** by Stage 5 | Written, never read by Stage 5 | LOW — passed to Stage 7 Gemini context |
| `ads_competitors` | dfs_signal_bundle.py:181 | **NOT read** by Stage 5 | Written, never read by Stage 5 | LOW — available to Stage 7 |
| `cost_usd` | dfs_signal_bundle.py:182 | **NOT read** (cost tracked separately by runner) | Written, not consumed downstream | NONE |
| `domain` | dfs_signal_bundle.py:171 | **NOT read** by Stage 5 | Written, not consumed | NONE |

**Sub-field contract check — `rank_overview` internals:**

Stage 4 calls `dfs.domain_rank_overview()` which returns a dict. Stage 5 reads sub-fields:
- `ro.get("dfs_organic_etv")` — prospect_scorer.py:89
- `ro.get("dfs_organic_keywords")` — prospect_scorer.py:90
- `ro.get("dfs_paid_keywords")` — prospect_scorer.py:91
- `ro.get("dfs_organic_pos_11_20")` — prospect_scorer.py:185

**MISMATCH RISK:** Stage 4 stores the raw `domain_rank_overview()` client output verbatim. The field names `dfs_organic_etv`, `dfs_organic_keywords`, `dfs_paid_keywords`, `dfs_organic_pos_11_20` are assumed to be what the DFSLabsClient returns. If the client normalises to different key names, Stage 5 will silently get 0 for all these via `.get() or 0` defaults — **scoring will silently zero-out with no error**. This is the highest-risk silent failure point in the pipeline.

**Sub-field contract check — `gmb` internals:**

Stage 5 reads `gmb.get("gmb_rating")` and `gmb.get("gmb_review_count")`. These are assumed to be the exact field names returned by `dfs.maps_search_gmb()`. Same silent-zero risk as above.

**Sub-field contract check — `ads_domain` internals:**

Stage 5 reads `ads_domain.get("is_running_ads")`. Same risk.

### Stage 3 → Stage 5 (f3a_output fields)
| Field | Written by Stage 3 | Read by Stage 5 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| `entity_type_hint` | comprehend_schema_f3a.py:27 | `f3a_output.get("entity_type_hint")` prospect_scorer.py:114 | YES | None |
| `staff_estimate_band` | comprehend_schema_f3a.py:28 | `f3a_output.get("staff_estimate_band")` prospect_scorer.py:103 | YES | None |
| `primary_phone` | comprehend_schema_f3a.py:31 | `f3a_output.get("primary_phone")` prospect_scorer.py:196 | YES | None |
| `primary_email` | comprehend_schema_f3a.py:32 | `f3a_output.get("primary_email")` prospect_scorer.py:198 | YES | None |
| `dm_candidate` | comprehend_schema_f3a.py:38 | `f3a_output.get("dm_candidate")` prospect_scorer.py:205 | YES | None |
| `social_urls` | comprehend_schema_f3a.py:33 | `f3a_output.get("social_urls")` prospect_scorer.py:209 | YES | None |
| `is_enterprise_or_chain` | comprehend_schema_f3a.py:29 | `f3a_output.get("is_enterprise_or_chain", False)` prospect_scorer.py:217 | YES | None |
| `industry_category` | comprehend_schema_f3a.py:26 | `f3a_output.get("industry_category")` prospect_scorer.py:249 | YES | None |
| `abn` | **NOT in Stage 3 schema** (explicitly excluded) | `f3a_output.get("abn")` prospect_scorer.py:107 | **MISMATCH** | MEDIUM — Stage 5 tries `f3a_output.get("abn") or f3a_output.get("serp_abn")`; Stage 3 schema comment says "ABN is NOT in this schema — ABN comes from Stage 2 VERIFY SERP only" (comprehend_schema_f3a.py:5). Stage 5 will always get None from `get("abn")` and fall through to `get("serp_abn")` which is also not in Stage 3 schema. The ABN budget signal will **always be 0** unless Stage 3 Gemini happens to return an `abn` field outside the schema, or the fallback to Stage 2's `serp_abn` path is wrong. |

**CRITICAL MISMATCH:** `prospect_scorer.py:107` reads `f3a_output.get("abn") or f3a_output.get("serp_abn")`. Neither field appears in the Stage 3 IDENTIFY schema (comprehend_schema_f3a.py). The `abn` from Stage 2 sits at `domain_data["stage2"]["serp_abn"]`, not inside `domain_data["stage3"]`. Stage 5 receives `domain_data.get("stage3", {})` as `f3a_output` (cohort_runner.py:205) and `domain_data.get("stage4", {})` as `signal_bundle` — neither contains the Stage 2 ABN. The ABN budget signal (+3 points) is always suppressed, silently.

---

## Stage 5 → Stage 6

Stage 5 returns — `prospect_scorer.py:261-271`:
```python
return {
    "budget_score": budget,
    "pain_score": pain,
    "reachability_score": reach,
    "fit_score": fit,
    "composite_score": composite,
    "etv_percentile": round(etv_pct, 3),
    "passed_gate": passed_gate,
    "is_viable_prospect": is_viable,
    "viability_reason": viability_reason,
    "score_breakdown": breakdown,
}
```

Stage 6 (`_run_stage6` wrapper) reads:
```python
# cohort_runner.py:229
if (domain_data.get("stage5") or {}).get("composite_score", 0) < 60:
    return domain_data
composite = domain_data["stage5"]["composite_score"]
```
Then calls `run_stage6_enrich(dfs, domain_data["domain"], composite)` — no other Stage 5 fields consumed.

### Stage 5 → Stage 6
| Field | Written by Stage 5 | Read by Stage 6 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| `composite_score` | prospect_scorer.py:265 | `domain_data["stage5"]["composite_score"]` cohort_runner.py:232 | YES | None |
| All other fields | prospect_scorer.py:261-270 | Not read by Stage 6 | Written, consumed later (Stage 11) | None |

**No mismatches.**

---

## Stage 6 → Stage 7

Stage 6 (`run_stage6_enrich`) return dict — `stage6_enrich.py:61-65`:
```python
return {
    "enriched": True,
    "historical_rank": historical,
    "months_available": months,
    "_cost": dfs.total_cost_usd - cost_before,
}
```

Stage 7 (`_run_stage7`) reads from `domain_data["stage3"]` and `domain_data["stage4"]` — `cohort_runner.py:247-250`:
```python
identity = domain_data.get("stage3") or {}
signals = domain_data.get("stage4") or {}
result = await gemini.call_f3b(f3a_output=identity, signal_bundle=signals)
```
Stage 6 output is **NOT passed to Stage 7**. It is only consumed by Stage 10 and Stage 11.

### Stage 6 → Stage 7
| Field | Written by Stage 6 | Read by Stage 7 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| All Stage 6 fields | stage6_enrich.py:58-65 | **NOT read** by Stage 7 | By design | LOW — Stage 6 data flows to Stage 10 and Stage 11 only |

**No mismatch — Stage 6 skips Stage 7 by design (historical enrichment is used for VR, not for Stage 7 ANALYSE).**

---

## Stage 7 → Stage 8

Stage 7 `call_f3b` returns `result.get("content") or {}` stored as `domain_data["stage7"]`.

Stage 7 content schema (comprehend_schema_f3b.py):
```
intent_band_final, intent_evidence_final, vulnerability_report{summary, strengths,
vulnerabilities[], gmb_health{rating,reviews,assessment}, recommended_services, urgency},
draft_email{subject, body}, draft_linkedin_note, draft_voice_script
```

Stage 8 (`_run_stage8`) reads from `domain_data["stage3"]` (identity) and `domain_data["stage2"]` (serp) — `cohort_runner.py:263-289`. **Stage 7 output is NOT read by Stage 8.**

### Stage 7 → Stage 8
| Field | Written by Stage 7 | Read by Stage 8 | Match | Risk |
|-------|-------------------|-----------------|-------|------|
| All Stage 7 fields | comprehend_schema_f3b.py | **NOT read** by Stage 8 | By design | None — Stage 8 is contact enrichment, Stage 7 is analytical |

**No mismatch — Stage 8 is contact acquisition and does not consume Stage 7 analysis.**

---

## Stage 8a (verify_fills) → Stage 8b (contact_waterfall)

Stage 8a (`run_verify_fills`) return dict — `verify_fills.py:228-238`:
```python
return {
    "abn": abn,
    "abn_status": "verified_serp" if abn else "unresolved",
    "abn_source": "dfs_serp_abr" if abn else "unresolved",
    "dm_linkedin_url": dm_linkedin,
    "company_linkedin_url": company_linkedin,
    "gmb_rating": None,
    "gmb_reviews": None,
    "gmb_category": None,
    "_cost": 0.006,
}
```

Stage 8b (`run_contact_waterfall`) is called in `cohort_runner.py:279-295`:
```python
contacts = await run_contact_waterfall(
    dm_name=dm.get("name"),
    dm_title=dm.get("role"),
    business_name=identity.get("business_name", ""),
    domain=domain_data["domain"],
    f3a_linkedin_url=dm.get("linkedin_url"),
    f4_linkedin_url=fills.get("dm_linkedin_url"),
    company_linkedin_url=(
        fills.get("company_linkedin_url") or serp.get("serp_company_linkedin")
    ),
    entity_type=identity.get("entity_type_hint"),
    business_phone=identity.get("primary_phone"),
)
```

### Stage 8a → Stage 8b
| Field | Written by Stage 8a | Read by Stage 8b | Match | Risk |
|-------|--------------------|--------------------|-------|------|
| `dm_linkedin_url` | verify_fills.py:231 | `fills.get("dm_linkedin_url")` cohort_runner.py:286 | YES | None |
| `company_linkedin_url` | verify_fills.py:232 | `fills.get("company_linkedin_url")` cohort_runner.py:287 | YES | None |
| `abn` | verify_fills.py:229 | **NOT read** by Stage 8b | Written, never consumed by contact waterfall | LOW — ABN is not needed for contact finding, but also never surfaces into Stage 11 card via this path |
| `abn_status` | verify_fills.py:230 | **NOT read** | Written, consumed by Stage 11 | NONE |
| `abn_source` | verify_fills.py:230 | **NOT read** | Written, consumed by Stage 11 | NONE |
| `gmb_rating` | verify_fills.py:233 (always None) | **NOT read** | Placeholder — always None | LOW — dead field. Stage 8a never populates GMB data. Stage 5 relies on Stage 4 GMB data instead. |
| `gmb_reviews` | verify_fills.py:234 (always None) | **NOT read** | Dead placeholder | LOW |
| `gmb_category` | verify_fills.py:235 (always None) | **NOT read** | Dead placeholder | LOW |
| `_cost` | verify_fills.py:236 (hardcoded 0.006) | **NOT read** | Cost absorbed into `domain_data["cost_usd"] += 0.023` hardcode in wrapper | LOW — actual DFS SERP call cost not tracked per-domain; hardcoded estimate used |

**MEDIUM RISK — Dead placeholder fields:** `gmb_rating`, `gmb_reviews`, `gmb_category` in Stage 8a output are always `None`. They were likely intended to be populated from a GMB lookup but the implementation was never wired up. Stage 5 reads GMB from Stage 4 signal bundle instead, so functionally there is no regression, but the fields add confusion.

**MEDIUM RISK — ABN availability:** The ABN resolved by Stage 8a (`verify_fills.py:229`) is stored in `domain_data["stage8_verify"]["abn"]`. Stage 11 (`funnel_classifier.py`) reads ABN from `stage2_verify.get("serp_abn")` (funnel_classifier.py:67) — i.e., from Stage 2, not Stage 8a. Stage 8a's higher-quality compound SERP ABN is **never surfaced into the final card**. This is a silent data quality loss.

---

## Stage 8b (contact_waterfall) → Stage 9

Stage 8b (`run_contact_waterfall`) return dict — `contact_waterfall.py:411-416`:
```python
return {"linkedin": linkedin, "email": email, "mobile": mobile}
```

Where:
- `linkedin`: `{linkedin_url, source, tier, match_type, match_company, match_confidence, ...}`
- `email`: `{email, source, tier, verified?, confidence?}` (or `{email: None, source: "unresolved", tier: "L5"}`)
- `mobile`: `{mobile, source, tier, ...}` (or `{mobile: None, source: "unresolved", tier: "L4"}`)

Stage 9 (`_run_stage9`) reads from `domain_data["stage8_verify"]` (8a output), NOT Stage 8b:
```python
# cohort_runner.py:304-308
fills = domain_data.get("stage8_verify") or {}
dm_li = fills.get("dm_linkedin_url")
company_li = fills.get("company_linkedin_url") or (
    (domain_data.get("stage2") or {}).get("serp_company_linkedin")
)
```

### Stage 8b → Stage 9
| Field | Written by Stage 8b | Read by Stage 9 | Match | Risk |
|-------|--------------------|--------------------|-------|------|
| `linkedin` | contact_waterfall.py:416 | **NOT read** by Stage 9 | By design | MEDIUM — Stage 9 uses Stage 8a's `dm_linkedin_url` (the candidate URL) NOT the Stage 8b verified URL. Stage 8b may have REJECTED the candidate URL (match_type="no_match") but Stage 9 still attempts to scrape the unverified candidate. |
| `email` | contact_waterfall.py:416 | Not read by Stage 9 | By design | None |
| `mobile` | contact_waterfall.py:416 | Not read by Stage 9 | By design | None |

**MEDIUM RISK — Stage 9 uses unverified LinkedIn URL:** Stage 9 (cohort_runner.py:304-305) reads `dm_linkedin_url` from Stage 8a verify_fills (the DFS SERP-discovered candidate URL), not from Stage 8b `stage8_contacts["linkedin"]["linkedin_url"]` (the L2-verified URL). If Stage 8b's L2 scraper rejected the URL as a company mismatch, Stage 9 still scrapes the rejected URL. The correct source for Stage 9 social scraping should be `domain_data["stage8_contacts"]["linkedin"]["linkedin_url"]` (Stage 8b L2 verified). Using the Stage 8a candidate is functionally incorrect — posts may be scraped for the wrong person.

---

## Stage 9 → Stage 10

Stage 9 (`run_stage9_social`) return dict — `stage9_social.py:81-87`:
```python
return {
    "dm_posts": dm_posts,
    "dm_posts_count": len(dm_posts),
    "company_posts": company_posts,
    "company_posts_count": len(company_posts),
    "_cost": 0.027,
}
```

Stage 10 (`run_stage10_vr_and_messaging`) reads from `stage9_social` param — `enhanced_vr.py:181-186`:
```python
dm_posts = stage9_social.get("dm_posts") or []
company_posts = stage9_social.get("company_posts") or []
```

### Stage 9 → Stage 10
| Field | Written by Stage 9 | Read by Stage 10 | Match | Risk |
|-------|-------------------|--------------------|-------|------|
| `dm_posts` | stage9_social.py:82 | `stage9_social.get("dm_posts")` enhanced_vr.py:181 | YES | None |
| `company_posts` | stage9_social.py:84 | `stage9_social.get("company_posts")` enhanced_vr.py:182 | YES | None |
| `dm_posts_count` | stage9_social.py:83 | `len(dm_posts)` (recomputed inline) enhanced_vr.py:183 | N/A — count recomputed | None |
| `company_posts_count` | stage9_social.py:85 | Not read by Stage 10 | Written, unused | LOW |
| `_cost` | stage9_social.py:86 | Not read by Stage 10 (cost added by wrapper) | Written, consumed by cohort_runner wrapper | None |

**No critical mismatches.**

---

## Stage 10 → Stage 11

Stage 10 (`run_stage10_vr_and_messaging`) return dict — `enhanced_vr.py:209-214`:
```python
return {
    "vr_report": vr_report,
    "outreach": outreach,
    "cost_usd": round(total_cost, 6),
    "f_status": f_status,
}
```

Stage 11 (`assemble_card`) reads from `stage10_vr_msg` param — `funnel_classifier.py:76-80`:
```python
"vulnerability_report": (stage10_vr_msg or {}).get("vr_report")
    or stage7_analyse.get("vulnerability_report"),
"outreach": (stage10_vr_msg or {}).get("outreach"),
```

### Stage 10 → Stage 11
| Field | Written by Stage 10 | Read by Stage 11 | Match | Risk |
|-------|--------------------|--------------------|-------|------|
| `vr_report` | enhanced_vr.py:210 | `(stage10_vr_msg or {}).get("vr_report")` funnel_classifier.py:76 | YES | None |
| `outreach` | enhanced_vr.py:211 | `(stage10_vr_msg or {}).get("outreach")` funnel_classifier.py:78 | YES | None |
| `cost_usd` | enhanced_vr.py:212 | Not read by Stage 11 (consumed by runner cohort_runner.py:346) | By design | None |
| `f_status` | enhanced_vr.py:213 | **NOT read** by Stage 11 | Written, never consumed downstream | LOW — partial/failed Stage 10 still produces a card without any flag |

**LOW RISK — `f_status` not propagated to card:** Stage 10 returns `f_status` ("success" / "partial" / "failed") but Stage 11 never reads it. A "partial" or "failed" Stage 10 still generates a card. The card's `lead_pool_eligible` check at funnel_classifier.py:48 checks `email_data.get("email")` but not Stage 10 status. A domain could be `lead_pool_eligible=True` with `vr_report=None` if outreach was produced but VR was not (partial).

---

## Stage 11 — Final Card Input Audit

`assemble_card` (funnel_classifier.py:11-86) receives:

| Param | Source in runner | Stage |
|-------|-----------------|-------|
| `stage2_verify` | `domain_data.get("stage2") or {}` | Stage 2 SERP |
| `stage3_identity` | `domain_data.get("stage3") or {}` | Stage 3 Gemini |
| `stage4_signals` | `domain_data.get("stage4") or {}` | Stage 4 DFS bundle |
| `stage5_scores` | `domain_data.get("stage5") or {}` | Stage 5 scorer |
| `stage7_analyse` | `domain_data.get("stage7") or {}` | Stage 7 Gemini |
| `stage8_contacts` | `domain_data.get("stage8_contacts") or {}` | Stage 8b waterfall |
| `stage9_social` | `domain_data.get("stage9") or {}` | Stage 9 social |
| `stage10_vr_msg` | `domain_data.get("stage10") or {}` | Stage 10 VR+MSG |
| `stage6_enrich` | `domain_data.get("stage6") or {}` | Stage 6 enrich |

Fields read by Stage 11 from `stage2_verify` (Stage 2):
```python
stage2_verify.get("serp_abn")              # funnel_classifier.py:67
stage2_verify.get("serp_company_linkedin")  # funnel_classifier.py:68
stage2_verify.get("serp_facebook_url")      # funnel_classifier.py:69
```

**MISMATCH — ABN source:** Stage 11 reads ABN from `stage2_verify.get("serp_abn")` (Stage 2 SERP). Stage 8a (`run_verify_fills`) runs a compound SERP with suburb/state enrichment and may find a better ABN, stored at `domain_data["stage8_verify"]["abn"]`. Stage 11 never reads Stage 8a's ABN. The card will use the Stage 2 basic SERP ABN (or null) even if Stage 8a found a better one.

**MISMATCH — company_linkedin source:** Stage 11 reads `stage2_verify.get("serp_company_linkedin")` (Stage 2). Stage 8a also resolves company LinkedIn via `fill_company_linkedin_via_serp()` → `verify_fills.py:232`. Stage 8b waterfall also receives company_linkedin_url (cohort_runner.py:287). Stage 11 only reads Stage 2's value. If Stage 2 returned None but Stage 8a found it, the card's `company_linkedin_url` is still None.

### Stage 11 Final Card Field Sources
| Card field | Expected source | Actual source in Stage 11 | Risk |
|-----------|----------------|--------------------------|------|
| `abn` | Best available (Stage 2 or Stage 8a) | Only Stage 2 `serp_abn` (funnel_classifier.py:67) | MEDIUM — Stage 8a enriched ABN silently discarded |
| `company_linkedin_url` | Best available | Only Stage 2 `serp_company_linkedin` (funnel_classifier.py:68) | MEDIUM — Stage 8a LinkedIn enrichment silently discarded |
| `facebook_url` | Stage 2 | Stage 2 `serp_facebook_url` (funnel_classifier.py:69) | None |
| `vulnerability_report` | Stage 10 or Stage 7 fallback | `(stage10_vr_msg).get("vr_report") or stage7_analyse.get("vulnerability_report")` funnel_classifier.py:76-77 | None — good fallback |
| `outreach` | Stage 10 only | `(stage10_vr_msg).get("outreach")` funnel_classifier.py:78 | LOW — no Stage 7 fallback for outreach. If Stage 10 fails/skips (no email gate), outreach is None |
| `intent_band` | Stage 7 | `stage7_analyse.get("intent_band_final")` funnel_classifier.py:79 | None |

---

## Summary of Findings

### CRITICAL
| ID | Boundary | Finding |
|----|----------|---------|
| C1 | Stage 3 → Stage 5 | `prospect_scorer.py:107` reads `f3a_output.get("abn") or f3a_output.get("serp_abn")` but neither key exists in Stage 3 schema (comprehend_schema_f3a.py). ABN budget signal (+3 pts) is **always 0**. |

### HIGH
| ID | Boundary | Finding |
|----|----------|---------|
| H1 | Stage 4 → Stage 5 | `rank_overview` sub-fields (`dfs_organic_etv`, `dfs_organic_keywords`, `dfs_paid_keywords`, `dfs_organic_pos_11_20`) are assumed field names from DFSLabsClient. If client normalises to different names, ALL scoring metrics silently zero-out. No runtime error. |
| H2 | Stage 8b → Stage 9 | Stage 9 uses `stage8_verify["dm_linkedin_url"]` (Stage 8a unverified candidate URL) instead of `stage8_contacts["linkedin"]["linkedin_url"]` (Stage 8b L2-verified URL). If Stage 8b rejected the URL as a mismatch, Stage 9 still scrapes the wrong person's posts. |

### MEDIUM
| ID | Boundary | Finding |
|----|----------|---------|
| M1 | Stage 8a → Stage 11 | Stage 8a's compound SERP ABN (suburb+state enriched) is stored at `domain_data["stage8_verify"]["abn"]` but Stage 11 reads ABN from `stage2_verify.get("serp_abn")` only. Higher-quality ABN silently discarded. |
| M2 | Stage 8a → Stage 11 | Stage 8a's company LinkedIn URL (`domain_data["stage8_verify"]["company_linkedin_url"]`) is never surfaced to Stage 11 card. Card always shows Stage 2 value or None. |
| M3 | Stage 8a output | `gmb_rating`, `gmb_reviews`, `gmb_category` in Stage 8a return are always `None` (dead placeholders, verify_fills.py:233-235). Fields imply GMB data is filled here but it is not. |

### LOW
| ID | Boundary | Finding |
|----|----------|---------|
| L1 | Stage 2 → Stage 3 | `serp_facebook_url` written by Stage 2 is not consumed by Stage 3 Gemini. Intentional (Facebook deferred). |
| L2 | Stage 10 → Stage 11 | Stage 10 `f_status` ("success"/"partial"/"failed") is not read by Stage 11. Partial Stage 10 can produce `lead_pool_eligible=True` card with missing VR or outreach without any flag. |
| L3 | Stage 11 | `outreach` in card has no fallback if Stage 10 was skipped (no email found). If Stage 10 gating fires, `outreach=None` with no Stage 7 fallback for outreach. Stage 7 writes `draft_email` / `draft_linkedin_note` / `draft_voice_script` (comprehend_schema_f3b.py) but Stage 11 does not read these as fallback — it only reads `intent_band_final` and `vulnerability_report` from Stage 7. |
| L4 | Stage 8a cost | Stage 8a hardcodes `_cost: 0.006` (verify_fills.py:236) but actual fill_abn_via_serp runs up to 4 SERP queries × $0.002 = up to $0.008. Hardcoded estimate is undercooked when all queries fire. |

---

## Fields Written But Never Read (anywhere in pipeline)

| Field | Written by | Consuming stage | Status |
|-------|-----------|-----------------|--------|
| `serp_facebook_url` (Stage 2) | serp_verify.py:166 | Stage 11 funnel_classifier.py:69 | OK — consumed at Stage 11 |
| `competitors` (Stage 4) | dfs_signal_bundle.py:173 | Stage 7 Gemini context (full bundle passed) | OK — consumed as bulk JSON |
| `keywords` (Stage 4) | dfs_signal_bundle.py:173 | Stage 7 Gemini context | OK |
| `backlinks` (Stage 4) | dfs_signal_bundle.py:176 | Stage 7 Gemini context | OK |
| `brand_serp` (Stage 4) | dfs_signal_bundle.py:177 | Stage 7 Gemini context | OK |
| `ads_competitors` (Stage 4) | dfs_signal_bundle.py:181 | Stage 7 Gemini context | OK |
| `cost_usd` (Stage 4) | dfs_signal_bundle.py:182 | Not consumed downstream | DEAD — not needed; runner tracks cost separately |
| `gmb_rating` (Stage 8a) | verify_fills.py:233 | Not consumed | DEAD PLACEHOLDER |
| `gmb_reviews` (Stage 8a) | verify_fills.py:234 | Not consumed | DEAD PLACEHOLDER |
| `gmb_category` (Stage 8a) | verify_fills.py:235 | Not consumed | DEAD PLACEHOLDER |
| `f_status` (Stage 10) | enhanced_vr.py:213 | Not consumed by Stage 11 | LOW RISK |
| `company_posts_count` (Stage 9) | stage9_social.py:85 | Not consumed by Stage 10 | INFORMATIONAL ONLY |
