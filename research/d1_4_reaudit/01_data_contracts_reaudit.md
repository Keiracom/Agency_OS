# D1.4 Re-Audit: Data Contracts
Branch: directive-d1-3-audit-fixes
Date: 2026-04-14
Auditor: build-2 (read-only, zero code changes)

---

## C1 — ABN budget signal zeroed

### (a) Original D1.2 evidence
Stage 5 called `score_prospect(f3a_output=domain_data.get("stage3", {}))`. Stage 3 (Gemini comprehension) never emits an `abn` key — that is a Stage 2 SERP field. So `f3a_output.get("abn")` and `f3a_output.get("serp_abn")` were both `None`, zeroing the `abn_registered` budget signal (worth 3 points).

### (b) Current state — verbatim
```
cohort_runner.py:203:        # FIX C1: inject Stage 2 ABN into stage3 bundle so scorer sees it
cohort_runner.py:204:        stage3_with_abn = dict(domain_data.get("stage3", {}))
cohort_runner.py:205:        stage3_with_abn["serp_abn"] = domain_data.get("stage2", {}).get("serp_abn")
cohort_runner.py:206:        scores = score_prospect(
cohort_runner.py:207:            signal_bundle=domain_data.get("stage4", {}),
cohort_runner.py:208:            f3a_output=stage3_with_abn,
```

prospect_scorer.py:107:    serp_abn = f3a_output.get("abn") or f3a_output.get("serp_abn")
prospect_scorer.py:109:    if serp_abn:
prospect_scorer.py:111:        breakdown["abn_registered"] = 3

### (c) Status: RESOLVED

`stage3_with_abn` is a shallow copy (`dict(...)`) — it does NOT mutate `domain_data["stage3"]`. Downstream stages (7, 8, 9, 10) that read `domain_data.get("stage3")` remain unaffected. The scorer reads `f3a_output.get("serp_abn")` which now resolves from Stage 2.

---

## H1 — rank_overview field names

### (a) Original D1.2 evidence
Stage 5 scorer was reading `dfs_organic_etv` etc from `rank_overview`, but the key names produced by `domain_rank_overview()` were in question.

### (b) Current state — verbatim
```
dfs_labs_client.py:469:            "dfs_organic_etv": organic.get("etv"),
dfs_labs_client.py:470:            "dfs_paid_etv": paid.get("etv"),
dfs_labs_client.py:471:            "dfs_organic_keywords": organic.get("count"),
dfs_labs_client.py:472:            "dfs_paid_keywords": paid.get("count"),

prospect_scorer.py:83:    ro = signal_bundle.get("rank_overview") or {}
prospect_scorer.py:88:    organic_etv = ro.get("dfs_organic_etv") or 0

funnel_classifier.py:102:        "organic_etv": ro.get("dfs_organic_etv"),
funnel_classifier.py:103:        "organic_keywords": ro.get("dfs_organic_keywords"),
```

### (c) Status: RESOLVED

Client emits `dfs_organic_etv`, scorer reads `dfs_organic_etv`. Full chain confirmed: client -> signal_bundle["rank_overview"] -> scorer -> card._extract_signal_summary. No regression.

---

## H2 — Stage 9 unverified LinkedIn URL

### (a) Original D1.2 evidence
Stage 9 was using `fills.get("dm_linkedin_url")` (an unverified SERP-sourced URL from stage8a) rather than the waterfall-verified URL from `stage8_contacts.linkedin.linkedin_url`.

### (b) Current state — verbatim
```
cohort_runner.py:308:    # FIX H2: use verified URL from stage8_contacts (waterfall result), not fills (unverified SERP)
cohort_runner.py:309:    contacts = domain_data.get("stage8_contacts") or {}
cohort_runner.py:310:    li_data = contacts.get("linkedin", {})
cohort_runner.py:311:    dm_li = li_data.get("linkedin_url") if li_data.get("match_type") != "no_match" else None
cohort_runner.py:312:    company_li = fills.get("company_linkedin_url") or (
cohort_runner.py:313:        (domain_data.get("stage2") or {}).get("serp_company_linkedin")
cohort_runner.py:314:    )
```

contact_waterfall.py confirms the linkedin dict contains keys `linkedin_url` and `match_type`.

### (c) Status: RESOLVED

`dm_li` is sourced from `stage8_contacts.linkedin.linkedin_url` and is set to `None` when `match_type == "no_match"`. Key names match the actual `contact_waterfall` output structure (verified at contact_waterfall.py lines 144, 198, 223).

---

## M1 — Stage 8a ABN not in card

