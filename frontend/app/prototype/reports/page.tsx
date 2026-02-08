/**
 * Reports Page - Standalone Route
 * Route: /prototype/reports
 * 
 * Performance analytics and insights.
 * Bloomberg dark mode glassmorphic styling.
 */

"use client";

import { ReportsContent } from "../pages/ReportsContent";
import { Sidebar } from "@/components/dashboard";
import { CampaignProvider, useCampaignContext } from "@/contexts";

function ReportsPageContent() {
  const { activeCampaignId } = useCampaignContext();

  return (
    <div className="flex min-h-screen bg-[#05050A]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <ReportsContent campaignId={activeCampaignId} />
      </div>
    </div>
  );
}

export default function ReportsPage() {
  return (
    <CampaignProvider>
      <ReportsPageContent />
    </CampaignProvider>
  );
}
