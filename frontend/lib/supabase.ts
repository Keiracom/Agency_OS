/**
 * FILE: frontend/lib/supabase.ts
 * PURPOSE: Supabase client configuration for Next.js (Client-side only)
 * PHASE: 8 (Frontend)
 */

import { createClientComponentClient } from "@supabase/auth-helpers-nextjs";
import { createClient } from "@supabase/supabase-js";

// Types for our database tables
export type Database = {
  public: {
    Tables: {
      clients: {
        Row: {
          id: string;
          name: string;
          tier: "ignition" | "velocity" | "dominance";
          subscription_status: "trialing" | "active" | "past_due" | "cancelled" | "paused";
          credits_remaining: number;
          default_permission_mode: "autopilot" | "co_pilot" | "manual";
          created_at: string;
          updated_at: string;
          deleted_at: string | null;
        };
      };
      users: {
        Row: {
          id: string;
          email: string;
          full_name: string | null;
          is_platform_admin: boolean;
          created_at: string;
          updated_at: string;
        };
      };
      memberships: {
        Row: {
          id: string;
          user_id: string;
          client_id: string;
          role: "owner" | "admin" | "member" | "viewer";
          accepted_at: string | null;
          created_at: string;
        };
      };
      campaigns: {
        Row: {
          id: string;
          client_id: string;
          name: string;
          description: string | null;
          status: "draft" | "active" | "paused" | "completed";
          permission_mode: "autopilot" | "co_pilot" | "manual" | null;
          allocation_email: number;
          allocation_sms: number;
          allocation_linkedin: number;
          allocation_voice: number;
          allocation_mail: number;
          daily_limit: number;
          total_leads: number;
          leads_contacted: number;
          leads_replied: number;
          leads_converted: number;
          created_at: string;
          updated_at: string;
          deleted_at: string | null;
        };
      };
      leads: {
        Row: {
          id: string;
          client_id: string;
          campaign_id: string;
          email: string;
          phone: string | null;
          first_name: string | null;
          last_name: string | null;
          title: string | null;
          company: string | null;
          linkedin_url: string | null;
          als_score: number | null;
          als_tier: string | null;
          status: "new" | "enriched" | "scored" | "in_sequence" | "converted" | "unsubscribed" | "bounced";
          created_at: string;
          updated_at: string;
          deleted_at: string | null;
        };
      };
      activities: {
        Row: {
          id: string;
          client_id: string;
          campaign_id: string;
          lead_id: string;
          channel: "email" | "sms" | "linkedin" | "voice" | "mail";
          action: string;
          provider_message_id: string | null;
          metadata: Record<string, unknown>;
          created_at: string;
        };
      };
      // Elliot Tables
      elliot_tasks: {
        Row: {
          id: string;
          label: string;
          session_key: string;
          task_description: string;
          status: "running" | "completed" | "failed" | "retry";
          retry_count: number;
          max_retries: number;
          output_summary: string | null;
          parent_session_key: string | null;
          created_at: string;
          completed_at: string | null;
          last_checked_at: string | null;
        };
      };
      elliot_signoff_queue: {
        Row: {
          id: string;
          knowledge_id: string;
          action_type: "evaluate_tool" | "build_poc" | "research";
          title: string;
          summary: string;
          status: "pending" | "approved" | "rejected";
          created_at: string;
          decided_at: string | null;
        };
      };
      elliot_knowledge: {
        Row: {
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
          deleted_at: string | null;
        };
      };
    };
  };
};

/**
 * Create a Supabase client for use in client components.
 * Uses cookies for session management.
 */
export function createBrowserClient() {
  return createClientComponentClient<Database>();
}

/**
 * Create a basic Supabase client (no auth).
 * Useful for operations that don't need user context.
 */
export function createAnonClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  return createClient<Database>(supabaseUrl, supabaseAnonKey);
}

/**
 * Alias for createBrowserClient - used by onboarding and other client components.
 */
export { createBrowserClient as createClient };
