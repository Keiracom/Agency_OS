/**
 * FILE: app/(marketing)/pricing/page.tsx
 * PURPOSE: Pricing page - Server Component wrapper for ISR
 * 
 * ISR Strategy:
 * - Revalidate every hour (3600s) - pricing rarely changes
 * - Server Component enables proper ISR caching
 * - Client interactivity handled by PricingClient component
 */

import { Metadata } from "next";
import PricingClient from "./PricingClient";

// ISR: Revalidate every hour (pricing content rarely changes)
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "Pricing - Agency OS | Simple, Transparent AUD Pricing",
  description: "Agency OS pricing plans in AUD. Founding members get 50% off for life. One client covers more than 2 years of Agency OS. No hidden fees.",
  openGraph: {
    title: "Agency OS Pricing - 50% Off Founding Offer",
    description: "Simple pricing. No hidden fees. Lock in 50% off for life.",
  },
};

export default function PricingPage() {
  return <PricingClient />;
}
