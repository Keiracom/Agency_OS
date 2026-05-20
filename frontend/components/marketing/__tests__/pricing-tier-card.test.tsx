/**
 * FILE: components/marketing/__tests__/pricing-tier-card.test.tsx
 * PURPOSE: Render tests for PricingTierCard component.
 *
 * SCAFFOLD STATUS: KEI-119
 * Runner: vitest + @testing-library/react (jsdom env, vitest.config.ts).
 * Run locally: cd frontend && npm test -- --run components/marketing/__tests__/pricing-tier-card.test.tsx
 *
 * Coverage focuses:
 *   - Typed props accepted without TS error
 *   - AUD currency display compliance (LAW II)
 *   - TBA placeholder verbatim match
 *   - Feature list rendering
 *   - highlightCta data-testid marker
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PricingTierCard } from "../pricing-tier-card";
import type { PricingTier } from "../pricing-tier-card";

// ── Fixtures ────────────────────────────────────────────────────────────────

const tierWithPrice: PricingTier = {
  name: "Pro",
  priceAud: 299,
  priceLabel: "per month",
  features: ["Feature A", "Feature B", "Feature C"],
  highlightCta: false,
};

const tierTba: PricingTier = {
  name: "Distributor",
  priceAud: null,
  features: ["Feature X", "Feature Y"],
  highlightCta: false,
};

const tierHighlight: PricingTier = {
  name: "Team",
  priceAud: null,
  features: ["Feature P"],
  highlightCta: true,
};

// ── Tests ────────────────────────────────────────────────────────────────────

describe("PricingTierCard", () => {
  it("renders tier name as heading", () => {
    render(<PricingTierCard tier={tierWithPrice} />);
    expect(screen.getByTestId("tier-name").textContent).toBe("Pro");
  });

  it("renders all feature bullets as list items", () => {
    render(<PricingTierCard tier={tierWithPrice} />);
    const list = screen.getByTestId("tier-features");
    const items = list.querySelectorAll("li");
    expect(items).toHaveLength(3);
    expect(items[0].textContent).toBe("Feature A");
    expect(items[1].textContent).toBe("Feature B");
    expect(items[2].textContent).toBe("Feature C");
  });

  it("renders verbatim TBA placeholder when priceAud is null (LAW II)", () => {
    render(<PricingTierCard tier={tierTba} />);
    expect(screen.getByTestId("tier-price").textContent).toBe(
      "$AUD TBA — private beta pricing",
    );
  });

  it("renders AUD price with label when priceAud is a number (LAW II)", () => {
    render(<PricingTierCard tier={tierWithPrice} />);
    // Must include explicit AUD suffix — never bare $N or USD
    expect(screen.getByTestId("tier-price").textContent).toBe(
      "A$299 AUD per month",
    );
  });

  it("adds data-testid='cta-highlight' when highlightCta is true", () => {
    render(<PricingTierCard tier={tierHighlight} />);
    expect(screen.getByTestId("cta-highlight")).toBeTruthy();
  });

  it("does not render cta-highlight when highlightCta is false", () => {
    render(<PricingTierCard tier={tierTba} />);
    expect(screen.queryByTestId("cta-highlight")).toBeNull();
  });

  it("does not render cta-highlight when highlightCta is omitted (default false)", () => {
    const tier: PricingTier = {
      name: "Sandbox",
      priceAud: null,
      features: ["F1"],
      // highlightCta intentionally omitted
    };
    render(<PricingTierCard tier={tier} />);
    expect(screen.queryByTestId("cta-highlight")).toBeNull();
  });
});
