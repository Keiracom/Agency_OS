/**
 * FILE: frontend/app/dashboard/layout.tsx
 * PURPOSE: Dashboard layout with sidebar and header
 * PHASE: 8 (Frontend)
 * TASK: FE-007
 *
 * Directive #309 — Auth re-enabled. Middleware handles the auth gate;
 * this layout handles session-based data fetch and DashboardLayout wrapper.
 */

// Force dynamic for entire dashboard segment
export const dynamic = "force-dynamic";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getCurrentUser, getUserMemberships } from "@/lib/supabase-server";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { createServerClient } from "@/lib/supabase-server";
// KillSwitch consolidated into PauseAllButton (P3) — pause action now
// lives in the topbar (Header + MobileTopbar) instead of as a fixed-
// position floater. Import + render removed in this PR.
import { DashboardNav } from "@/components/dashboard/DashboardNav";
import { DemoModeBanner } from "@/components/dashboard/DemoModeBanner";

const DEMO_COOKIE = "agency_os_demo";
const DEMO_CLIENT_NAME = "Demo Agency";

/** Demo-mode bypass — when the agency_os_demo cookie is set the
 *  dashboard renders without a Supabase session. The shell uses the
 *  Demo Agency client row (created by scripts/seed_demo_tenant.py)
 *  for client context; falls back to a static stub when the row is
 *  unreachable so the demo never hard-fails. */
async function loadDemoContext() {
  let clientDataForLayout: {
    id: string; name: string; tier: string;
    creditsRemaining: number;
    pausedAt: string | null; pauseReason: string | null;
  } = {
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
      clientDataForLayout = {
        id: row.id, name: row.name, tier: row.tier,
        creditsRemaining: row.credits_remaining ?? 0,
        pausedAt: row.paused_at, pauseReason: row.pause_reason,
      };
    }
  } catch {
    // Fall through to stub client; the dashboard still renders.
  }
  return {
    userData: {
      email:    "demo@keiracom.com",
      fullName: "Demo Investor",
      avatarUrl: undefined as string | undefined,
    },
    clientDataForLayout,
  };
}

export default async function DashboardRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Demo-mode short-circuit — middleware bypasses auth for the
  // agency_os_demo=true cookie; this server layout must do the same
  // or the three redirects below fire before render.
  const demoCookie = cookies().get(DEMO_COOKIE)?.value;
  if (demoCookie === "true") {
    const { userData, clientDataForLayout } = await loadDemoContext();
    return (
      <DashboardLayout user={userData} client={clientDataForLayout}>
        <DemoModeBanner />
        <div className="flex min-h-screen">
          <DashboardNav />
          <div className="flex-1 min-w-0 pt-14 md:pt-0">{children}</div>
        </div>
      </DashboardLayout>
    );
  }

  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  // Check onboarding status
  const supabase = await createServerClient();
  const { data: onboardingStatus } = (await supabase.rpc(
    "get_onboarding_status"
  )) as {
    data: Array<{ client_id: string; needs_onboarding: boolean }> | null;
  };

  // If user needs onboarding, redirect
  if (
    onboardingStatus &&
    onboardingStatus.length > 0 &&
    onboardingStatus[0].needs_onboarding
  ) {
    redirect("/onboarding");
  }

  const memberships = await getUserMemberships();
  const activeMembership = memberships[0];

  if (!activeMembership) {
    redirect("/onboarding");
  }

  const userData = {
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

  const clientDataForLayout = activeMembership?.client
    ? {
        id: activeMembership.client.id,
        name: activeMembership.client.name,
        tier: activeMembership.client.tier,
        creditsRemaining: creditsRemaining,
        pausedAt: pausedAt,
        pauseReason: pauseReason,
      }
    : undefined;

  return (
    <DashboardLayout user={userData} client={clientDataForLayout}>
      <DemoModeBanner />
      <div className="flex min-h-screen">
        <DashboardNav />
        <div className="flex-1 min-w-0 pt-14 md:pt-0">{children}</div>
      </div>
    </DashboardLayout>
  );
}
