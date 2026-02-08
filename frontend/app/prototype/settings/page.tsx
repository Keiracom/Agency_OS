/**
 * Settings Page - Standalone Route
 * Route: /prototype/settings
 * 
 * Account and targeting configuration.
 * Bloomberg dark mode glassmorphic styling.
 */

"use client";

import { SettingsContent } from "../pages/SettingsContent";
import { Sidebar } from "@/components/dashboard";
import { CampaignProvider } from "@/contexts";

function SettingsPageContent() {
  return (
    <div className="flex min-h-screen bg-[#05050A]">
      <Sidebar />
      <div className="flex-1 ml-60">
        <SettingsContent />
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <CampaignProvider>
      <SettingsPageContent />
    </CampaignProvider>
  );
}
