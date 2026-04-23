/**
 * FILE: frontend/lib/hooks/useRealtimeSubscription.ts
 * PURPOSE: Generic Supabase Realtime subscription with automatic polling fallback.
 * PHASE: PHASE-2.1-REALTIME-VITEST
 *
 * Usage:
 *   const { isRealtime, isPolling, lastEvent } = useRealtimeSubscription({
 *     table: "cis_outreach_outcomes",
 *     filter: `client_id=eq.${clientId}`,
 *     onInsert: (row) => qc.invalidateQueries({ queryKey: [...] }),
 *     onUpdate: (row) => ...,
 *     onDelete: (row) => ...,
 *   });
 *
 * Behaviour:
 *   - Subscribes on mount. Unsubscribes on unmount.
 *   - If SUBSCRIBED status is not reached within SUBSCRIBE_TIMEOUT_MS (5s)
 *     or if the channel emits CHANNEL_ERROR / TIMED_OUT / CLOSED, flips to
 *     polling mode: fires a tick every POLLING_INTERVAL_MS (30s) so callers
 *     can refetch as though an event occurred.
 *   - Automatic reconnect: the Supabase JS client handles transport-level
 *     reconnects; this hook only flips to polling on hard failure.
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase";

export type RealtimeStatus = "connecting" | "live" | "polling" | "error";

export interface UseRealtimeSubscriptionOptions {
  /** Table to subscribe to (public schema). */
  table: string;
  /** Optional PostgREST-style filter string: `client_id=eq.<uuid>`. */
  filter?: string;
  /** Channel name — defaults to `rt:${table}:${filter}`. */
  channelName?: string;
  /** Skip subscription entirely (e.g. no clientId yet). */
  enabled?: boolean;
  /** Called for INSERT events. */
  onInsert?: (row: Record<string, unknown>) => void;
  /** Called for UPDATE events. */
  onUpdate?: (row: Record<string, unknown>) => void;
  /** Called for DELETE events. */
  onDelete?: (row: Record<string, unknown>) => void;
  /** Called every polling tick when in polling fallback. */
  onPoll?: () => void;
}

export interface UseRealtimeSubscriptionResult {
  status: RealtimeStatus;
  isRealtime: boolean;
  isPolling: boolean;
  lastEvent: number | null;
}

const SUBSCRIBE_TIMEOUT_MS = 5_000;
const POLLING_INTERVAL_MS = 30_000;

export function useRealtimeSubscription(
  options: UseRealtimeSubscriptionOptions,
): UseRealtimeSubscriptionResult {
  const { table, filter, channelName, enabled = true, onInsert, onUpdate, onDelete, onPoll } =
    options;

  const [status, setStatus] = useState<RealtimeStatus>(enabled ? "connecting" : "error");
  const [lastEvent, setLastEvent] = useState<number | null>(null);

  // Refs so we can re-read the latest callback from the interval / channel
  // without re-subscribing on every render.
  const cbRef = useRef({ onInsert, onUpdate, onDelete, onPoll });
  cbRef.current = { onInsert, onUpdate, onDelete, onPoll };

  useEffect(() => {
    if (!enabled) {
      setStatus("error");
      return;
    }

    setStatus("connecting");
    const supabase = createClient();
    const name = channelName ?? `rt:${table}:${filter ?? "all"}`;
    const channel = supabase.channel(name);

    channel.on(
      "postgres_changes",
      { event: "*", schema: "public", table, ...(filter ? { filter } : {}) },
      (payload: { eventType?: string; new?: unknown; old?: unknown }) => {
        setLastEvent(Date.now());
        const row = (payload.new ?? payload.old ?? {}) as Record<string, unknown>;
        const ev = payload.eventType?.toUpperCase();
        if (ev === "INSERT") cbRef.current.onInsert?.(row);
        else if (ev === "UPDATE") cbRef.current.onUpdate?.(row);
        else if (ev === "DELETE") cbRef.current.onDelete?.(row);
      },
    );

    let settled = false;
    let fallbackTimer: ReturnType<typeof setTimeout> | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const startPolling = () => {
      if (pollTimer) return;
      setStatus("polling");
      pollTimer = setInterval(() => {
        setLastEvent(Date.now());
        cbRef.current.onPoll?.();
      }, POLLING_INTERVAL_MS);
    };

    fallbackTimer = setTimeout(() => {
      if (!settled) {
        settled = true;
        startPolling();
      }
    }, SUBSCRIBE_TIMEOUT_MS);

    channel.subscribe((subStatus: string) => {
      if (subStatus === "SUBSCRIBED") {
        settled = true;
        if (fallbackTimer) clearTimeout(fallbackTimer);
        setStatus("live");
      } else if (
        subStatus === "CHANNEL_ERROR" ||
        subStatus === "TIMED_OUT" ||
        subStatus === "CLOSED"
      ) {
        settled = true;
        if (fallbackTimer) clearTimeout(fallbackTimer);
        startPolling();
      }
    });

    return () => {
      if (fallbackTimer) clearTimeout(fallbackTimer);
      if (pollTimer) clearInterval(pollTimer);
      supabase.removeChannel(channel);
    };
  }, [enabled, table, filter, channelName]);

  return {
    status,
    isRealtime: status === "live",
    isPolling: status === "polling",
    lastEvent,
  };
}
