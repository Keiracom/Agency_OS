/**
 * FILE: frontend/components/campaigns/CampaignAllocationManager.tsx
 * PURPOSE: Orchestrating component for campaign priority allocation UI
 * PHASE: Phase I Dashboard Redesign (Item 55)
 *
 * Responsibilities:
 * 1. Fetch campaigns and track original priorities
 * 2. Manage pending changes (original vs current)
 * 3. Auto-balance priorities when slider changes
 * 4. Call allocate API on confirm
 * 5. Handle state transitions (initial → pending → processing → success/error)
 * 6. Derive max campaigns from client tier
 *
 * Composed of:
 * - CampaignPriorityPanel (container)
 * - CampaignPriorityCard (individual cards)
 * - PrioritySlider (sliders within cards)
 * - useCampaignAllocations (auto-balance logic)
 */

"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { CampaignPriorityPanel, type PanelState } from "./CampaignPriorityPanel";
import { CampaignPriorityCard, type CampaignType } from "./CampaignPriorityCard";
import { useCampaignAllocations, type CampaignAllocation } from "./PrioritySlider";
import { useCampaigns, useAllocateCampaigns } from "@/hooks/use-campaigns";
import { useClient } from "@/hooks/use-client";
import type { Campaign, TierType } from "@/lib/api/types";
import { Skeleton } from "@/components/ui/skeleton";

// ============================================
// Tier Configuration
// ============================================

/**
 * Maximum campaigns allowed per tier
 * Based on docs/architecture/frontend/CAMPAIGNS.md
 */
const TIER_MAX_CAMPAIGNS: Record<TierType, number> = {
  ignition: 2,   // Starter tier
  velocity: 3,   // Growth tier
  dominance: 5,  // Scale tier
};

/**
 * Get max campaigns for a tier
 */
function getMaxCampaigns(tier: TierType | undefined | null): number {
  if (!tier) return 2; // Default to lowest
  return TIER_MAX_CAMPAIGNS[tier] || 2;
}

// ============================================
// Component Props
// ============================================

export interface CampaignAllocationManagerProps {
  /** Override max campaigns (for testing) */
  maxCampaignsOverride?: number;
  /** Additional class names */
  className?: string;
}

// ============================================
// Main Component
// ============================================

/**
 * CampaignAllocationManager orchestrates the campaign priority allocation UI.
 *
 * Features:
 * - Shows all campaigns with priority sliders
 * - Auto-balances priorities to sum to 100%
 * - Detects pending changes and shows confirm/cancel
 * - Calls backend API on confirm
 * - Shows processing/success/error states
 */
