# D2 Audit — Q3, Q4, Q6 Findings
**Pipeline F v2.1 Validation Run (n=20)**  
**Date:** 2026-04-15  
**Cost:** $2.96 USD / $4.59 AUD | $0.42 per card

---

## Q3 — FULL FUNNEL DROP-OFF

### Funnel Table

| Stage | Entering | Exiting | Dropped | Drop % | Drop Reasons |
|-------|----------|---------|---------|--------|--------------|
| 1 DISCOVER | 20 | 20 | 0 | 0% | — |
| 2 (SERP/ABN) | 20 | 20 | 0 | 0% | — |
| 3 (COMPREHENSION) | 20 | 19 | 1 | 5% | stage3_fail: gstcalc.com.au (no entity_type_hint) |
| 4 (AFFORDABILITY) | 19 | 13 | 6 | 32% | enterprise_or_chain (5) + filtering |
| 5 (VIABILITY/GATE) | 13 | 13 | 0 | 0% | — |
| 6 (ENRICH) | 13 | 12 | 1 | 8% | TBD (stage6 data partial) |
| 7 (DM ANALYSIS) | 12 | 12 | 0 | 0% | — |
| 8 (CONTACTS) | 12 | 12 | 0 | 0% | — |
| 9 (SOCIAL) | 12 | 12 | 0 | 0% | — |
| 10 (VR) | 12 | 12 | 0 | 0% | — |
| 11 (CARD) | 12 | 7 | 5 | 42% | missing_email (5) |

**Total flow:** 20 → 7 cards (35% conversion, net drop of 13)

### Drop Analysis by Stage

**Stage 3 (COMPREHENSION):** 1 domain rejected
- `gstcalc.com.au` — `drop_reason: "no_dm_found"`, `stage3.entity_type_hint: null`

**Stage 4 (AFFORDABILITY):** 6 domains rejected
- 5 marked `enterprise_or_chain: true` in stage3:
  - `www.landers.com.au`
  - `www.gtlaw.com.au`
  - `identityservice.auspost.com.au`
  - `www.etax.com.au`
  - `www.plusfitness.com.au`
- 1 rejected on viability in stage5:
  - `www.localfitness.com.au` — `viability_reason: "directory/aggregator: fitness directory"`, `is_viable_prospect: false`

**Stage 6:** 1 domain filtered (stage6 sparse in results, reason unclear from this run)

**Stage 11 (CARD → Lead Pool):** 5 domains excluded
- All 5 failed `lead_pool_eligible` check due to **missing email**
- Domains: `dentalaspects.com.au`, `glenferriedental.com.au`, `dentistsclinic.com.au`, `www.hillsirrigation.com.au`, `hartsport.com.au`
- Despite passing all upstream gates and scoring 66–76 composite

---

## Q4 — STAGE 5→11 DROPS (5 Domains)

### The 5 Domains that Passed Stage 5 but Dropped at Stage 11

All 5 failed the card assembly gate at Stage 11 due to **email unresolved**:

| Domain | Stage 5 Status | Stage 5 Score | Stage 11 Block | Reason |
|--------|----------------|---------------|----------------|--------|
| dentalaspects.com.au | `passed_gate: true`, `is_viable_prospect: true` | 76 | `lead_pool_eligible: false` | `missing_fields: ["email"]` |
| glenferriedental.com.au | `passed_gate: true`, `is_viable_prospect: true` | 69 | `lead_pool_eligible: false` | `missing_fields: ["email"]` |
| dentistsclinic.com.au | `passed_gate: true`, `is_viable_prospect: true` | 72 | `lead_pool_eligible: false` | `missing_fields: ["email"]` |
| www.hillsirrigation.com.au | `passed_gate: true`, `is_viable_prospect: true` | 66 | `lead_pool_eligible: false` | `missing_fields: ["email"]` |
| hartsport.com.au | `passed_gate: true`, `is_viable_prospect: true` | 69 | `lead_pool_eligible: false` | `missing_fields: ["email"]` |

**All 5 have:**
- `contacts.email.email: null`
- `contacts.email.source: "unresolved"`
- `contacts.email.tier: "L5"`

**Root cause:** Hunter email-finder returned no result; no fallback to Leadmagic or other L3 tier in this run.

---

## Q6 — DM VERIFICATION SEMANTICS

### 7 Final Cards — DM Verification Status

