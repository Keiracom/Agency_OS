/**
 * FILE: frontend/app/dashboard/layout.tsx
 * PURPOSE: Dashboard layout with sidebar and header
 * PHASE: 8 (Frontend)
 * TASK: FE-007
 */

import { redirect } from "next/navigation";
import { getCurrentUser, getUserMemberships } from "@/lib/supabase-server";
import { DashboardLayout } from "@/components/layout/dashboard-layout";

export default async function DashboardRootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = await getCurrentUser();

  if (!user) {
    redirect("/login");
  }

  const memberships = await getUserMemberships();
  const activeMembership = memberships[0]; // Get first (or active) membership

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
