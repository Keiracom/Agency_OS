/**
 * FILE: app/(marketing)/how-it-works/page.tsx
 * PURPOSE: How It Works page - Server Component wrapper for ISR
 * 
 * ISR Strategy:
 * - Revalidate every hour (3600s) - content rarely changes
 * - Server Component enables proper ISR caching
 * - Client interactivity handled by HowItWorksClient component
 */

import { Metadata } from "next";
import HowItWorksClient from "./HowItWorksClient";

// ISR: Revalidate every hour (content rarely changes)
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "How It Works - Agency OS | 5 Steps to Booked Meetings",
  description: "From ICP discovery to booked meetings in 5 simple steps. See how Agency OS automates your multi-channel outreach across email, LinkedIn, SMS, voice, and direct mail.",
  openGraph: {
    title: "How Agency OS Works - 5 Steps to Booked Meetings",
    description: "ICP Discovery → Lead Enrichment → ALS Scoring → Multi-Channel Outreach → Meetings Booked",
  },
};

export default function HowItWorksPage() {
  return <HowItWorksClient />;
}
