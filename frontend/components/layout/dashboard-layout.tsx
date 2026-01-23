/**
 * FILE: frontend/components/layout/dashboard-layout.tsx
 * PURPOSE: Main dashboard layout wrapper
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 * UPDATED: Phase H Item 43 - Added pause status support
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
    id: string;
    name: string;
    tier: string;
    creditsRemaining: number;
    // Phase H, Item 43: Emergency pause status
    pausedAt?: string | null;
    pauseReason?: string | null;
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
