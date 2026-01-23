"use client";

import { useState, useCallback } from "react";
import { Plus, Sparkles, MoreVertical, AlertCircle, CheckCircle2 } from "lucide-react";
import { PrioritySlider } from "./PrioritySlider";

/**
 * Campaign data with priority information
 */
export interface CampaignWithPriority {
  id: string;
  name: string;
  status: "active" | "paused" | "draft";
  priority_pct: number;
  is_ai_suggested: boolean;
  meetings_this_month: number;
  reply_rate: number;
  show_rate: number;
}

/**
 * CampaignAllocationManager props
 */
export interface CampaignAllocationManagerProps {
  /** List of campaigns with their priorities */
  campaigns: CampaignWithPriority[];
  /** Maximum number of campaigns allowed (from tier) */
  maxCampaigns?: number;
  /** Callback when priorities are confirmed */
  onConfirm?: (allocations: Array<{ campaign_id: string; priority_pct: number }>) => void;
  /** Whether confirm action is in progress */
  isConfirming?: boolean;
}

/**
 * CampaignAllocationManager - Container managing all campaign priority sliders
 *
 * Features:
 * - Header with slot count and Add button
 * - List of campaign cards with priority sliders
 * - Total percentage tracking (must sum to 100%)
 * - Auto-balance when adjusting sliders
 * - Pending changes state with Cancel/Confirm buttons
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Card background: #FFFFFF
 * - Card border: #E2E8F0
 * - Pending border: #EAB308 (yellow-500)
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 */
export function CampaignAllocationManager({
  campaigns,
  maxCampaigns = 3,
  onConfirm,
  isConfirming = false,
}: CampaignAllocationManagerProps) {
  // Track original and current priorities
  const [priorities, setPriorities] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    campaigns.forEach((c) => {
      initial[c.id] = c.priority_pct;
    });
    return initial;
  });

  const [originalPriorities] = useState<Record<string, number>>(() => {
    const initial: Record<string, number> = {};
    campaigns.forEach((c) => {
      initial[c.id] = c.priority_pct;
    });
    return initial;
  });

  // Check if there are pending changes
  const hasPendingChanges = Object.keys(priorities).some(
    (id) => priorities[id] !== originalPriorities[id]
  );

  // Calculate total percentage
  const totalPercentage = Object.values(priorities).reduce((sum, v) => sum + v, 0);

  // Auto-balance algorithm
  const autoBalance = useCallback(
    (changedId: string, newValue: number) => {
      const min = 10;
      const max = 80;

      // Clamp the new value
      const clampedValue = Math.max(min, Math.min(max, newValue));

      // Get the delta
      const oldValue = priorities[changedId];
      const delta = clampedValue - oldValue;

      // Get other campaign IDs
      const otherIds = Object.keys(priorities).filter((id) => id !== changedId);

      if (otherIds.length === 0) {
        setPriorities({ [changedId]: 100 });
        return;
      }

      // Calculate how much to distribute
      const otherTotal = otherIds.reduce((sum, id) => sum + priorities[id], 0);

      const newPriorities: Record<string, number> = { [changedId]: clampedValue };

      // Distribute proportionally
      for (const id of otherIds) {
        const proportion = priorities[id] / otherTotal;
        const adjustment = Math.round(delta * proportion);
        const adjusted = Math.max(min, Math.min(max, priorities[id] - adjustment));
        newPriorities[id] = adjusted;
      }

      // Normalize to 100%
      const total = Object.values(newPriorities).reduce((sum, v) => sum + v, 0);
      if (total !== 100) {
        const diff = 100 - total;
        // Add the difference to the largest value that can accommodate it
        const sortedIds = Object.keys(newPriorities).sort(
          (a, b) => newPriorities[b] - newPriorities[a]
        );
        for (const id of sortedIds) {
          const newVal = newPriorities[id] + diff;
          if (newVal >= min && newVal <= max) {
            newPriorities[id] = newVal;
            break;
          }
        }
      }

      setPriorities(newPriorities);
    },
    [priorities]
  );

  const handleCancel = () => {
    setPriorities({ ...originalPriorities });
  };

  const handleConfirm = () => {
    if (onConfirm) {
      const allocations = Object.entries(priorities).map(([campaign_id, priority_pct]) => ({
        campaign_id,
        priority_pct,
      }));
      onConfirm(allocations);
    }
  };

  // Status badge component
  const StatusBadge = ({ status }: { status: "active" | "paused" | "draft" }) => {
    const styles = {
      active: "bg-[#DCFCE7] text-[#166534]",
      paused: "bg-[#FEF3C7] text-[#92400E]",
      draft: "bg-[#F1F5F9] text-[#64748B]",
    };

    const labels = {
      active: "Active",
      paused: "Paused",
      draft: "Draft",
    };

    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status]}`}>
        {labels[status]}
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
            Your Campaigns
          </h2>
          <p className="text-sm text-[#94A3B8] mt-1">
            {campaigns.length} of {maxCampaigns} slots used
          </p>
        </div>
        {campaigns.length < maxCampaigns && (
          <button className="flex items-center gap-2 px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25">
            <Plus className="h-4 w-4" />
            Add Campaign
          </button>
        )}
      </div>

      {/* Campaign Cards */}
      <div className="space-y-4">
        {campaigns.map((campaign) => {
          const isPending = priorities[campaign.id] !== originalPriorities[campaign.id];

          return (
            <div
              key={campaign.id}
              className={`bg-white rounded-xl border shadow-sm transition-all ${
                isPending
                  ? "border-[#EAB308] ring-1 ring-[#EAB308]/20"
                  : "border-[#E2E8F0]"
              }`}
            >
              {/* Card Header */}
              <div className="px-6 py-4 border-b border-[#E2E8F0]">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {campaign.is_ai_suggested && (
                      <span className="flex items-center gap-1 px-2 py-0.5 bg-[#F3E8FF] text-[#7C3AED] rounded-full text-xs font-medium">
                        <Sparkles className="h-3 w-3" />
                        AI
                      </span>
                    )}
                    <span className="font-semibold text-[#1E293B]">{campaign.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={campaign.status} />
                    <button className="p-1 text-[#94A3B8] hover:text-[#64748B] hover:bg-[#F8FAFC] rounded transition-colors">
                      <MoreVertical className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Card Content */}
              <div className="px-6 py-4">
                {/* Priority Label */}
                <div className="mb-3">
                  <span className="text-sm font-medium text-[#64748B]">Priority</span>
                </div>

                {/* Priority Slider */}
                <PrioritySlider
                  value={priorities[campaign.id]}
                  onChange={(value) => autoBalance(campaign.id, value)}
                  disabled={isConfirming}
                />

                {/* Metrics Row */}
                <div className="mt-4 pt-4 border-t border-[#E2E8F0]">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center">
                      <div className="text-lg font-bold text-[#1E293B]">
                        {campaign.meetings_this_month}
                      </div>
                      <div className="text-xs text-[#64748B]">meetings</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-[#1E293B]">
                        {campaign.reply_rate}%
                      </div>
                      <div className="text-xs text-[#64748B]">reply rate</div>
                    </div>
                    <div className="text-center">
                      <div className="text-lg font-bold text-[#1E293B]">
                        {campaign.show_rate}%
                      </div>
                      <div className="text-xs text-[#64748B]">show rate</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Total Percentage Indicator */}
      <div className="flex items-center justify-center gap-2 py-2">
        {totalPercentage === 100 ? (
          <div className="flex items-center gap-2 text-[#10B981]">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-sm font-medium">Total: 100%</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-[#F59E0B]">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm font-medium">Total: {totalPercentage}% (must be 100%)</span>
          </div>
        )}
      </div>

      {/* Action Bar (shown when pending changes) */}
      {hasPendingChanges && (
        <div className="bg-[#FFFBEB] border border-[#FCD34D] rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-[#D97706]" />
              <span className="text-sm font-medium text-[#92400E]">
                Changes pending
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleCancel}
                disabled={isConfirming}
                className="px-4 py-2 text-sm font-medium text-[#64748B] hover:text-[#1E293B] hover:bg-white rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                disabled={isConfirming || totalPercentage !== 100}
                className="px-4 py-2 bg-[#3B82F6] hover:bg-[#2563EB] text-white text-sm font-medium rounded-lg transition-colors shadow-lg shadow-blue-500/25 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isConfirming ? "Processing..." : "Confirm & Activate"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CampaignAllocationManager;
