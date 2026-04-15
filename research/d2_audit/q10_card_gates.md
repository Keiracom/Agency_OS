# Q10 — Stage 11 Card Gate Enforcement
**D2 Audit | 2026-04-15 | review-5 (claude-sonnet-4-6)**

---

## PART (a): Does Stage 11 reject domains with dm_count == 0?

### Gate Logic — assemble_card() with line numbers

Source: `/home/elliotbot/clawd/Agency_OS/src/intelligence/funnel_classifier.py`

```
Line 33:    dm = stage3_identity.get("dm_candidate") or {}
Line 39:    if not dm.get("name"):
Line 40:        missing.append("dm_name")
Line 41:    if not email_data.get("email"):
Line 42:        missing.append("email")
Line 43:    if not stage5_scores:
Line 44:        missing.append("scores")
Line 45:    if not stage7_analyse:
Line 46:        missing.append("vr_report")
Line 48:    lead_pool_eligible = len(missing) == 0
```

The `missing` list is populated when any of four fields are absent. `lead_pool_eligible` is `True` only when `missing` is empty — i.e. ALL four checks pass. One of those checks is `dm_name`.

**However**, Stage 11 (`assemble_card`) is only reached for domains that survived Stage 3. Stage 3 in `cohort_runner.py` drops domains with no DM before Stage 11 is ever called:

```
Line 188:    if not (content.get("dm_candidate") or {}).get("name"):
Line 189:        domain_data["dropped_at"] = "stage3"
Line 190:        domain_data["drop_reason"] = "no_dm_found"
Line 191:        return domain_data
```

Source: `/home/elliotbot/clawd/Agency_OS/src/orchestration/cohort_runner.py` lines 188–191.

**Verdict:** YES. Domains with dm_count == 0 are dropped at Stage 3 (`no_dm_found`) and never reach Stage 11. If somehow a domain with no DM name reached Stage 11, `assemble_card()` would also mark it ineligible via the `dm_name` check on line 39–40.

No code path exists where a card can be emitted with `lead_pool_eligible=True` and no DM name.

---

## PART (b): Does Stage 11 require at least one verified contact path?

### Definition of "verified" in this codebase

**In `contact_waterfall.py`:**
- `dm_verified` on the card is NOT about contact verification. It tracks whether Gemini confirmed the DM identity as the correct local Australian decision-maker (source: `gemini_client.py` lines 165–181, key `_dm_verified`).
- Contact verification is per-channel:
  - Email: `ContactOut` returns `"verified": True` (L1); ZeroBounce returns `"verified": True` (L3). Hunter (L2) returns a confidence score ≥ 70 but does NOT set `verified: True`.
  - LinkedIn: L2 harvestapi profile scraper sets `source: l2_verified_*`. L3 is `"source": "unresolved"`.
  - Mobile: L0 sole-trader inference; L1 ContactOut; remainder unresolved.

**In `funnel_classifier.py` (lines 41–42):**

The ONLY contact field checked for card eligibility is:
```
if not email_data.get("email"):
    missing.append("email")
```

That is: **email presence only**. No check for LinkedIn URL. No check for mobile. No check for `verified: True` flag on the email. No check for `dm_verified`. A card is eligible so long as:
1. DM name present
2. An email string exists (from ANY tier, any confidence)
3. stage5_scores present
4. stage7_analyse present

**Is dm_verified=true required for card emission?** NO. `dm_verified` is written to the card as an informational field only (line 64). It is not part of the `missing` list gate.

**Is there a check for "at least one of: verified email, verified LinkedIn, verified phone"?** NO. Only email presence is checked. LinkedIn URL and phone are not gated.

**What happens if a card ships with dm_verified=False AND no verified email AND no verified LinkedIn?**

The card is still eligible if `email` is present (regardless of verification tier). The `dm_verified=False` flag is cosmetic on the card — no block. The customer receives a card with:
- A DM name that may be wrong (not locally verified)
- An email at whatever confidence tier resolved it (Hunter at score 50–69 would be rejected at L2 due to `conf >= 70` check, but a pattern+ZeroBounce email at L3 would pass as `verified: True`)

The customer can still act on the email and DM name. However if dm_verified=False and the email is a Hunter pattern guess that happened to clear ZeroBounce, the actionability is low.

---

## PART (c): Evidence from actual runs

### D2 Validation Run (20-domain input → 7 cards)

Source: `scripts/output/d2_validation_run/cards.json`

| Domain | dm_count | dm_verified | email | linkedin_url | mobile | lead_pool_eligible | UNREACHABLE |
|--------|----------|-------------|-------|-------------|--------|-------------------|-------------|
| www.theorthodontists.com.au | 1 | True | mithran.goonewardene@... | None | None | True | No |
| www.buildmat.com.au | 1 | **False** | jimmy@buildmat.com.au | None | None | True | No |
| www.puretec.com.au | 1 | True | arne.hornsey@puretecgroup.com | linkedin.com/in/craig-hornsey-34510a76 | None | True | No |
| purewatersystems.com.au | 1 | True | grahaml@purewatersystems.com.au | linkedin.com/in/grahamlewin | None | True | No |
| www.criminaldefencelawyers.com.au | 1 | **False** | js@criminaldefencelawyers.com.au | linkedin.com/in/jimmy-singh-898611a1 | None | True | No |
| www.brydens.com.au | 1 | **False** | leeh@brydens.com.au | linkedin.com/in/bandeli-lee-hagipantelis-b006982a | None | True | No |
| twl.com.au | 1 | **False** | andy@twl.com.au | linkedin.com/in/andylee-twl | None | True | No |

