/**
 * FILE: app/(marketing)/about/page.tsx
 * PURPOSE: About page - Server Component wrapper for ISR
 * 
 * ISR Strategy:
 * - Revalidate every hour (3600s) - content rarely changes
 * - Server Component enables proper ISR caching
 * - Client interactivity handled by AboutClient component
 */

import { Metadata } from "next";
import AboutClient from "./AboutClient";

// ISR: Revalidate every hour (content rarely changes)
export const revalidate = 3600;

export const metadata: Metadata = {
  title: "About Agency OS - Built for Australian Agencies",
  description: "Learn about Agency OS - the client acquisition platform built specifically for Australian marketing agencies. Our mission, vision, and values.",
  openGraph: {
    title: "About Agency OS",
    description: "Built by agency people, for agency people. Learn our story.",
  },
};

export default function AboutPage() {
  return <AboutClient />;
}
