/**
 * FILE: frontend/components/layout/dashboard-layout.tsx
 * PURPOSE: Main dashboard layout wrapper
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 * UPDATED: 2026-04-30 — mobile-responsive shell. Sidebar now collapses
 *          to an off-canvas drawer on <md viewports; Header gains a
 *          hamburger button. State lifted here (now a client component)
 *          so Sidebar + Header share open/close.
 */

"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
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
  // Mobile drawer state. Defaults closed; opened by the Header
  // hamburger; closed by the Sidebar X button, the backdrop, or any
  // nav-link click. Always closed on route change.
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // Lock body scroll while the drawer is open on mobile so the user
  // can't accidentally pan the underlying page through the backdrop.
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (mobileOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = prev; };
    }
  }, [mobileOpen]);

  return (
    <div className="min-h-screen bg-cream text-ink">
      <Sidebar open={mobileOpen} onClose={() => setMobileOpen(false)} />

      {/* Right column. On mobile the sidebar is off-canvas → no left
          padding; on md+ it's fixed at 232px → reserve space. */}
      <div className="md:pl-sidebar flex min-h-screen flex-col">
        <Header
          user={user}
          client={client}
          onOpenMenu={() => setMobileOpen(true)}
        />
        <main className="flex-1 bg-cream px-4 py-4 sm:px-6 md:px-8 md:py-6">
          <div className="mx-auto w-full max-w-[1280px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