export function CampaignAllocationManager({
  maxCampaignsOverride,
  className,
}: CampaignAllocationManagerProps) {
  const router = useRouter();
  const { client } = useClient();
  const { data: campaignsData, isLoading, error } = useCampaigns({ status: "active" });
  const allocateMutation = useAllocateCampaigns();

  // Derive max campaigns from tier
  const maxCampaigns = maxCampaignsOverride ?? getMaxCampaigns(client?.tier);

  // Track original priorities (from server)
  const [originalPriorities, setOriginalPriorities] = React.useState<
    Record<string, number>
  >({});

  // Initialize allocation state from campaigns
  const campaigns = campaignsData?.items || [];
  const initialAllocations: CampaignAllocation[] = React.useMemo(() => {
    if (campaigns.length === 0) return [];
    const defaultPct = Math.floor(100 / campaigns.length);
    return campaigns.map((c) => ({
      campaignId: c.id,
      campaignName: c.name,
      priorityPct: c.lead_allocation_pct ?? defaultPct,
    }));
  }, [campaigns]);

  // Use auto-balance hook
  const { allocations, setAllocations, updateAllocation, isValid } =
    useCampaignAllocations(initialAllocations);

  // Sync allocations when campaigns change
  React.useEffect(() => {
    if (campaigns.length > 0 && allocations.length === 0) {
      const defaultPct = Math.floor(100 / campaigns.length);
      const newAllocations = campaigns.map((c) => ({
        campaignId: c.id,
        campaignName: c.name,
        priorityPct: c.lead_allocation_pct ?? defaultPct,
      }));
      setAllocations(newAllocations);

      // Set original priorities
      const originals: Record<string, number> = {};
      for (const c of campaigns) {
        originals[c.id] = c.lead_allocation_pct ?? defaultPct;
      }
      setOriginalPriorities(originals);
    }
  }, [campaigns, allocations.length, setAllocations]);

  // Calculate panel state
  const [manualState, setManualState] = React.useState<PanelState | null>(null);

  const panelState = React.useMemo((): PanelState => {
    // Manual override for processing/success/error
    if (manualState) return manualState;

    // Check if any priority has changed
    const hasChanges = allocations.some((a) => {
      const original = originalPriorities[a.campaignId];
      return original !== undefined && original !== a.priorityPct;
    });

    return hasChanges ? "pending" : "initial";
  }, [manualState, allocations, originalPriorities]);

  // Check if a specific campaign has changes
  const hasChanges = React.useCallback(
    (campaignId: string): boolean => {
      const allocation = allocations.find((a) => a.campaignId === campaignId);
      const original = originalPriorities[campaignId];
      if (!allocation || original === undefined) return false;
      return allocation.priorityPct !== original;
    },
    [allocations, originalPriorities]
  );

  // Get current priority for a campaign
  const getPriority = React.useCallback(
    (campaignId: string): number => {
      const allocation = allocations.find((a) => a.campaignId === campaignId);
      return allocation?.priorityPct ?? 0;
    },
    [allocations]
  );

  // Handle priority change from slider
  const handlePriorityChange = React.useCallback(
    (campaignId: string, newValue: number) => {
      updateAllocation(campaignId, newValue);
    },
    [updateAllocation]
  );

  // Handle cancel - reset to original
  const handleCancel = React.useCallback(() => {
    const resetAllocations = campaigns.map((c) => ({
      campaignId: c.id,
      campaignName: c.name,
      priorityPct: originalPriorities[c.id] ?? Math.floor(100 / campaigns.length),
    }));
    setAllocations(resetAllocations);
    setManualState(null);
  }, [campaigns, originalPriorities, setAllocations]);

  // Handle confirm - call API
  const handleConfirm = React.useCallback(async () => {
    if (!isValid) return;

    setManualState("processing");

    try {
      const apiAllocations = allocations.map((a) => ({
        campaign_id: a.campaignId,
        priority_pct: a.priorityPct,
      }));

      await allocateMutation.mutateAsync(apiAllocations);

      // Update original priorities to new values
      const newOriginals: Record<string, number> = {};
      for (const a of allocations) {
        newOriginals[a.campaignId] = a.priorityPct;
      }
      setOriginalPriorities(newOriginals);

      setManualState("success");

      // Auto-clear success after 3 seconds
      setTimeout(() => {
        setManualState(null);
      }, 3000);
    } catch {
      setManualState("error");
    }
  }, [allocations, isValid, allocateMutation]);

  // Handle retry
  const handleRetry = React.useCallback(() => {
    setManualState(null);
  }, []);

  // Handle view campaigns (after success)
  const handleViewCampaigns = React.useCallback(() => {
    setManualState(null);
  }, []);

  // Handle add campaign
  const handleAddCampaign = React.useCallback(() => {
    router.push("/dashboard/campaigns/new");
  }, [router]);

  // Loading state
  if (isLoading) {
    return <CampaignAllocationManagerSkeleton className={className} />;
  }

  // Error state
  if (error) {
    return (
      <CampaignPriorityPanel
        state="error"
        usedSlots={0}
        maxSlots={maxCampaigns}
        errorMessage="Failed to load campaigns"
        onRetry={() => window.location.reload()}
        className={className}
      >
        {null}
      </CampaignPriorityPanel>
    );
  }

  return (
    <CampaignPriorityPanel
      state={panelState}
      usedSlots={campaigns.length}
      maxSlots={maxCampaigns}
      onAddCampaign={handleAddCampaign}
      onCancel={handleCancel}
      onConfirm={handleConfirm}
      onRetry={handleRetry}
      onViewCampaigns={handleViewCampaigns}
      errorMessage={allocateMutation.error?.message}
      className={className}
    >
      {campaigns.map((campaign) => (
        <CampaignPriorityCard
          key={campaign.id}
          id={campaign.id}
          name={campaign.name}
          type={getCampaignType(campaign)}
          status={campaign.status}
          priorityPct={getPriority(campaign.id)}
          channels={getCampaignChannels(campaign)}
          metrics={getCampaignMetrics(campaign)}
          hasChanges={hasChanges(campaign.id)}
          onPriorityChange={handlePriorityChange}
        />
      ))}
    </CampaignPriorityPanel>
  );
}

// ============================================
// Helper Functions
// ============================================

/**
 * Get campaign type (AI suggested or custom)
 */
function getCampaignType(campaign: Campaign): CampaignType {
  return campaign.is_ai_suggested ? "ai" : "custom";
}

/**
 * Get active channels from campaign allocations
 */
function getCampaignChannels(campaign: Campaign) {
  return {
    email: (campaign.allocation_email ?? 0) > 0,
    linkedin: (campaign.allocation_linkedin ?? 0) > 0,
    sms: (campaign.allocation_sms ?? 0) > 0,
    voice: (campaign.allocation_voice ?? 0) > 0,
  };
}

/**
 * Get campaign metrics for display
 */
function getCampaignMetrics(campaign: Campaign) {
  return {
    meetingsBooked: campaign.leads_converted ?? 0,
    replyRate: campaign.reply_rate ?? 0,
    showRate: campaign.conversion_rate ?? 0, // TODO: Use actual show rate when available
  };
}

// ============================================
// Loading Skeleton
// ============================================

function CampaignAllocationManagerSkeleton({ className }: { className?: string }) {
  return (
    <div className={className}>
      <div className="rounded-lg border bg-card p-6 space-y-6">
        {/* Header skeleton */}
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-6 w-40 mb-2" />
            <Skeleton className="h-4 w-24" />
          </div>
          <Skeleton className="h-9 w-32" />
        </div>

        {/* Card skeletons */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-lg border p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Skeleton className="h-5 w-5" />
                <Skeleton className="h-5 w-40" />
              </div>
              <Skeleton className="h-5 w-24" />
            </div>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-2 w-full" />
            <Skeleton className="h-16 w-full" />
            <div className="flex justify-between">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default CampaignAllocationManager;
