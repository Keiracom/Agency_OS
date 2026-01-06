/**
 * FILE: frontend/hooks/use-client.ts
 * PURPOSE: Hook to get current client context
 * PHASE: 13 (Frontend-Backend Connection)
 * TASK: FBC-001
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { createBrowserClient } from "@/lib/supabase";
import type { Client, MembershipRole } from "@/lib/api/types";

interface ClientWithMembership {
  client: Client;
  role: MembershipRole;
  token: string | null;
}

/**
 * Fetch the current user's primary client
 */
async function fetchCurrentClient(): Promise<ClientWithMembership | null> {
  const supabase = createBrowserClient();
  const { data: { session } } = await supabase.auth.getSession();
  const user = session?.user;

  if (!user) return null;

  // Get user's primary membership (first accepted membership)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: membership, error } = await (supabase as any)
    .from("memberships")
    .select(`
      role,
      client_id,
      clients (*)
    `)
    .eq("user_id", user.id)
    .not("accepted_at", "is", null)
    .is("deleted_at", null)
    .order("created_at", { ascending: true })
    .limit(1)
    .single();

  if (error || !membership || !membership.clients) {
    console.error("Error fetching client membership:", error);
    return null;
  }

  // Transform the joined clients data to Client type
  const clientData = membership.clients as Client;

  return {
    client: clientData,
    role: membership.role as MembershipRole,
    token: session?.access_token || null,
  };
}

/**
 * Hook to get current client context
 *
 * Usage:
 * ```tsx
 * const { client, role, isLoading } = useClient();
 * if (client) {
 *   console.log(client.id, client.name);
 * }
 * ```
 */
export function useClient() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["current-client"],
    queryFn: fetchCurrentClient,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 1,
  });

  return {
    client: data?.client || null,
    clientId: data?.client?.id || null,
    role: data?.role || null,
    token: data?.token || null,
    isLoading,
    error,
    refetch,

    // Role checks
    isOwner: data?.role === "owner",
    isAdmin: data?.role === "owner" || data?.role === "admin",
    isMember: data?.role !== "viewer",
    isViewer: data?.role === "viewer",
  };
}

export default useClient;
