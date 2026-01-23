"use client";

import { ArrowLeft } from "lucide-react";
import { DashboardShell } from "../layout/DashboardShell";
import { NotificationSettingsForm, NotificationPreferences } from "./NotificationSettingsForm";

/**
 * NotificationSettings - Notification settings page
 *
 * Features:
 * - Back button to settings hub
 * - NotificationSettingsForm component
 * - Save button (in form)
 *
 * Design tokens from DESIGN_SYSTEM.md applied throughout
 */
export function NotificationSettings() {
  const handleSave = (values: NotificationPreferences) => {
    console.log("Saving notifications:", values);
    // In production, this would call the API
  };

  return (
    <DashboardShell title="Notification Settings" activePath="/settings">
      <div className="max-w-2xl mx-auto">
        {/* Back Button */}
        <button
          type="button"
          className="flex items-center gap-2 text-sm text-[#64748B] hover:text-[#1E293B] mb-6 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Settings
        </button>

        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-[#1E293B]">
            Notification Settings
          </h1>
          <p className="text-sm text-[#64748B] mt-1">
            Configure how you receive updates from Agency OS
          </p>
        </div>

        {/* Notification Form */}
        <NotificationSettingsForm onSave={handleSave} />
      </div>
    </DashboardShell>
  );
}

export default NotificationSettings;
