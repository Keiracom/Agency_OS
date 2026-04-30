/**
 * FILE: frontend/app/dashboard/layout.tsx
 * PURPOSE: Dashboard route layout — server auth gate.
 * UPDATED:
 *   2026-04-30 — B1 sidebar consolidation. Stopped wrapping children
 *   in `DashboardLayout`; sub-routes use `<AppShell>` directly so
 *   only one sidebar renders (the prior layout rendered AppShell's
 *   72px rail AND DashboardLayout's 232px sidebar simultaneously —
 *   the double-sidebar bug). Server-fetched user + client now flow
 *   through `<AppShellProvider>` so `useAppShellContext()` inside
 *   each sub-route's AppShell picks up the right tenant context
 *   without prop threading.
 *
 *   `DashboardNav` removed — the consolidated Sidebar covers both the
 *   primary nav and the previous in-page nav, and the BottomNav from
 *   PR #458 covers mobile.
 *   `KillSwitch` already removed in P3-2-1 / P3 cleanup.
 *   `DemoModeBanner` already retired in favour of the consolidated
 *   `DemoBanner` rendered inside AppShell.
 */

// Force dynamic for entire dashboard segment
export const dynamic = "force-dynamic";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getCurrentUser, getUserMemberships } from "@/lib/supabase-server";
import { createServerClient } from "@/lib/supabase-server";
import {
  AppShellProvider,
  type AppShellUser,
  type AppShellClient,
} from "@/components/layout/AppShellContext";

const DEMO_COOKIE = "agency_os_demo";
const DEMO_CLIENT_NAME = "Demo Agency";

/** Demo-mode bypass — when the agency_os_demo cookie is set the
 *  dashboard renders without a Supabase session. Falls back to a
 *  static stub when the row is unreachable so the demo never fails. */
async function loadDemoContext(): Promise<{ user: AppShellUser; client: AppShellClient }> {
  let client: AppShellClient = {
    id: "demo-agency", name: DEMO_CLIENT_NAME, tier: "ignition",
    creditsRemaining: 1250, pausedAt: null, pauseReason: null,
  };
  try {
    const supabase = await createServerClient();
    const { data: row } = (await supabase
      .from("clients")
      .select("id, name, tier, credits_remaining, paused_at, pause_reason")
      .eq("name", DEMO_CLIENT_NAME)
      .is("deleted_at", null)
      .maybeSingle()) as {
        data: {
          id: string; name: string; tier: string;
          credits_remaining: number;
          paused_at: string | null; pause_reason: string | null;
        } | null;
      };
    if (row) {
      client = {
        id: row.id, name: row.name, tier: row.tier,
        creditsRemaining: row.credits_remaining ?? 0,
        pausedAt: row.paused_at, pauseReason: row.pause_reason,
      };
    }
  } catch {
    // Fall through to stub client; the dashboard still renders.
  }
  return {
    user: {
      email:    "demo@keiracom.com",
      fullName: "Demo Investor",
      avatarUrl: undefined,
    },
    client,
  };
}

export default async function DashboardRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Demo-mode short-circuit — middleware bypasses auth for the
  // agency_os_demo=true cookie; this server layout must do the same.
  const demoCookie = cookies().get(DEMO_COOKIE)?.value;
  if (demoCookie === "true") {
    const { user, client } = await loadDemoContext();
    return (
      <AppShellProvider user={user} client={client}>
        {children}
      </AppShellProvider>
    );
  }

  const user = await getCurrentUser();
  if (!user) redirect("/login");

  // Onboarding gate
  const supabase = await createServerClient();
  const { data: onboardingStatus } = (await supabase.rpc(
    "get_onboarding_status",
  )) as {
    data: Array<{ client_id: string; needs_onboarding: boolean }> | null;
  };
  if (
    onboardingStatus &&
    onboardingStatus.length > 0 &&
    onboardingStatus[0].needs_onboarding
  ) {
    redirect("/onboarding");
  }

  // Membership gate
  const memberships = await getUserMemberships();
  const activeMembership = memberships[0];
  if (!activeMembership) redirect("/onboarding");

  // Build context payload for AppShell consumers
  const userData: AppShellUser = {
    email: user.email || "",
    fullName: user.user_metadata?.full_name,
    avatarUrl: user.user_metadata?.avatar_url,
  };

  let creditsRemaining = 0;
  let pausedAt: string | null = null;
  let pauseReason: string | null = null;
  if (activeMembership?.client?.id) {
    const { data: clientData } = (await supabase
      .from("clients")
      .select("credits_remaining, paused_at, pause_reason")
      .eq("id", activeMembership.client.id)
      .single()) as {
        data: {
          credits_remaining: number;
          paused_at: string | null;
          pause_reason: string | null;
        } | null;
      };
    creditsRemaining = clientData?.credits_remaining ?? 0;
    pausedAt = clientData?.paused_at ?? null;
    pauseReason = clientData?.pause_reason ?? null;
  }

  const clientData: AppShellClient | undefined = activeMembership?.client
    ? {
        id: activeMembership.client.id,
        name: activeMembership.client.name,
        tier: activeMembership.client.tier,
        creditsRemaining,
        pausedAt,
        pauseReason,
      }
    : undefined;

  return (
    <AppShellProvider user={userData} client={clientData}>
      {children}
    </AppShellProvider>
  );
}
