/**
 * FILE: frontend/app/dashboard/page.tsx
 * PURPOSE: Home — single linear sequence matching /demo renderHome
 *          (lines 1643-1722). BDR hero → 4-card sum-row → today's
 *          meetings strip → Maya strip → cycle funnel → attention.
 * UPDATED: 2026-05-01 — B2.4 visual parity rewrite (replaces v10 +
 *          ROW1-4 stack with the prototype's linear sequence).
 */

"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { HeroStrip } from "@/components/dashboard/HeroStrip";
import { TodayStrip } from "@/components/dashboard/TodayStrip";
import { MayaStrip } from "@/components/dashboard/MayaStrip";
import { FunnelBar } from "@/components/dashboard/FunnelBar";
import { AttentionCards } from "@/components/dashboard/AttentionCards";
import { ProspectDrawer } from "@/components/dashboard/ProspectDrawer";
import { SectionLabel } from "@/components/dashboard/SectionLabel";

export default function DashboardPage() {
  const [drawerLeadId, setDrawerLeadId] = useState<string | null>(null);

  return (
    <AppShell>
      <div className="space-y-7">
        <HeroStrip />
        <TodayStrip />
        <MayaStrip />

        <div>
          <SectionLabel className="mt-0 mb-3">Cycle funnel</SectionLabel>
          <FunnelBar />
        </div>

        <div>
          <SectionLabel className="mt-0 mb-3">Needs your attention</SectionLabel>
          <AttentionCards onLeadClick={(id) => setDrawerLeadId(id)} />
        </div>
      </div>
      <ProspectDrawer leadId={drawerLeadId} onClose={() => setDrawerLeadId(null)} />
    </AppShell>
  );
}
