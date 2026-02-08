/**
 * Campaigns Page - Standalone Route
 * Route: /prototype/campaigns
 * 
 * Campaign management with AI suggestions.
 * Bloomberg dark mode glassmorphic styling.
 */

"use client";

import { useState } from "react";
import { CampaignsContent } from "../pages/CampaignsContent";
import { Sidebar, NewCampaignModal } from "@/components/dashboard";
import { CampaignProvider, useCampaignContext } from "@/contexts";

function CampaignsPageContent() {
  const [showNewCampaignModal, setShowNewCampaignModal] = useState(false);
  const { activeCampaignId } = useCampaignContext();

  return (
    <div className="flex min-h-screen bg-[#05050A]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <CampaignsContent 
          campaignId={activeCampaignId} 
          onNewCampaign={() => setShowNewCampaignModal(true)} 
        />
      </div>
      
      <NewCampaignModal
        isOpen={showNewCampaignModal}
        onClose={() => setShowNewCampaignModal(false)}
        onSubmit={() => setShowNewCampaignModal(false)}
      />
    </div>
  );
}

export default function CampaignsPage() {
  return (
    <CampaignProvider>
      <CampaignsPageContent />
    </CampaignProvider>
  );
}
