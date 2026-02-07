/**
 * FILE: frontend/hooks/use-elliot.ts
 * PURPOSE: React Query hooks with Supabase Realtime for Elliot monitoring dashboard
 * PHASE: Elliot Dashboard
 */

"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { createBrowserClient } from "@/lib/supabase";
import type { RealtimeChannel } from "@supabase/supabase-js";

// ============================================
// Types
// ============================================

export type TaskStatus = "running" | "completed" | "failed" | "retry";

export interface ElliotTask {
  id: string;
  label: string;
  session_key: string;
  task_description: string;
  status: TaskStatus;
  retry_count: number;
  max_retries: number;
  output_summary: string | null;
  parent_session_key: string | null;
  created_at: string;
  completed_at: string | null;
  last_checked_at: string | null;
}

export interface SignoffItem {
  id: string;
  knowledge_id: string;
  action_type: "evaluate_tool" | "build_poc" | "research";
  title: string;
  summary: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  decided_at: string | null;
}

export interface KnowledgeEntry {
  id: string;
  category: string;
  content: string;
  summary: string | null;
  source_url: string | null;
  source_type: string | null;
  learned_at: string;
  applied: boolean;
  applied_at: string | null;
  confidence_score: number;
  relevance_score: number | null;
  tags: string[] | null;
}

// ============================================
// Realtime Connection Status
// ============================================

export type RealtimeStatus = "connecting" | "connected" | "disconnected" | "error";

// Global status tracker for all Elliot realtime connections
const realtimeStatusListeners = new Set<(status: RealtimeStatus) => void>();
let globalRealtimeStatus: RealtimeStatus = "connecting";

function setGlobalRealtimeStatus(status: RealtimeStatus) {
  globalRealtimeStatus = status;
  realtimeStatusListeners.forEach((listener) => listener(status));
}

export function useRealtimeStatus(): RealtimeStatus {
  const [status, setStatus] = useState<RealtimeStatus>(globalRealtimeStatus);

  useEffect(() => {
    realtimeStatusListeners.add(setStatus);
    return () => {
      realtimeStatusListeners.delete(setStatus);
    };
  }, []);

  return status;
}

// ============================================
// Realtime Subscription Hook
// ============================================

function useRealtimeSubscription(
  table: string,
  queryKeys: string[][],
  enabled: boolean = true
) {
  const queryClient = useQueryClient();
  const channelRef = useRef<RealtimeChannel | null>(null);
  const supabaseRef = useRef(createBrowserClient());

  // Memoize the invalidation callback
  const handleChange = useCallback(
    (payload: { eventType: string }) => {
      console.log(`[Realtime] ${table} change:`, payload.eventType);
      // Invalidate all related queries
      queryKeys.forEach((key) => {
        queryClient.invalidateQueries({ queryKey: key });
      });
    },
    [table, queryKeys, queryClient]
  );

  useEffect(() => {
    if (!enabled) return;

    // Avoid creating duplicate subscriptions
    if (channelRef.current) {
      return;
    }

    const supabase = supabaseRef.current;
    const channelName = `elliot-${table}-${Date.now()}`;

    const channel: RealtimeChannel = supabase
      .channel(channelName)
      .on(
        "postgres_changes",
        {
          event: "*", // INSERT, UPDATE, DELETE
          schema: "public",
          table: table,
        },
        handleChange
      )
      .subscribe((status) => {
        if (status === "SUBSCRIBED") {
          console.log(`[Realtime] ✓ ${table} connected`);
          setGlobalRealtimeStatus("connected");
        } else if (status === "CHANNEL_ERROR") {
          console.error(`[Realtime] ✗ ${table} error`);
          setGlobalRealtimeStatus("error");
        } else if (status === "CLOSED") {
          setGlobalRealtimeStatus("disconnected");
        }
      });

    channelRef.current = channel;

    return () => {
      if (channelRef.current) {
        console.log(`[Realtime] Unsubscribing from ${table}`);
        supabase.removeChannel(channelRef.current);
        channelRef.current = null;
      }
    };
  }, [table, enabled, handleChange]);
}

