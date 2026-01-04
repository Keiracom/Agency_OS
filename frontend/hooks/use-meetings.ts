/**
 * FILE: frontend/hooks/use-meetings.ts
 * PURPOSE: React Query hooks for meetings
 * PHASE: 14 (Missing UI)
 * TASK: MUI-002
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { useClient } from "./use-client";
import { getMeetings, type Meeting } from "@/lib/api/meetings";

/**
 * Hook to fetch upcoming meetings
 */
export function useMeetings(params?: { upcoming?: boolean; limit?: number }) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["meetings", clientId, params],
    queryFn: () => getMeetings(clientId!, params),
    enabled: !!clientId,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook to fetch only upcoming meetings (convenience)
 */
export function useUpcomingMeetings(limit = 5) {
  return useMeetings({ upcoming: true, limit });
}

export type { Meeting };