### (a) Original D1.2 evidence
`verify_fills` (stage8a) returned `{"abn": ..., "company_linkedin_url": ...}` but `assemble_card` only read from `stage2_verify` (i.e., `domain_data["stage2"]`). The stage8a ABN was never surfaced into the card.

### (b) Current state — verbatim
```
cohort_runner.py:364:        # FIX M1+M2: merge stage8_verify ABN and LinkedIn into stage2 so card sees them
cohort_runner.py:365:        stage2_merged = dict(domain_data.get("stage2") or {})
cohort_runner.py:366:        verify = domain_data.get("stage8_verify") or {}
cohort_runner.py:367:        if verify.get("abn"):
cohort_runner.py:368:            stage2_merged["serp_abn"] = verify["abn"]
cohort_runner.py:373:            stage2_verify=stage2_merged,

funnel_classifier.py:66:        "abn": stage2_verify.get("serp_abn"),
```

verify_fills.py:231:        "abn": abn,   (key is "abn" in stage8_verify)
cohort_runner.py:367-368: verify.get("abn") -> stage2_merged["serp_abn"]  (remapped correctly)

### (c) Status: RESOLVED

The key rename from `"abn"` (stage8_verify) to `"serp_abn"` (stage2_merged) is intentional and correct — `assemble_card` reads `stage2_verify.get("serp_abn")`. `stage2_merged` is a local copy; `domain_data["stage2"]` is never mutated (only written at lines 137 and 141, both in `_run_stage2`).

---

## M2 — Stage 8a company LinkedIn not in card

### (a) Original D1.2 evidence
Same as M1 — `verify_fills` `company_linkedin_url` was not reaching the card.

### (b) Current state — verbatim
```
cohort_runner.py:369:        if verify.get("company_linkedin_url"):
cohort_runner.py:370:            stage2_merged["serp_company_linkedin"] = verify["company_linkedin_url"]

funnel_classifier.py:67:        "company_linkedin_url": stage2_verify.get("serp_company_linkedin"),
```

### (c) Status: RESOLVED

Key remapped `company_linkedin_url` -> `serp_company_linkedin` correctly matches the card reader.

---

## M3 — verify_fills always-None GMB fields

### (a) Original D1.2 evidence
`verify_fills` returned `gmb_rating`, `gmb_reviews`, `gmb_category` as always-`None` (never populated), creating dead weight in every card.

### (b) Current state — verbatim
```
verify_fills.py:229:    # FIX M3: gmb_rating/gmb_reviews/gmb_category removed — always None, deferred by design
verify_fills.py:230:    return {
verify_fills.py:231:        "abn": abn,
verify_fills.py:232:        "abn_status": "verified_serp" if abn else "unresolved",
verify_fills.py:233:        "abn_source": "dfs_serp_abr" if abn else "unresolved",
verify_fills.py:234:        "dm_linkedin_url": dm_linkedin,
verify_fills.py:235:        "company_linkedin_url": company_linkedin,
verify_fills.py:236:        "_cost": 0.008,
verify_fills.py:237:    }
```

No `gmb_rating`, `gmb_reviews`, or `gmb_category` keys present anywhere in verify_fills.py source.

### (c) Status: RESOLVED

---

## L1 — serp_facebook_url skipped (by design)

### (a) Original D1.2 evidence
`verify_fills` did not populate `serp_facebook_url`. Card reads `stage2_verify.get("serp_facebook_url")` which resolves from the original Stage 2 SERP output (not stage8a).

### (b) Current state — verbatim
```
funnel_classifier.py:68:        "facebook_url": stage2_verify.get("serp_facebook_url"),
```

`stage2_merged` inherits all keys from `domain_data["stage2"]`, so `serp_facebook_url` still flows through Stage 2 if the SERP found it. No change required.

### (c) Status: RESOLVED (confirmed no-action, by design)

---

## L2 — Stage 10 f_status not in card

### (a) Original D1.2 evidence
`assemble_card` did not surface `f_status` from Stage 10 output. The field was computed but discarded.

### (b) Current state — verbatim
```
funnel_classifier.py:78:        # FIX L2: surface f_status from Stage 10
funnel_classifier.py:79:        "stage10_status": (stage10_vr_msg or {}).get("f_status"),
```

### (c) Status: RESOLVED

---

## L3 — Stage 7 outreach fallback

### (a) Original D1.2 evidence
If Stage 10 did not run (no email found), the card outreach field was empty — Stage 7 draft outreach was available but not used as fallback.

### (b) Current state — verbatim
```
funnel_classifier.py:80:        # FIX L3: fall back to Stage 7 draft outreach if Stage 10 outreach absent
funnel_classifier.py:81:        "outreach": (stage10_vr_msg or {}).get("outreach") or {
funnel_classifier.py:82:            "draft_email": stage7_analyse.get("draft_email"),
funnel_classifier.py:83:            "draft_linkedin_note": stage7_analyse.get("draft_linkedin_note"),
funnel_classifier.py:84:            "draft_voice_script": stage7_analyse.get("draft_voice_script"),
funnel_classifier.py:85:        },
```

