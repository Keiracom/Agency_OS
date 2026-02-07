/**
 * CampaignContext.tsx - Multi-tenant Campaign State Management
 * Phase: Operation Modular Cockpit
 * 
 * Centralizes campaign state for tenant isolation:
 * - Active campaign selection
 * - Campaign list management
 * - Data fetching scoped by campaign_id
 */

"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useCampaigns } from "@/hooks/use-campaigns";
import type { Campaign, CampaignStatus } from "@/lib/api/types";

interface CampaignContextValue {
  /** Currently selected campaign ID (null = all campaigns view) */
  activeCampaignId: string | null;
  
  /** Set the active campaign for filtering */
  setActiveCampaignId: (id: string | null) => void;
  
  /** All campaigns for the client */
  campaigns: Campaign[];
  
  /** Active campaigns only (status = active) */
  activeCampaigns: Campaign[];
  
  /** Loading state for campaigns */
  isLoading: boolean;
  
  /** Error state */
  error: Error | null;
  
  /** Refresh campaigns from API */
  refreshCampaigns: () => Promise<void>;
  
  /** Get a specific campaign by ID */
  getCampaign: (id: string) => Campaign | undefined;
  
  /** Current filter status */
  statusFilter: CampaignStatus | "all";
  
  /** Set status filter */
  setStatusFilter: (status: CampaignStatus | "all") => void;
}

const CampaignContext = createContext<CampaignContextValue | null>(null);

interface CampaignProviderProps {
  children: ReactNode;
  /** Initial campaign ID to select */
  initialCampaignId?: string | null;
}

export function CampaignProvider({
  children,
  initialCampaignId = null,
}: CampaignProviderProps) {
  const queryClient = useQueryClient();
  const [activeCampaignId, setActiveCampaignId] = useState<string | null>(
    initialCampaignId
  );
  const [statusFilter, setStatusFilter] = useState<CampaignStatus | "all">("all");

  // Fetch campaigns via existing hook
  const {
    data: campaignsResponse,
    isLoading,
    error,
    refetch,
  } = useCampaigns({
    status: statusFilter === "all" ? undefined : statusFilter,
  });

  const campaigns = useMemo(
    () => campaignsResponse?.items ?? [],
    [campaignsResponse]
  );

  const activeCampaigns = useMemo(
    () => campaigns.filter((c) => c.status === "active"),
    [campaigns]
  );

  const getCampaign = useCallback(
    (id: string) => campaigns.find((c) => c.id === id),
    [campaigns]
  );

  const refreshCampaigns = useCallback(async () => {
    await refetch();
    // Also invalidate related queries that depend on campaigns
    await queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
    await queryClient.invalidateQueries({ queryKey: ["leads"] });
    await queryClient.invalidateQueries({ queryKey: ["activity"] });
  }, [refetch, queryClient]);

  const value = useMemo<CampaignContextValue>(
    () => ({
      activeCampaignId,
      setActiveCampaignId,
      campaigns,
      activeCampaigns,
      isLoading,
      error: error as Error | null,
      refreshCampaigns,
      getCampaign,
      statusFilter,
      setStatusFilter,
    }),
    [
      activeCampaignId,
      campaigns,
      activeCampaigns,
      isLoading,
      error,
      refreshCampaigns,
      getCampaign,
      statusFilter,
    ]
  );

  return (
    <CampaignContext.Provider value={value}>
      {children}
    </CampaignContext.Provider>
  );
}

/**
 * Hook to access campaign context
 * @throws Error if used outside CampaignProvider
 */
export function useCampaignContext(): CampaignContextValue {
  const context = useContext(CampaignContext);
  if (!context) {
    throw new Error("useCampaignContext must be used within a CampaignProvider");
  }
  return context;
}

/**
 * Hook to get the active campaign object (not just ID)
 */
export function useActiveCampaign(): Campaign | null {
  const { activeCampaignId, getCampaign } = useCampaignContext();
  if (!activeCampaignId) return null;
  return getCampaign(activeCampaignId) ?? null;
}

export default CampaignContext;
