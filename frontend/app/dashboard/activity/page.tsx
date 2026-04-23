"use client";

/**
 * FILE: frontend/app/dashboard/activity/page.tsx
 * PURPOSE: Full-page activity timeline route
 * PHASE: PHASE-2.1-PROSPECT-DRAWER-FEED
 */

import Link from "next/link";
import { AppShell } from "@/components/layout/AppShell";
import { ActivityFeedFull } from "@/components/dashboard/ActivityFeedFull";

export default function ActivityPage() {
  return (
    <AppShell pageTitle="Activity">
      <div className="min-h-screen bg-gray-950 text-gray-100 p-4 md:p-6">
        <header className="mb-4">
          <h1 className="font-serif text-2xl md:text-3xl text-gray-100">Activity</h1>
          <p className="text-sm text-gray-400">
            Live outreach events. Click any row to open the prospect drawer.
          </p>
        </header>

        <ActivityFeedFull limit={150} />

        <nav className="mt-6 text-xs text-gray-500 font-mono flex gap-3">
          <Link href="/dashboard" className="hover:text-gray-300">← Home</Link>
          <Link href="/dashboard/pipeline" className="hover:text-gray-300">Pipeline →</Link>
          <Link href="/dashboard/meetings" className="hover:text-gray-300">Meetings →</Link>
        </nav>
      </div>
    </AppShell>
  );
}