### (c) Status: RESOLVED

---

## L4 — verify_fills _cost 0.006 -> 0.008

### (a) Original D1.2 evidence
`verify_fills` `_cost` was set to `0.006` but up to 4 SERP call variants are now possible (ABN + DM LinkedIn + Company LinkedIn + fallback), making the correct cost `0.008` ($0.002 x 4).

### (b) Current state — verbatim
```
verify_fills.py:228:    # FIX L4: _cost updated to 0.008 (4 SERP call variants now possible)
verify_fills.py:236:        "_cost": 0.008,
```

### (c) Status: RESOLVED

---

## Fresh Boundary Scan — New Mismatches Introduced by Fixes

### 1. stage3_with_abn — isolation risk

`stage3_with_abn = dict(domain_data.get("stage3", {}))` is a **shallow copy**. The `serp_abn` key added is a string (not mutable), so downstream stages (7, 8, 9, 10, 11) that read `domain_data.get("stage3")` remain unchanged. No mutation risk. SAFE.

### 2. stage2_merged — isolation risk

`stage2_merged = dict(domain_data.get("stage2") or {})` is a local variable in `_run_stage11`. It is passed as `stage2_verify=stage2_merged` to `assemble_card` but **never written back** to `domain_data["stage2"]`. The only writes to `domain_data["stage2"]` are at cohort_runner.py lines 137 and 141, both in `_run_stage2`. SAFE.

### 3. assemble_card parameter mismatch risk

`_run_stage11` calls `assemble_card(stage2_verify=stage2_merged, ...)`. `assemble_card` signature requires `stage2_verify: dict` at position 2. The merged dict contains all original Stage 2 keys plus optional overrides for `serp_abn` and `serp_company_linkedin`. Readers in `assemble_card` are:
- `stage2_verify.get("serp_abn")` — present in merged dict (either from Stage 2 or from stage8_verify override)
- `stage2_verify.get("serp_company_linkedin")` — same
- `stage2_verify.get("serp_facebook_url")` — inherited unchanged from Stage 2

No mismatch. SAFE.

### 4. New silent .get() defaults

Scan of new fix code shows:
- `verify.get("abn")` — guarded by `if verify.get("abn"):`, no silent default
- `verify.get("company_linkedin_url")` — guarded by `if verify.get("company_linkedin_url"):`, no silent default
- `li_data.get("match_type") != "no_match"` — if `match_type` is absent (shouldn't be per contract), this evaluates as `None != "no_match"` = `True`, meaning `dm_li` would be set to `li_data.get("linkedin_url")` which may be `None`. This is a low-risk edge case: result is `dm_li = None`, same as `no_match` path. ACCEPTABLE.

### 5. Stage 8 cost accounting double-count risk

`_run_stage8` hard-codes `cost_usd += 0.023` regardless of how many SERP calls `verify_fills` actually made. `verify_fills` returns `_cost: 0.008` but this returned cost is **not consumed** by `_run_stage8` — it adds 0.023 flat. This was pre-existing behaviour, not introduced by the D1.3 fixes. Not a new mismatch. Flagged for awareness only.

### 6. stage10_status field name consistency

`assemble_card` surfaces Stage 10 `f_status` as `"stage10_status"`. Nothing in the card schema reads this back internally. Downstream consumers (Supabase insert, Salesforge push) will need to be aware of the new field name. Not a mismatch within the pipeline itself, but a contract change at the card boundary.

---

## Summary Table

| Finding | Status |
|---------|--------|
| C1 — ABN budget signal zeroed | RESOLVED |
| H1 — rank_overview field names | RESOLVED |
| H2 — Stage 9 unverified LinkedIn URL | RESOLVED |
| M1 — Stage 8a ABN not in card | RESOLVED |
| M2 — Stage 8a company LinkedIn not in card | RESOLVED |
| M3 — verify_fills always-None GMB fields | RESOLVED |
| L1 — serp_facebook_url skipped | RESOLVED (by design) |
| L2 — Stage 10 f_status not in card | RESOLVED |
| L3 — Stage 7 outreach fallback | RESOLVED |
| L4 — verify_fills _cost 0.006 -> 0.008 | RESOLVED |

**All 10 D1.2 findings: RESOLVED.**

New issues surfaced by fresh scan: 0 blockers. 2 awareness items (cost double-count pre-existing; stage10_status new card field for downstream consumers).