**Counts (D2 validation run):**
- Cards with dm_count == 0: **0**
- Cards with dm_verified == False: **4** (buildmat, criminaldefencelawyers, brydens, twl)
- Cards UNREACHABLE (dm exists, no email, no linkedin, no phone): **0**

### 100-Domain Cohort Run (Apr 15, 10:52 AEST)

Source: `scripts/output/cohort_run_20260415_103508/cards.json` + `summary.json`

Funnel: 100 domains → 42 survived Stage 3 → 40 survived Stage 5 → 28 cards emitted

Drop reasons before Stage 11:
- `enterprise_or_chain`: 35
- `no_dm_found`: 5 (dropped at Stage 3, never reached Stage 11)
- `f3a_failed: unknown`: 18
- `viability: media/publishing`: 1
- `viability: directory/aggregator`: 1

**Counts (100-domain run, 28 cards):**
- Cards with dm_count == 0: **0**
- Cards with dm_verified == False: **5**
- Cards UNREACHABLE (dm exists, no email, no linkedin, no phone): **0**

Domains with dm_verified == False in 100-domain run:

| Domain | dm_name | email (source) | linkedin_url (source) | lead_pool_eligible |
|--------|---------|----------------|----------------------|-------------------|
| www.theorthodontists.com.au | Mithran Goonewardene | mithran.goonewardene@... (hunter) | None (unresolved) | True |
| www.bathroomsalesdirect.com.au | James Salhab | james@bathroomsalesdirect.com.au (hunter) | linkedin.com/in/bathroomsalesdirect (l2_verified_f4_serp) | True |
| jamesonlaw.com.au | Cynthia Bachour-Choucair | cynthia@jamesonlaw.com.au (hunter) | linkedin.com/in/cynthia-choucair (l2_verified_f4_serp) | True |
| www.actlawsociety.asn.au | Simone Carton | simone.carton@actlawsociety.asn.au (hunter) | linkedin.com/in/simonecarton (l2_verified_f4_serp) | True |
| twl.com.au | Andy Lee | andy@twl.com.au (hunter) | linkedin.com/in/andylee-twl (l2_verified_f4_serp) | True |

All 5 unverified-DM cards have at minimum an email via Hunter. All are reachable.

---

## PART (d): Unreachable Card JSON

Definition: DM name present, no email, no LinkedIn URL, no phone.

**D2 validation run: 0 unreachable cards.**

**100-domain run: 0 unreachable cards.**

No unreachable card JSON to paste. Every card in both runs that has a DM name has at minimum a resolved email.

---

## Summary Answer

**Does Stage 11 enforce minimum contact requirements?**

**PARTIALLY YES — with a significant gap.**

What IS enforced:
1. `dm_name` presence (line 39–40 of funnel_classifier.py) — no card emits without a named DM
2. `email` presence (line 41–42) — no card is eligible without at least one email string
3. Upstream Stage 3 gate (cohort_runner.py line 188–190) drops all dm_count==0 domains before Stage 11

What is NOT enforced:
1. `dm_verified=True` is NOT a gate. Cards with unverified DM identity pass freely.
2. Email verification tier is NOT checked. A Hunter email with score 50 would be rejected at L2 (score < 70 threshold in contact_waterfall.py line 277), but an L3 ZeroBounce-confirmed pattern email passes with `verified: True`. There is no minimum tier requirement at the gate.
3. LinkedIn URL is NOT required. Phone is NOT required. Only email presence matters.
4. No combined "at least one VERIFIED contact path" check exists. The gate is purely "email field is non-empty."

**Practical impact in actual runs:** Both runs produced 0 unreachable cards. All emitted cards have an email. The dm_verified=False rate is 57% (4/7) in the 20-domain run and 18% (5/28) in the 100-domain run — these cards are actionable but carry identity risk.

**Gap/Risk:** A card could theoretically emit with:
- dm_verified=False (Gemini could not confirm local AU identity)
- email from Hunter at confidence 70 exactly (marginal quality)
- No LinkedIn, no phone

Such a card is technically eligible and would reach the customer. The customer would be outreaching to an unverified DM name at a marginal email confidence. No system block prevents this.

**Recommendation:** Add a secondary gate:
```python
if not dm_verified and email_tier not in ("L1", "L2") and not linkedin_url:
    missing.append("contact_quality_insufficient")
```
Or at minimum: surface `dm_verified=False` as a dashboard warning flag so customers know which cards carry identity risk.
