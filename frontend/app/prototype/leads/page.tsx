/**
 * Leads Page - Standalone Route
 * Route: /prototype/leads
 * 
 * Bloomberg dark mode leads view with:
 * - "Why Hot?" badges
 * - Tier filter cards
 * - Channel touch icons
 * - Sortable columns
 * - Glassmorphic styling
 */

"use client";

import { LeadsContent } from "../pages/LeadsContent";
import { Sidebar } from "@/components/dashboard";
import { CampaignProvider, useCampaignContext } from "@/contexts";

function LeadsPageContent() {
  const { activeCampaignId } = useCampaignContext();

  return (
    <div className="flex min-h-screen bg-[#05050A]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <LeadsContent campaignId={activeCampaignId} />
      </div>
    </div>
  );
}

export default function LeadsPage() {
  return (
    <CampaignProvider>
      <LeadsPageContent />
    </CampaignProvider>
  );
}
