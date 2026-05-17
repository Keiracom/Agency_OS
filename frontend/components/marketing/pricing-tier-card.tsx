/**
 * FILE: components/marketing/pricing-tier-card.tsx
 * PURPOSE: Typed component for a single Keiracom pricing tier card.
 *
 * SCAFFOLD STATUS: KEI-119
 * Sub-KEI claimers replace stub copy; this file owns shape + rendering logic only.
 *
 * AUD COMPLIANCE (LAW II): All prices rendered with explicit "AUD" suffix.
 * When priceAud is null the verbatim placeholder "$AUD TBA — private beta pricing"
 * is shown. Never renders bare "$N" or USD values.
 *
 * SOCIAL PROOF: None. No testimonials, customer counts, or partner logos.
 * (feedback_pre_revenue_reality — Keiracom is pre-revenue.)
 *
 * USAGE:
 *   import { PricingTierCard } from "@/components/marketing/pricing-tier-card";
 *   <PricingTierCard tier={tier} />
 *
 * FUTURE SUB-KEI HOOKS:
 *   - Replace feature bullet stubs with finalised copy per tier
 *   - Add CTA link href once signup flow exists
 *   - Wire highlightCta to a real CTA button variant
 *   - Add annual/monthly toggle price variants
 */

/**
 * Shape for a single pricing tier.
 *
 * @property name        - Display name shown as card heading.
 * @property priceAud    - Monthly price in AUD cents. null = TBA (private beta).
 * @property priceLabel  - Billing cadence label, e.g. "per month". Omit when priceAud is null.
 * @property features    - 3–5 capability bullets. Stub text accepted at scaffold stage.
 * @property highlightCta - If true, renders a data-testid="cta-highlight" marker for the CTA.
 */
export interface PricingTier {
  readonly name: string;
  readonly priceAud: number | null; // null → "$AUD TBA — private beta pricing"
  readonly priceLabel?: string; // "per month" etc — omit when priceAud is null
  readonly features: readonly string[];
  readonly highlightCta?: boolean; // default false
}

/**
 * PricingTierCard
 *
 * Renders a single tier card. Intentionally unstyled beyond basic structure —
 * visual design is deferred to a sub-KEI. Layout uses semantic HTML so a future
 * CSS pass does not require DOM changes.
 *
 * @param tier - The tier data object conforming to PricingTier interface.
 */
export function PricingTierCard({
  tier,
}: Readonly<{ tier: PricingTier }>): React.ReactElement {
  let priceDisplay: string;
  if (tier.priceAud === null) {
    priceDisplay = "$AUD TBA — private beta pricing";
  } else {
    const value = `A$${tier.priceAud} AUD`;
    priceDisplay = tier.priceLabel ? `${value} ${tier.priceLabel}` : value;
  }

  return (
    <article
      data-testid="pricing-tier-card"
      data-tier={tier.name.toLowerCase()}
    >
      {/* Tier name — sub-KEI: replace with styled heading */}
      <h3 data-testid="tier-name">{tier.name}</h3>

      {/* Price display — AUD-compliant per LAW II */}
      <p data-testid="tier-price">{priceDisplay}</p>

      {/* Feature bullets — sub-KEI: replace stub text with finalised copy */}
      <ul data-testid="tier-features">
        {tier.features.map((feature) => (
          <li key={feature}>{feature}</li>
        ))}
      </ul>

      {/* CTA — sub-KEI: wire href + button variant */}
      {tier.highlightCta === true ? (
        <div data-testid="cta-highlight">
          {/* Pending(sub-KEI): Replace with real CTA button + route */}
          <button type="button">Get started</button>
        </div>
      ) : (
        <div>
          {/* Pending(sub-KEI): Replace with real CTA button + route */}
          <button type="button">Learn more</button>
        </div>
      )}
    </article>
  );
}
