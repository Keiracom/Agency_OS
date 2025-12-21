/**
 * FILE: frontend/lib/supabase.ts
 * PURPOSE: Supabase client configuration for Next.js
 * PHASE: 8 (Frontend)
 * TASK: FE-003
 * DEPENDENCIES:
 *   - @supabase/supabase-js
 *   - @supabase/auth-helpers-nextjs
 */

import { createClientComponentClient, createServerComponentClient } from "@supabase/auth-helpers-nextjs";
import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";

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
 * Create a Supabase client for use in server components.
 * Requires cookies() from next/headers.
 */
export async function createServerClient() {
  const cookieStore = await cookies();
  return createServerComponentClient<Database>({ cookies: () => cookieStore });
}

/**
 * Create a basic Supabase client (no auth).
 * Useful for server-side operations that don't need user context.
 */
export function createAnonClient() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

  return createClient<Database>(supabaseUrl, supabaseAnonKey);
}

/**
 * Get the current user from Supabase auth.
 */
export async function getCurrentUser() {
  const supabase = await createServerClient();
  const { data: { user }, error } = await supabase.auth.getUser();

  if (error || !user) {
    return null;
  }

  return user;
}

/**
 * Get the current user's memberships.
 */
export async function getUserMemberships() {
  const user = await getCurrentUser();
  if (!user) return [];

  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("memberships")
    .select(`
      id,
      role,
      accepted_at,
      client:clients(id, name, tier, subscription_status)
    `)
    .eq("user_id", user.id)
    .not("accepted_at", "is", null);

  if (error) {
    console.error("Error fetching memberships:", error);
    return [];
  }

  return data;
}

/**
 * Check if user has access to a specific client.
 */
export async function hasClientAccess(clientId: string): Promise<boolean> {
  const memberships = await getUserMemberships();
  return memberships.some((m) => m.client?.id === clientId);
}

/**
 * Get user's role in a specific client.
 */
export async function getClientRole(clientId: string): Promise<string | null> {
  const memberships = await getUserMemberships();
  const membership = memberships.find((m) => m.client?.id === clientId);
  return membership?.role || null;
}

/**
 * Check if the current user is a platform admin.
 */
export async function isPlatformAdmin(): Promise<boolean> {
  const user = await getCurrentUser();
  if (!user) return false;

  const supabase = await createServerClient();
  const { data, error } = await supabase
    .from("users")
    .select("is_platform_admin")
    .eq("id", user.id)
    .single();

  if (error || !data) {
    return false;
  }

  return data.is_platform_admin === true;
}

/**
 * Get platform admin user data.
 */
export async function getAdminUser() {
  const user = await getCurrentUser();
  if (!user) return null;

  const isAdmin = await isPlatformAdmin();
  if (!isAdmin) return null;

  return {
    id: user.id,
    email: user.email || "",
    fullName: user.user_metadata?.full_name,
    avatarUrl: user.user_metadata?.avatar_url,
  };
}
