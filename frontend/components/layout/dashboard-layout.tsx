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
  // PR1 rebuild — fixed 232px dark sidebar + cream main area with
  // 56px sticky cream-blur topbar. The sidebar is `position: fixed`,
  // so the right column reserves space via `pl-sidebar` instead of
  // wrapping in a flex grid (matches prototype #shell layout).
  return (
    <div className="min-h-screen bg-cream text-ink">
      <Sidebar />
      <div className="pl-sidebar flex min-h-screen flex-col">
        <Header user={user} client={client} />
        <main className="flex-1 bg-cream px-8 py-6">
          <div className="mx-auto w-full max-w-[1280px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
