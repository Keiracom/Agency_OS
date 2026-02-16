/**
 * FILE: frontend/app/dashboard/layout.tsx
 * PURPOSE: Dashboard layout with sidebar and header
 * PHASE: 8 (Frontend)
 * TASK: FE-007
 * 
 * NOTE: Auth logic DISABLED for visual review (PR #25)
 * TODO: Re-enable auth before production deploy
 */

export default function DashboardRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // TEMPORARILY DISABLED: All auth checks bypassed for visual review
  // Just render children directly - no layout wrapper needed for preview
  return <>{children}</>;
}

/*
 * ORIGINAL AUTH LAYOUT - PRESERVED FOR LATER
 * ==========================================

// Force dynamic for entire dashboard segment
export const dynamic = 'force-dynamic';

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
    pausedAt: pausedAt,
    pauseReason: pauseReason,
  } : undefined;

  return (
    <DashboardLayout user={userData} client={clientDataForLayout}>
      {children}
    </DashboardLayout>
  );
}
*/
