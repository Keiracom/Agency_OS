/**
 * FILE: frontend/app/dashboard/layout.tsx
 * PURPOSE: Dashboard layout with sidebar and header
 * PHASE: 8 (Frontend)
 * TASK: FE-007
 * UPDATED: Add onboarding redirect check
 */

import { redirect } from "next/navigation";
import { getCurrentUser, getUserMemberships } from "@/lib/supabase-server";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { createServerClient } from "@/lib/supabase-server";

export default async function DashboardRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  // Check onboarding status
  const supabase = await createServerClient();
  const { data: onboardingStatus } = await supabase.rpc('get_onboarding_status') as {
    data: Array<{ client_id: string; needs_onboarding: boolean }> | null
  };

  // If user needs onboarding, redirect
  if (onboardingStatus && onboardingStatus.length > 0 && onboardingStatus[0].needs_onboarding) {
    redirect("/onboarding");
  }

  const memberships = await getUserMemberships();
  const activeMembership = memberships[0]; // Get first (or active) membership

  // If no memberships exist (edge case), redirect to onboarding
  if (!activeMembership) {
    redirect("/onboarding");
  }

  const userData = {
    email: user.email || "",
    fullName: user.user_metadata?.full_name,
    avatarUrl: user.user_metadata?.avatar_url,
  };

  // Fetch client data including credits and pause status (Phase H, Item 43)
  let creditsRemaining = 0;
  let pausedAt: string | null = null;
  let pauseReason: string | null = null;

  if (activeMembership?.client?.id) {
    const { data: clientData } = await supabase
      .from("clients")
      .select("credits_remaining, paused_at, pause_reason")
      .eq("id", activeMembership.client.id)
      .single() as { data: { credits_remaining: number; paused_at: string | null; pause_reason: string | null } | null };

    creditsRemaining = clientData?.credits_remaining ?? 0;
    pausedAt = clientData?.paused_at ?? null;
    pauseReason = clientData?.pause_reason ?? null;
  }

  const clientDataForLayout = activeMembership?.client ? {
    id: activeMembership.client.id,
    name: activeMembership.client.name,
    tier: activeMembership.client.tier,
    creditsRemaining: creditsRemaining,
    // Phase H, Item 43: Emergency pause status
    pausedAt: pausedAt,
    pauseReason: pauseReason,
  } : undefined;

  return (
    <DashboardLayout user={userData} client={clientDataForLayout}>
      {children}
    </DashboardLayout>
  );
}
