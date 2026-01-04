/**
 * FILE: frontend/hooks/use-replies.ts
 * PURPOSE: React Query hooks for replies
 * PHASE: 14 (Missing UI)
 * TASK: MUI-001
 */

"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useClient } from "./use-client";
import {
  getReplies,
  getReply,
  markReplyHandled,
  type Reply,
  type ReplyFilters,
  type IntentType,
} from "@/lib/api/replies";

/**
 * Hook to fetch paginated replies list
 */
export function useReplies(params?: ReplyFilters) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["replies", clientId, params],
    queryFn: () => getReplies(clientId!, params),
    enabled: !!clientId,
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute for inbox feel
  });
}

/**
 * Hook to fetch single reply
 */
export function useReply(replyId: string | undefined) {
  const { clientId } = useClient();

  return useQuery({
    queryKey: ["reply", clientId, replyId],
    queryFn: () => getReply(clientId!, replyId!),
    enabled: !!clientId && !!replyId,
    staleTime: 30 * 1000,
  });
}

/**
 * Hook to mark reply as handled/unhandled
 */
export function useMarkReplyHandled() {
  const { clientId } = useClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ replyId, handled }: { replyId: string; handled: boolean }) =>
      markReplyHandled(clientId!, replyId, handled),
    onSuccess: (data, { replyId }) => {
      // Update the single reply cache
      queryClient.setQueryData(["reply", clientId, replyId], data);
      // Invalidate list to refetch
      queryClient.invalidateQueries({ queryKey: ["replies", clientId] });
    },
  });
}

export type { Reply, IntentType };
