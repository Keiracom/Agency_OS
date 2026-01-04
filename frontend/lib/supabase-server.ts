/**
 * FILE: frontend/lib/supabase-server.ts
 * PURPOSE: Supabase server-side client configuration
 * PHASE: 8 (Frontend)
 */

import { createServerComponentClient } from "@supabase/auth-helpers-nextjs";
import { cookies } from "next/headers";
import type { Database } from "./supabase";

// Type for membership data with joined client
type MembershipWithClient = {
  id: string;
  role: string;
  accepted_at: string | null;
  client: {
    id: string;
    name: string;
    tier: string;
    subscription_status: string;
  } | null;
};

/**
 * Create a Supabase client for use in server components.
 * Requires cookies() from next/headers.
 */
export async function createServerClient() {
  const cookieStore = await cookies();
  return createServerComponentClient<Database>({ cookies: () => cookieStore });
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
export async function getUserMemberships(): Promise<MembershipWithClient[]> {
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

  return (data || []) as MembershipWithClient[];
}

/**
 * Check if user has access to a specific client.
 */
export async function hasClientAccess(clientId: string): Promise<boolean> {
  const memberships = await getUserMemberships();
  // FIXED by fixer-agent: removed any type, using MembershipWithClient from getUserMemberships
  return memberships.some((m) => m.client?.id === clientId);
}

/**
 * Get user's role in a specific client.
 */
export async function getClientRole(clientId: string): Promise<string | null> {
  const memberships = await getUserMemberships();
  // FIXED by fixer-agent: removed any type, using MembershipWithClient from getUserMemberships
  const membership = memberships.find((m) => m.client?.id === clientId);
  return membership?.role || null;
}

// FIXED by fixer-agent: added type for platform admin query result
type PlatformAdminResult = {
  is_platform_admin: boolean | null;
};

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

  // FIXED by fixer-agent: use proper type instead of any
  return (data as PlatformAdminResult).is_platform_admin === true;
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
