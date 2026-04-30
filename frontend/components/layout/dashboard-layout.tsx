/**
 * FILE: frontend/components/layout/dashboard-layout.tsx
 * PURPOSE: Main dashboard layout wrapper.
 * UPDATED:
 *   2026-04-30 — mobile-responsive shell (#452): Sidebar drawer + Header
 *                hamburger.
 *   2026-04-30 — A5 mobile chrome (this PR): mobile topbar (52px,
 *                replaces desktop Header on <md), bottom nav (60px,
 *                fixed bottom md:hidden), content padding adjusts so
 *                neither bar occludes the page.
 */

"use client";

import { useState, useEffect } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { MobileTopbar } from "./mobile-topbar";
import { BottomNav } from "./bottom-nav";

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
    pausedAt?: string | null;
    pauseReason?: string | null;
  };
}

export function DashboardLayout({ children, user, client }: DashboardLayoutProps) {
  // Mobile drawer state. Defaults closed; opened by either the desktop
  // Header hamburger or the MobileTopbar hamburger; closed by the
  // Sidebar X button, the backdrop, or any nav-link click. Always
  // closed on route change.
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

      {/* Mobile-only topbar — replaces the desktop Header on <md */}
      <MobileTopbar
        onOpenMenu={() => setMobileOpen(true)}
        client={client?.id
          ? { id: client.id, pausedAt: client.pausedAt, pauseReason: client.pauseReason }
          : undefined}
      />

      {/* Right column. Mobile: no left pad (sidebar off-canvas), bottom
          padding reserves space for the BottomNav (60px) so content
          isn't hidden behind it. md+: 232px sidebar reservation, no
          bottom nav, no extra bottom pad. */}
      <div className="md:pl-sidebar flex min-h-screen flex-col pb-[var(--bottomnav-h)] md:pb-0">
        <Header
          user={user}
          client={client}
          onOpenMenu={() => setMobileOpen(true)}
        />
        <main className="flex-1 bg-cream px-4 py-4 sm:px-6 md:px-8 md:py-6">
          <div className="mx-auto w-full max-w-[1280px]">{children}</div>
        </main>
      </div>

      {/* Mobile-only bottom navigation */}
      <BottomNav />
    </div>
  );
}
