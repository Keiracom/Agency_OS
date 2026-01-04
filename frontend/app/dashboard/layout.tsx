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
  const { data: onboardingStatus } = await supabase.rpc('get_onboarding_status');

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

  const clientData = activeMembership?.client ? {
    name: activeMembership.client.name,
    tier: activeMembership.client.tier,
    creditsRemaining: 1250, // Would come from client data
  } : undefined;

  return (
    <DashboardLayout user={userData} client={clientData}>
      {children}
    </DashboardLayout>
  );
}
