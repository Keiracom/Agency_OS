/**
 * FILE: frontend/hooks/use-linkedin.ts
 * PURPOSE: React Query hooks for LinkedIn connection
 * PHASE: 309 - Onboarding Rebuild
 *
 * useLinkedInConnect and useLinkedInVerify2FA removed — credential-based
 * LinkedIn is deprecated. Connection is now via Unipile OAuth redirect.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  linkedinApi,
  type LinkedInStatusResponse,
} from "@/lib/api/linkedin";

// Query key constant
const LINKEDIN_QUERY_KEY = ["linkedin", "status"];

/**
 * Hook to get LinkedIn connection status
 */
export function useLinkedInStatus() {
  return useQuery<LinkedInStatusResponse>({
    queryKey: LINKEDIN_QUERY_KEY,
    queryFn: linkedinApi.getStatus,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // 1 minute
  });
}

/**
 * Hook to disconnect LinkedIn account
 */
export function useLinkedInDisconnect() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: linkedinApi.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: LINKEDIN_QUERY_KEY });
    },
  });
}

// Re-export types
export type { LinkedInStatusResponse };
