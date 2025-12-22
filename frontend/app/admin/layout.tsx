/**
 * FILE: frontend/app/admin/layout.tsx
 * PURPOSE: Admin dashboard layout with protection
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Foundation
 */

import { redirect } from "next/navigation";
import { isPlatformAdmin, getAdminUser } from "@/lib/supabase-server";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { AdminHeader } from "@/components/admin/AdminHeader";

export default async function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Check if user is platform admin
  const isAdmin = await isPlatformAdmin();

  if (!isAdmin) {
    // Redirect non-admins to dashboard
    redirect("/dashboard");
  }

  const adminUser = await getAdminUser();

  return (
    <div className="flex h-screen overflow-hidden">
      <AdminSidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <AdminHeader
          user={adminUser || undefined}
          alertCount={0}
        />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
