/**
 * FILE: frontend/components/layout/dashboard-layout.tsx
 * PURPOSE: Main dashboard layout wrapper
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 */

import { Sidebar } from "./sidebar";
import { Header } from "./header";

interface DashboardLayoutProps {
  children: React.ReactNode;
  user?: {
    email: string;
    fullName?: string;
    avatarUrl?: string;
  };
  client?: {
    name: string;
    tier: string;
    creditsRemaining: number;
  };
}

export function DashboardLayout({ children, user, client }: DashboardLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header user={user} client={client} />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
