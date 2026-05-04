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

// Demo mode: Keiracom (Keira Communications) — own usage data shown to prospects
// when no auth session + agency_os_demo cookie is present. Set by middleware on ?demo=true.
const KEIRACOM_CLIENT_ID = "ec9b4f47-8098-4d98-b449-e15308a79e17";

function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  return document.cookie
    .split("; ")
    .find((r) => r.startsWith(name + "="))
    ?.split("=")[1];
}

/**
 * Fetch the current user's primary client. In demo mode (no session + demo cookie),
 * fall back to Keiracom's own client record so prospects see real internal usage data.
 */
async function fetchCurrentClient(): Promise<ClientWithMembership | null> {
  const supabase = createBrowserClient();
  const { data: { session } } = await supabase.auth.getSession();
  const user = session?.user;

  if (!user) {
    // Demo mode fallback — middleware set agency_os_demo=true cookie via ?demo=true
    const demoCookie = readCookie("agency_os_demo");
    if (demoCookie === "true") {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { data: demoClient, error } = await (supabase as any)
        .from("clients")
        .select("*")
        .eq("id", KEIRACOM_CLIENT_ID)
        .single();
      if (error || !demoClient) {
        console.error("Demo client fetch failed:", error);
        return null;
      }
      return {
        client: demoClient as Client,
        role: "viewer" as MembershipRole,
        token: null,
      };
    }
    return null;
  }

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