```json
[
  {
    "domain": "www.theorthodontists.com.au",
    "dm_name": "Mithran Goonewardene",
    "dm_verified": true,
    "dm_role": "Principal Orthodontist",
    "composite_score": 65,
    "email": "mithran.goonewardene@theorthodontists.com.au",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": "1300 067 846",
    "linkedin_url": null,
    "missing_fields": []
  },
  {
    "domain": "www.buildmat.com.au",
    "dm_name": "Jimmy Tang",
    "dm_verified": false,
    "dm_role": "Owner",
    "composite_score": 84,
    "email": "jimmy@buildmat.com.au",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": "1300 123 122",
    "linkedin_url": null,
    "missing_fields": []
  },
  {
    "domain": "www.puretec.com.au",
    "dm_name": "Arne Hornsey",
    "dm_verified": true,
    "dm_role": "Chief Executive Officer / Director",
    "composite_score": 69,
    "email": "arne.hornsey@puretecgroup.com",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": "1300 140 140",
    "linkedin_url": null,
    "missing_fields": []
  },
  {
    "domain": "purewatersystems.com.au",
    "dm_name": "Graham Lewin",
    "dm_verified": true,
    "dm_role": "Owner and Director",
    "composite_score": 76,
    "email": "grahaml@purewatersystems.com.au",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": "1300 808 966",
    "linkedin_url": null,
    "missing_fields": []
  },
  {
    "domain": "www.criminaldefencelawyers.com.au",
    "dm_name": "Jimmy Singh",
    "dm_verified": false,
    "dm_role": "Principal Lawyer and Founder",
    "composite_score": 71,
    "email": "js@criminaldefencelawyers.com.au",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": "(02) 8606 2218",
    "linkedin_url": null,
    "missing_fields": []
  },
  {
    "domain": "www.brydens.com.au",
    "dm_name": "Lee Hagipantelis",
    "dm_verified": false,
    "dm_role": "Principal",
    "composite_score": 71,
    "email": "leeh@brydens.com.au",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": "1800 848 848",
    "linkedin_url": null,
    "missing_fields": []
  },
  {
    "domain": "twl.com.au",
    "dm_name": "Andy Lee",
    "dm_verified": false,
    "dm_role": "Co-Founder",
    "composite_score": 71,
    "email": "andy@twl.com.au",
    "email_tier": "L2",
    "email_source": "hunter",
    "email_confidence": 98,
    "phone": null,
    "linkedin_url": null,
    "missing_fields": []
  }
]
```

### Q6.1 — What does dm_verified=true REQUIRE?

From `src/intelligence/gemini_client.py`:

```python
verified = v_content.get("dm_verified")
# ...
if str(verified).lower() == "true":
    # Confirmed — keep original Stage 3 IDENTIFY result
    stage3_result["content"]["_dm_verified"] = True
    stage3_result["content"]["_dm_verification_note"] = v_content.get("verification_note", "")
```

**dm_verified=true REQUIRES:**
1. A verification step (upstream DM verification call) successfully returns
2. The verification result explicitly sets `dm_verified: "true"` (string, case-insensitive)
3. The Stage 3 IDENTIFY dm_candidate is either:
   - **Confirmed unchanged** — DM name matches the verification source exactly, OR
   - **Corrected** — DM name was updated based on verification (sets `_dm_corrected_from` flag)
4. A verification_note is populated to justify the confirmation/correction

**dm_verified=false REQUIRES:**
- Verification step was skipped, failed, or returned a non-true result
- Original Stage 3 dm_candidate stands unverified

In the D2 run:
- **3 cards have dm_verified=true:** Mithran Goonewardene, Arne Hornsey, Graham Lewin
- **4 cards have dm_verified=false:** Jimmy Tang, Jimmy Singh, Lee Hagipantelis, Andy Lee

### Q6.2 — buildmat.com.au (Score 84, dm_verified=false, Email Resolved)

**Full verification status:**
```json
{
  "domain": "www.buildmat.com.au",
  "dm_verified": false,
  "composite_score": 84,
  "missing_fields": [],
  "lead_pool_eligible": true,
  "email_actual": "jimmy@buildmat.com.au",
  "email_source": "hunter",
  "email_tier": "L2",
  "email_confidence": 98,
  "phone": "1300 123 122",
  "linkedin_url": null
}
```

**Status summary:**
- **Missing fields:** None (email resolved via Hunter, confidence 98%)
- **Lead pool eligible:** YES (`lead_pool_eligible: true`)
- **DM verification:** False (DM name "Jimmy Tang" not verified by upstream step)
- **Shipping status:** **CARD SHIPPED** — all missing_fields blocks are cleared
  - Email is present and sourced from L2 (Hunter)
  - Composite score is 84 (highest in cohort)
  - Despite dm_verified=false, the card assembly gate checks `lead_pool_eligible`, not `dm_verified`

**Would this card ship to a paying customer in current logic?**

**YES.** Current card assembly in `funnel_classifier.py` checks:
```python
missing = []
if not dm.get("name"):
    missing.append("dm_name")
if not email_data.get("email"):
    missing.append("email")
# ...
lead_pool_eligible = len(missing) == 0
```

`lead_pool_eligible=true` is the gate, not `dm_verified`. buildmat.com.au has both dm_name and email, so it ships as a lead pool card despite dm_verified=false.

**Risk:** The card has an **unverified DM name** with a **high-confidence email from Hunter**. If Jimmy Tang is not the correct decision-maker for outreach, the Hunter email address may not reach the intended contact. A paying customer's BDR would risk email waste and low response.

**Recommendation:** Consider adding a secondary gate that flags `dm_verified=false` cards as "requires verification before outreach" in the dashboard, or surface it as a data quality warning in the card UI.

---

## Summary

- **Q3 Funnel:** 20 → 7 cards (35%), 5-stage drop pattern: enterprise filter (stage 4) + email resolution (stage 11)
- **Q4 Drops:** All 5 Stage 5→11 drops due to email unresolved; no secondary enrichment fallback triggered
- **Q6 DM Verification:** dm_verified=true for 3/7; dm_verified=false does NOT block card shipping (lead_pool_eligible is the actual gate). buildmat.com.au ships despite dm_verified=false, scoring 84/100.

