/**
 * FILE: frontend/hooks/use-linkedin.ts
 * PURPOSE: React Query hooks for LinkedIn connection
 * PHASE: 24H - LinkedIn Credential Connection
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  linkedinApi,
  type LinkedInConnectRequest,
  type LinkedInConnectResponse,
  type LinkedInStatusResponse,
  type TwoFactorRequest,
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
 * Hook to start LinkedIn connection
 */
export function useLinkedInConnect() {
  const queryClient = useQueryClient();

  return useMutation<LinkedInConnectResponse, Error, LinkedInConnectRequest>({
    mutationFn: linkedinApi.connect,
    onSuccess: () => {
      // Invalidate status query to refetch
      queryClient.invalidateQueries({ queryKey: LINKEDIN_QUERY_KEY });
    },
  });
}

/**
 * Hook to submit 2FA verification code
 */
export function useLinkedInVerify2FA() {
  const queryClient = useQueryClient();

  return useMutation<LinkedInConnectResponse, Error, TwoFactorRequest>({
    mutationFn: linkedinApi.verify2FA,
    onSuccess: () => {
      // Invalidate status query to refetch
      queryClient.invalidateQueries({ queryKey: LINKEDIN_QUERY_KEY });
    },
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
      // Invalidate status query to refetch
      queryClient.invalidateQueries({ queryKey: LINKEDIN_QUERY_KEY });
    },
  });
}

// Re-export types
export type { LinkedInStatusResponse, LinkedInConnectResponse };