// ============================================
// Task Monitor Hooks
// ============================================

export function useTasks(statusFilter?: TaskStatus | "all") {
  const supabase = createBrowserClient();
  const queryClient = useQueryClient();

  // Subscribe to realtime updates
  useRealtimeSubscription(
    "elliot_tasks",
    [["elliot-tasks"], ["elliot-task-stats"]],
    true
  );

  return useQuery({
    queryKey: ["elliot-tasks", statusFilter],
    queryFn: async () => {
      let query = supabase
        .from("elliot_tasks")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(100);

      if (statusFilter && statusFilter !== "all") {
        query = query.eq("status", statusFilter);
      }

      const { data, error } = await query;

      if (error) throw error;
      return data as ElliotTask[];
    },
    staleTime: 30 * 1000, // 30 seconds (realtime handles updates)
  });
}

export function useTaskStats() {
  const supabase = createBrowserClient();

  return useQuery({
    queryKey: ["elliot-task-stats"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("elliot_tasks")
        .select("status");

      if (error) throw error;

      const stats = {
        running: 0,
        completed: 0,
        failed: 0,
        retry: 0,
        total: 0,
      };

      for (const row of data || []) {
        const status = row.status as TaskStatus;
        stats[status] = (stats[status] || 0) + 1;
        stats.total++;
      }

      return stats;
    },
    staleTime: 30 * 1000,
  });
}

// ============================================
// Sign-off Queue Hooks
// ============================================

export function useSignoffQueue(statusFilter?: "pending" | "approved" | "rejected" | "all") {
  const supabase = createBrowserClient();

  // Subscribe to realtime updates
  useRealtimeSubscription(
    "elliot_signoff_queue",
    [["elliot-signoff-queue"]],
    true
  );

  return useQuery({
    queryKey: ["elliot-signoff-queue", statusFilter],
    queryFn: async () => {
      let query = supabase
        .from("elliot_signoff_queue")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);

      if (statusFilter && statusFilter !== "all") {
        query = query.eq("status", statusFilter);
      }

      const { data, error } = await query;

      if (error) throw error;
      return data as SignoffItem[];
    },
    staleTime: 30 * 1000,
  });
}

export function useSignoffAction() {
  const supabase = createBrowserClient();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      action,
    }: {
      id: string;
      action: "approved" | "rejected";
    }) => {
      const { data, error } = await supabase
        .from("elliot_signoff_queue")
        .update({
          status: action,
          decided_at: new Date().toISOString(),
        })
        .eq("id", id)
        .select()
        .single();

      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      // Realtime will handle the cache invalidation, but we can also do it immediately
      queryClient.invalidateQueries({ queryKey: ["elliot-signoff-queue"] });
    },
  });
}

// ============================================
// Knowledge Feed Hooks
// ============================================

export function useKnowledge(sourceFilter?: string | "all") {
  const supabase = createBrowserClient();

  // Subscribe to realtime updates
  useRealtimeSubscription(
    "elliot_knowledge",
    [["elliot-knowledge"], ["elliot-knowledge-stats"]],
    true
  );

  return useQuery({
    queryKey: ["elliot-knowledge", sourceFilter],
    queryFn: async () => {
      let query = supabase
        .from("elliot_knowledge")
        .select("*")
        .is("deleted_at", null)
        .order("learned_at", { ascending: false })
        .limit(50);

      if (sourceFilter && sourceFilter !== "all") {
        query = query.eq("source_type", sourceFilter);
      }

      const { data, error } = await query;

      if (error) throw error;
      return data as KnowledgeEntry[];
    },
    staleTime: 60 * 1000,
  });
}

