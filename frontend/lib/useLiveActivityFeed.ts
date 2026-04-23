/**
 * FILE: frontend/lib/useLiveActivityFeed.ts
 * PURPOSE: Supabase Realtime-backed activity feed hook. Upgrades the existing
 *          polling-based `useActivityFeed` to a websocket-push subscription,
 *          with 30s polling as automatic fallback on websocket failure.
 *
 * PHASE: PHASE-2.1-2.2 Slice 2 (Track 2.1-next — Realtime subscriptions)
 *
 * Subscribes per-client-id to four tables:
 *   - cis_outreach_outcomes   (outreach events)
 *   - replies                 (inbound replies)
 *   - dm_meetings             (meeting bookings)
 *   - client_suppression      (compliance state changes — drive UI badges)
 *
 * On INSERT/UPDATE the activity cache is invalidated so the underlying
 * `useActivityFeed` hook refetches the authoritative server-side transform
 * (keeps all business logic in one place rather than reimplementing the
 * activity shape from raw row payloads).
 *
 * Fallback: if the websocket channel enters CHANNEL_ERROR or times out on
 * SUBSCRIBE, we flip to 30s polling. This preserves functionality in dev
 * environments where Realtime may be disabled, and during network blips.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { createClient } from "@/lib/supabase";
import { useClient } from "@/hooks/use-client";
import { useActivityFeed } from "@/hooks/use-activity-feed";

type RealtimeStatus = "connecting" | "live" | "polling" | "error";

const REALTIME_TABLES = [
  "cis_outreach_outcomes",
  "replies",
  "dm_meetings",
  "client_suppression",
] as const;

const POLLING_FALLBACK_MS = 30_000;
const SUBSCRIBE_TIMEOUT_MS = 10_000;

export interface UseLiveActivityFeedOptions {
  limit?: number;
  campaignId?: string;
}

export interface UseLiveActivityFeedResult {
  activities: ReturnType<typeof useActivityFeed>["activities"];
  isLoading: boolean;
  isLive: boolean;
  status: RealtimeStatus;
  error: unknown;
  refetch: () => void;
}

export function useLiveActivityFeed(
  options: UseLiveActivityFeedOptions = {},
): UseLiveActivityFeedResult {
  const { limit = 10, campaignId } = options;
  const { clientId } = useClient();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<RealtimeStatus>("connecting");
  const fellBackRef = useRef(false);

  // Underlying hook owns fetch + transform. We pass pollInterval = 0 when
  // realtime is live, and POLLING_FALLBACK_MS when we've fallen back.
  const pollInterval =
    status === "polling" ? POLLING_FALLBACK_MS : 0;
  const underlying = useActivityFeed({ limit, campaignId, pollInterval });

  useEffect(() => {
    if (!clientId) return;
    if (fellBackRef.current) return;

    const supabase = createClient();
    const queryKey = ["activity", clientId, limit, campaignId];

    const invalidate = () => {
      queryClient.invalidateQueries({ queryKey });
    };

    const channel = supabase.channel(`activity:${clientId}`);

    for (const table of REALTIME_TABLES) {
      channel.on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table,
          filter: `client_id=eq.${clientId}`,
        },
        invalidate,
      );
    }

    let settled = false;
    const fallbackTimer = setTimeout(() => {
      if (!settled) {
        fellBackRef.current = true;
        setStatus("polling");
      }
    }, SUBSCRIBE_TIMEOUT_MS);

    channel.subscribe((subStatus) => {
      if (subStatus === "SUBSCRIBED") {
        settled = true;
        clearTimeout(fallbackTimer);
        setStatus("live");
      } else if (
        subStatus === "CHANNEL_ERROR" ||
        subStatus === "TIMED_OUT" ||
        subStatus === "CLOSED"
      ) {
        settled = true;
        clearTimeout(fallbackTimer);
        fellBackRef.current = true;
        setStatus("polling");
      }
    });

    return () => {
      clearTimeout(fallbackTimer);
      supabase.removeChannel(channel);
    };
  }, [clientId, limit, campaignId, queryClient]);

  return {
    activities: underlying.activities,
    isLoading: underlying.isLoading,
    isLive: status === "live",
    status,
    error: underlying.error,
    refetch: underlying.refetch,
  };
}

export default useLiveActivityFeed;
