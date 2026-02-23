"use client";

/**
 * FILE: frontend/hooks/useICPAutoPopulate.ts
 * PURPOSE: Fetch agency_service_profile and map ICP to campaign filters
 * SPRINT: Step 5/8 - Campaign Targeting Filters + ICP Auto-Populate
 * SSOT: master_build_vision - "Maya suggests first campaign pre-filled from ICP"
 */

import { useState, useEffect, useCallback } from "react";
import { TargetingFiltersData } from "@/components/campaigns/TargetingFilters";

interface AgencyServiceProfile {
  id: string;
  client_id: string;
  services: string[];
  specialisations: string[];
  target_industries: string[];
  avg_deal_size_aud: number | null;
  win_rate: number | null;
  best_case_study: string | null;
  top_clients: string[];
  geographic_focus: string[];
  confidence_score: number | null;
}

interface ICPSuggestion {
  targetIndustries: string[];
  targetLocations: string[];
  targetCompanySizes: string[];
  targeting: TargetingFiltersData;
  profileId: string;
  confidenceScore: number;
}

/**
 * Maps avg_deal_size_aud to company size ranges
 * Logic: Higher deal sizes suggest larger companies
 */
function mapDealSizeToCompanySizes(avgDealSize: number | null): string[] {
  if (!avgDealSize) return ["1-10", "11-50", "51-200", "201-500", "500+"];
  
  if (avgDealSize < 10000) {
    // Small deals → target startups and small businesses
    return ["1-10", "11-50"];
  } else if (avgDealSize < 50000) {
    // Medium deals → target SMBs
    return ["11-50", "51-200"];
  } else if (avgDealSize < 200000) {
    // Larger deals → target mid-market
    return ["51-200", "201-500"];
  } else {
    // Enterprise deals → target large companies
    return ["201-500", "500+"];
  }
}

/**
 * Maps deal size to revenue range assumptions
 */
function mapDealSizeToRevenue(avgDealSize: number | null): { min: number | null; max: number | null } {
  if (!avgDealSize) return { min: null, max: null };
  
  // Assumption: Deal size is ~1-5% of annual budget
  // Revenue assumption: ~10-20x the deal size for target company
  const multiplier = 15;
  const minRevenue = Math.round(avgDealSize * multiplier * 0.5);
  const maxRevenue = Math.round(avgDealSize * multiplier * 3);
  
  return { min: minRevenue, max: maxRevenue };
}

/**
 * Maps deal size to suggested ALS tiers
 * Higher deal sizes → focus on better qualified leads
 */
function mapDealSizeToAlsTiers(avgDealSize: number | null): string[] {
  if (!avgDealSize) return ["Hot", "Warm", "Cool", "Cold"];
  
  if (avgDealSize > 100000) {
    // High-value deals → focus on best leads only
    return ["Hot", "Warm"];
  } else if (avgDealSize > 30000) {
    // Medium deals → include cool leads
    return ["Hot", "Warm", "Cool"];
  } else {
    // Lower deal sizes can handle higher volume
    return ["Hot", "Warm", "Cool", "Cold"];
  }
}

export function useICPAutoPopulate(clientId: string | null) {
  const [suggestion, setSuggestion] = useState<ICPSuggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchICP = useCallback(async () => {
    if (!clientId) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/v1/clients/${clientId}/service-profile`);
      
      if (!response.ok) {
        if (response.status === 404) {
          // No ICP configured yet, that's OK
          setSuggestion(null);
          return;
        }
        throw new Error("Failed to fetch ICP profile");
      }

      const profile: AgencyServiceProfile = await response.json();
      
      // Map ICP to campaign targeting suggestion
      const revenueRange = mapDealSizeToRevenue(profile.avg_deal_size_aud);
      const alsTiers = mapDealSizeToAlsTiers(profile.avg_deal_size_aud);
      const companySizes = mapDealSizeToCompanySizes(profile.avg_deal_size_aud);

      const icpSuggestion: ICPSuggestion = {
        targetIndustries: profile.target_industries || [],
        targetLocations: profile.geographic_focus || [],
        targetCompanySizes: companySizes,
        targeting: {
          alsTiers,
          hiringOnly: false, // Default off, Maya doesn't know hiring preference
          revenueMinAud: revenueRange.min,
          revenueMaxAud: revenueRange.max,
          fundingStages: [], // No ICP data for this, leave open
        },
        profileId: profile.id,
        confidenceScore: profile.confidence_score || 0.5,
      };

      setSuggestion(icpSuggestion);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [clientId]);

  useEffect(() => {
    fetchICP();
  }, [fetchICP]);

  const applyToForm = useCallback(
    (
      setFormData: (updater: (prev: any) => any) => void,
      fields?: ("industries" | "locations" | "sizes" | "targeting")[]
    ) => {
      if (!suggestion) return;

      const fieldsToApply = fields || ["industries", "locations", "sizes", "targeting"];

      setFormData((prev: any) => {
        const updates: any = { ...prev };

        if (fieldsToApply.includes("industries") && suggestion.targetIndustries.length > 0) {
          updates.targetIndustries = suggestion.targetIndustries;
        }
        if (fieldsToApply.includes("locations") && suggestion.targetLocations.length > 0) {
          updates.targetLocations = suggestion.targetLocations;
        }
        if (fieldsToApply.includes("sizes") && suggestion.targetCompanySizes.length > 0) {
          updates.targetCompanySizes = suggestion.targetCompanySizes;
        }
        if (fieldsToApply.includes("targeting")) {
          updates.targeting = suggestion.targeting;
        }

        updates.icpPrefilled = true;
        updates.icpSourceProfileId = suggestion.profileId;

        return updates;
      });
    },
    [suggestion]
  );

  return {
    suggestion,
    loading,
    error,
    applyToForm,
    refetch: fetchICP,
  };
}

export default useICPAutoPopulate;