export function useKnowledgeStats() {
  const supabase = createBrowserClient();

  return useQuery({
    queryKey: ["elliot-knowledge-stats"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("elliot_knowledge")
        .select("source_type, applied")
        .is("deleted_at", null);

      if (error) throw error;

      const bySource: Record<string, number> = {};
      let total = 0;
      let applied = 0;

      for (const row of data || []) {
        const source = row.source_type || "unknown";
        bySource[source] = (bySource[source] || 0) + 1;
        total++;
        if (row.applied) applied++;
      }

      return { bySource, total, applied };
    },
    staleTime: 60 * 1000,
  });
}

// ============================================
// Cost Overview (from static data or future table)
// ============================================

export interface CostCategory {
  name: string;
  lowEstimate: number;
  highEstimate: number;
  services: Array<{
    name: string;
    cost: string;
    notes?: string;
  }>;
}

export function useCosts() {
  // For now, return static data from costs.md
  // In future, this could query an elliot_costs table with realtime
  return useQuery({
    queryKey: ["elliot-costs"],
    queryFn: async (): Promise<{ categories: CostCategory[]; summary: { low: number; high: number } }> => {
      // Static data derived from costs.md
      const categories: CostCategory[] = [
        {
          name: "Core Infrastructure",
          lowEstimate: 75,
          highEstimate: 150,
          services: [
            { name: "Supabase", cost: "$25-75/mo", notes: "Pro tier + usage" },
            { name: "Railway", cost: "$20-50/mo", notes: "Backend hosting" },
            { name: "Redis (Upstash)", cost: "$5-25/mo", notes: "Caching" },
          ],
        },
        {
          name: "AI/LLM",
          lowEstimate: 50,
          highEstimate: 500,
          services: [
            { name: "Anthropic Claude", cost: "$50-500+/mo", notes: "Usage-dependent" },
          ],
        },
        {
          name: "Lead Enrichment",
          lowEstimate: 100,
          highEstimate: 500,
          services: [
            { name: "Apollo.io", cost: "$79-199/mo", notes: "1-2 users" },
            { name: "Prospeo", cost: "$49-99/mo", notes: "Email finder" },
            { name: "DataForSEO", cost: "$50-100/mo", notes: "Domain metrics" },
            { name: "Apify", cost: "$29-199/mo", notes: "Scraping" },
          ],
        },
        {
          name: "Email Channel",
          lowEstimate: 120,
          highEstimate: 400,
          services: [
            { name: "Salesforge", cost: "$80-160/mo", notes: "Campaign sending" },
            { name: "InfraForge", cost: "$50-150/mo", notes: "Domains & mailboxes" },
            { name: "WarmForge", cost: "Free", notes: "With Salesforge" },
            { name: "Resend", cost: "$20/mo", notes: "Transactional" },
          ],
        },
        {
          name: "LinkedIn Channel",
          lowEstimate: 55,
          highEstimate: 275,
          services: [
            { name: "Unipile", cost: "$55-275/mo", notes: "10-50 accounts" },
          ],
        },
        {
          name: "Voice Channel",
          lowEstimate: 50,
          highEstimate: 300,
          services: [
            { name: "Vapi", cost: "$50-200/mo", notes: "Voice AI" },
            { name: "Twilio", cost: "$20-100/mo", notes: "Telephony" },
            { name: "ElevenLabs", cost: "$22-99/mo", notes: "TTS" },
          ],
        },
        {
          name: "SMS/Mail",
          lowEstimate: 20,
          highEstimate: 100,
          services: [
            { name: "ClickSend", cost: "$20-100/mo AUD", notes: "SMS + direct mail" },
          ],
        },
      ];

      const summary = {
        low: categories.reduce((sum, c) => sum + c.lowEstimate, 0),
        high: categories.reduce((sum, c) => sum + c.highEstimate, 0),
      };

      return { categories, summary };
    },
    staleTime: Infinity, // Static data
  });
}
