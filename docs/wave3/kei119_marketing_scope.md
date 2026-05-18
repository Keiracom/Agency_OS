# KEI-119 Marketing Scope — Sub-KEI Dependency Graph

**Scaffold author:** MAX  
**Linear issue:** KEI-119  
**Branch:** max/kei119-landing-page-scaffold  
**Status:** Scaffold complete. Sub-KEIs below are unblocked once this PR merges.

---

## What this scaffold ships

- `frontend/app/(marketing)/page.tsx` — landing page root (hero + 6 tier cards, all TBA pricing)
- `frontend/components/marketing/pricing-tier-card.tsx` — typed `PricingTierCard` component
- `frontend/components/marketing/__tests__/pricing-tier-card.test.tsx` — render tests
- `docs/wave3/kei119_marketing_scope.md` — this file

---

## Sub-KEI Dependency Graph

```
KEI-119 (scaffold, this PR)
├── KEI-119a  Hero copy + brand stylesheet              [blocks: 119b–g CTA styling]
│             Owner: TBD | Depends on: brand guidelines from Dave
├── KEI-119b  Sandbox tier: copy + AUD price            [unblocked after 119 merges]
│             Owner: TBD | Scope: name, priceAud, priceLabel, 3–5 bullets
├── KEI-119c  Solo tier: copy + AUD price               [unblocked after 119 merges]
├── KEI-119d  Pro tier: copy + AUD price                [unblocked after 119 merges]
│             Note: highlightCta=true already set; CTA styling depends on 119a
├── KEI-119e  Team tier: copy + AUD price               [unblocked after 119 merges]
├── KEI-119f  Distributor tier: copy + AUD price        [unblocked after 119 merges]
├── KEI-119g  Self-Hosted tier: copy + AUD price        [unblocked after 119 merges]
│
├── KEI-119h  CTA / waitlist integration                [depends on: 119a + Dave go-signal]
│             Scope: wire CTA buttons to waitlist flow or signup route
├── KEI-119i  Nav + footer for marketing layout         [depends on: 119a brand stylesheet]
│             Scope: top nav (links to /pricing /about /how-it-works) + footer
└── KEI-119j  SEO metadata + OG images                 [depends on: 119a–g copy finalised]
              Scope: finalise metadata per page + og:image generation
```

### Parallel work (unblocked on merge, no mutual dependency)

KEI-119b through KEI-119g can be claimed and executed in parallel by different sub-KEI agents once Dave ratifies pricing. Each sub-KEI is a single-file edit to `page.tsx` PRICING_TIERS array for that tier's entry.

---

## LAW II AUD Compliance Notes

- All `priceAud` fields currently `null` — placeholder text `"$AUD TBA — private beta pricing"` renders.
- When Dave publishes pricing, each sub-KEI (119b–g) sets the correct `priceAud: <number>` (AUD, NOT USD).
- Never set `priceAud` to a USD value. Conversion rate: 1 USD = 1.55 AUD (LAW II).
- `priceLabel` (e.g. `"per month"`) must be set alongside any non-null `priceAud`.

---

## Social Proof Constraint

Keiracom is pre-revenue (`feedback_pre_revenue_reality`).  
No sub-KEI may add: testimonials, customer counts, partner logos, trust badges, or any fabricated social proof.  
First customer reference requires explicit Dave approval before any copy goes live.

---

## Test Coverage

`pricing-tier-card.test.tsx` covers:
- Tier name heading render
- Feature list render
- TBA placeholder (verbatim AUD string)
- Numeric AUD price + label
- `highlightCta=true` marker
- `highlightCta=false` / omitted (no marker)

Sub-KEI test additions: 119h (CTA click / form submit), 119i (nav link hrefs), 119j (metadata shape).
