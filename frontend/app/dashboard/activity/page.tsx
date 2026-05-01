/**
 * FILE: frontend/app/dashboard/activity/page.tsx
 * PURPOSE: Canonical activity surface — day-grouped feed with channel
 *          filter chips and expandable event cards. Matches /demo
 *          renderFeed lines 1973-2017.
 * UPDATED: 2026-05-01 — B2.4 consolidation. /dashboard/replies and
 *          /dashboard/inbox now redirect here.
 */

"use client";

import { AppShell } from "@/components/layout/AppShell";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";

export default function ActivityPage() {
  return (
    <AppShell pageTitle="Activity">
      <div>
        <h1 className="font-display font-bold text-[28px] md:text-[36px] text-ink leading-[1.06] tracking-[-0.02em]">
          Activity feed,
          <br />
          <em className="text-amber" style={{ fontStyle: "italic" }}>
            everything Maya is doing.
          </em>
        </h1>
        <p className="text-[13px] text-ink-3 mt-2 max-w-[820px]">
          Reverse-chronological. Tap any event card to expand. Tap the
          prospect name to open the briefing drawer.
        </p>

        <div className="mt-7">
          <ActivityFeed limit={150} />
        </div>
      </div>
    </AppShell>
  );
}
