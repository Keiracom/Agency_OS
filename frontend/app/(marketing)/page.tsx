/**
 * FILE: app/(marketing)/page.tsx
 * PURPOSE: Keiracom landing page root — hero section + 6 pricing tier cards.
 *
 * SCAFFOLD STATUS: KEI-119
 * Sub-KEI claimers replace stub copy and add visual styling.
 * This file owns: page structure, tier data shape, AUD compliance, ISR config.
 *
 * POSITIONING TAGLINE (verbatim from Linear KEI-119):
 *   "OpenClaw is Linux, Keiracom is RHEL."
 *   Managed AI compute with built-in governance. Global launch day 1.
 *
 * AUD COMPLIANCE (LAW II):
 *   All tier prices use priceAud: null ("$AUD TBA — private beta pricing").
 *   Dollar amounts are NOT shown until Dave ratifies and publishes pricing.
 *   Pattern mirrors costs/page.tsx in Aiden's PR #959 (KEI-114).
 *
 * SOCIAL PROOF: None. (feedback_pre_revenue_reality — pre-revenue, no customers.)
 *
 * ISR: 3600s — matches sibling /pricing page revalidation cadence.
 *
 * FUTURE SUB-KEI HOOKS (see docs/wave3/kei119_marketing_scope.md):
 *   - KEI-119a: Hero copy + brand stylesheet
 *   - KEI-119b–g: Per-tier card copy (one KEI per tier)
 *   - KEI-119h: CTA / waitlist integration
 *   - KEI-119i: Nav + footer for marketing layout
 *   - KEI-119j: SEO metadata + OG images
 */

import type { Metadata } from "next";
import { PricingTierCard } from "@/components/marketing/pricing-tier-card";
import type { PricingTier } from "@/components/marketing/pricing-tier-card";

// ISR: Revalidate hourly — matches /pricing page cadence.
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Keiracom — Managed AI Compute with Built-in Governance",
  description:
    // Pending(KEI-119j): Replace with ratified SEO copy once brand review complete.
    "Keiracom: managed AI compute with built-in governance. OpenClaw is Linux, Keiracom is RHEL.",
};

/**
 * TIER DATA — KEI-119 scaffold
 *
 * Slot order is verbatim from Linear spec:
 *   Sandbox / Solo / Pro / Team / Distributor / Self-Hosted
 *
 * priceAud: null on all tiers — Dave has not published pricing yet.
 * Feature bullets are shape stubs only — sub-KEI claimers replace with copy.
 *
 * Pending(KEI-119b–g): Each tier gets its own sub-KEI for finalised copy + pricing.
 */
const PRICING_TIERS: readonly PricingTier[] = [
  {
    name: "Sandbox",
    priceAud: null,
    // Pending(KEI-119b): Finalise Sandbox tier copy + AUD price
    features: [
      "Concurrent agent threads: stub value",
      "Context window: stub GB",
      "Governance preset: developer sandbox",
      "Rate limits: stub calls/min",
    ],
    highlightCta: false,
  },
  {
    name: "Solo",
    priceAud: null,
    // Pending(KEI-119c): Finalise Solo tier copy + AUD price
    features: [
      "Concurrent agent threads: stub value",
      "Context window: stub GB",
      "Governance preset: solo operator",
      "Support: async",
    ],
    highlightCta: false,
  },
  {
    name: "Pro",
    priceAud: null,
    // Pending(KEI-119d): Finalise Pro tier copy + AUD price
    features: [
      "Concurrent agent threads: stub value",
      "Context window: stub GB",
      "Governance preset: pro operator",
      "Support: priority async",
      "Audit log retention: stub days",
    ],
    highlightCta: true, // Recommended tier — CTA highlighted
  },
  {
    name: "Team",
    priceAud: null,
    // Pending(KEI-119e): Finalise Team tier copy + AUD price
    features: [
      "Concurrent agent threads: stub value",
      "Context window: stub GB",
      "Governance preset: multi-seat team",
      "Role-based access control: stub seats",
      "Support: dedicated channel",
    ],
    highlightCta: false,
  },
  {
    name: "Distributor",
    priceAud: null,
    // Pending(KEI-119f): Finalise Distributor tier copy + AUD price
    features: [
      "White-label configuration: stub value",
      "Sub-account management: stub seats",
      "Governance preset: distributor namespace",
      "Revenue share: stub %",
    ],
    highlightCta: false,
  },
  {
    name: "Self-Hosted",
    priceAud: null,
    // Pending(KEI-119g): Finalise Self-Hosted tier copy + AUD price
    features: [
      "On-premise compute: customer-managed",
      "Air-gap support: stub value",
      "Governance preset: self-hosted sovereign",
      "Enterprise SLA: contact sales",
    ],
    highlightCta: false,
  },
] as const;

/**
 * LandingPage — Server Component
 *
 * Renders the Keiracom marketing landing page.
 * Hero section + pricing tier grid.
 *
 * Visual design (CSS, fonts, spacing) is deferred to KEI-119a and follow-ups.
 * DOM structure is intentionally minimal so a CSS pass needs no DOM changes.
 */
export default function LandingPage(): React.ReactElement {
  return (
    <main>
      {/* ── Hero ──────────────────────────────────────────────────────────
       * SCAFFOLD: Positioning tagline from KEI-119 spec (verbatim).
       * Pending(KEI-119a): Replace stub hero body copy + add brand stylesheet.
       */}
      <section data-testid="hero-section">
        <h1>
          {/* Verbatim tagline — KEI-119 Linear spec */}
          OpenClaw is Linux, Keiracom is RHEL.
        </h1>
        <p>
          {/* Pending(KEI-119a): Replace with ratified hero body copy */}
          Managed AI compute with built-in governance. Global launch day 1.
        </p>
      </section>

      {/* ── Pricing Tiers ─────────────────────────────────────────────────
       * Six tiers: Sandbox / Solo / Pro / Team / Distributor / Self-Hosted.
       * All prices TBA until Dave publishes ratified AUD pricing.
       * Pending(KEI-119b–g): Sub-KEI claimers fill copy per tier.
       */}
      <section data-testid="pricing-section">
        <h2>Pricing</h2>
        {/* Pending(KEI-119a): Add section intro copy */}
        <ul data-testid="pricing-tier-grid">
          {PRICING_TIERS.map((tier) => (
            <li key={tier.name}>
              <PricingTierCard tier={tier} />
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
