/**
 * Replies Page - Standalone Route
 * Route: /prototype/replies
 * 
 * Reply inbox with intent classification.
 * Bloomberg dark mode glassmorphic styling.
 */

"use client";

import { RepliesContent } from "../pages/RepliesContent";
import { Sidebar } from "@/components/dashboard";
import { CampaignProvider, useCampaignContext } from "@/contexts";

function RepliesPageContent() {
  const { activeCampaignId } = useCampaignContext();

  return (
    <div className="flex min-h-screen bg-[#05050A]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <RepliesContent campaignId={activeCampaignId} />
      </div>
    </div>
  );
}

export default function RepliesPage() {
  return (
    <CampaignProvider>
      <RepliesPageContent />
    </CampaignProvider>
  );
}
