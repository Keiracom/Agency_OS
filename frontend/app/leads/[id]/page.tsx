"use client";

/**
 * Lead Detail Page - Sprint 2 Port
 * Ported from: frontend/design/html-prototypes/lead-detail-v2.html
 */

import { AppShell } from "@/components/layout/AppShell";
import { LeadHeader } from "@/components/leads/LeadHeader";
import { LeadRadarChart } from "@/components/leads/LeadRadarChart";
import { LeadTimeline } from "@/components/leads/LeadTimeline";
import { LeadContactInfo } from "@/components/leads/LeadContactInfo";
import { SiegeWaterfallProgress } from "@/components/leads/SiegeWaterfallProgress";
import { mockLeadDetail } from "@/data/mock-lead-detail";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  // In production, fetch lead by params.id
  const lead = mockLeadDetail;

  return (
    <AppShell>
      <div className="min-h-screen bg-bg-void">
        {/* Breadcrumb Header */}
        <div className="bg-bg-surface border-b border-border-subtle px-8 py-4">
          <Link
            href="/leads"
            className="inline-flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Leads
          </Link>
        </div>

        {/* Content */}
        <div className="p-8 max-w-7xl">
          {/* Lead Header */}
          <LeadHeader lead={lead} />

          {/* Grid Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
            {/* Left Column - 2/3 */}
            <div className="lg:col-span-2 space-y-6">
              <LeadRadarChart scores={lead.radarScores} />
              <LeadTimeline events={lead.timeline} />
            </div>

            {/* Right Column - 1/3 */}
            <div className="space-y-6">
              <LeadContactInfo company={lead.company} />
              <SiegeWaterfallProgress tiers={lead.siegeWaterfall} />
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
