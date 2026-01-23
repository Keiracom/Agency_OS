"use client";

import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { DashboardShell } from "../layout/DashboardShell";
import { ICPSettingsForm, ICPProfile } from "./ICPSettingsForm";

/**
 * ICPSettings - ICP configuration page
 *
 * Features:
 * - Back button to settings hub
 * - ICPSettingsForm component
 * - Save/Cancel buttons (in form)
 *
 * Design tokens from DESIGN_SYSTEM.md applied throughout
 */
export function ICPSettings() {
  const [isReanalyzing, setIsReanalyzing] = useState(false);

  const handleSave = (values: ICPProfile) => {
    console.log("Saving ICP:", values);
    // In production, this would call the API
  };

  const handleReanalyze = () => {
    setIsReanalyzing(true);
    // Simulate re-analysis
    setTimeout(() => {
      setIsReanalyzing(false);
    }, 3000);
  };

  return (
    <DashboardShell title="ICP Settings" activePath="/settings">
      <div className="max-w-4xl mx-auto">
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
            Ideal Customer Profile
          </h1>
          <p className="text-sm text-[#64748B] mt-1">
            Define who you want to reach. This profile guides all campaign targeting and messaging.
          </p>
        </div>

        {/* ICP Form */}
        <ICPSettingsForm
          onSave={handleSave}
          onReanalyze={handleReanalyze}
          isReanalyzing={isReanalyzing}
        />
      </div>
    </DashboardShell>
  );
}

export default ICPSettings;
