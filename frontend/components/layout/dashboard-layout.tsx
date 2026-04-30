/**
 * FILE: frontend/components/layout/dashboard-layout.tsx
 * PURPOSE: Main dashboard layout wrapper.
 * UPDATED:
 *   2026-04-30 — mobile-responsive shell (#452): Sidebar drawer + Header
 *                hamburger.
 *   2026-04-30 — A5 mobile chrome (#458): mobile topbar (52px), bottom
 *                nav (60px), content padding adjusts.
 *   2026-04-30 — A4 sidebar collapse rebase (this PR): desktop sidebar
 *                shrinks 232px ↔ 72px via chevron toggle. State
 *                persists to localStorage and mirrors onto <html
 *                data-sidebar="collapsed"> via the pre-paint script in
 *                app/layout.tsx so first paint matches saved state.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { MobileTopbar } from "./mobile-topbar";
import { BottomNav } from "./bottom-nav";

const SIDEBAR_STORAGE_KEY = "agencyos_sidebar";

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

  // A4 desktop collapse state. Hydration-safe: starts `false`, then
  // useEffect reads localStorage + the [data-sidebar] attr the
  // pre-paint script wrote. The pre-paint script set the right CSS
  // var before this code runs, so reconciling React state here
  // doesn't cause a visual snap — only a single state update.
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(SIDEBAR_STORAGE_KEY) === "collapsed");
    } catch {
      /* localStorage may be blocked; default to expanded. */
    }
  }, []);

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

  const toggleCollapsed = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      try {
        if (typeof document !== "undefined") {
          if (next) {
            document.documentElement.setAttribute("data-sidebar", "collapsed");
          } else {
            document.documentElement.removeAttribute("data-sidebar");
          }
        }
        localStorage.setItem(SIDEBAR_STORAGE_KEY, next ? "collapsed" : "expanded");
      } catch {
        /* localStorage blocked; attribute change still wins for the session. */
      }
      return next;
    });
  }, []);

  return (
    <div className="min-h-screen bg-cream text-ink">
      <Sidebar
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
      />

      {/* Mobile-only topbar — replaces the desktop Header on <md */}
      <MobileTopbar
        onOpenMenu={() => setMobileOpen(true)}
        client={client?.id
          ? { id: client.id, pausedAt: client.pausedAt, pauseReason: client.pauseReason }
          : undefined}
      />

      {/* Right column.
          Mobile: no left pad (sidebar off-canvas); pb reserves space
          for BottomNav (60px) so content isn't occluded.
          md+: padding-left tracks --sidebar-current-w (232px expanded
          ↔ 72px collapsed) with a 300ms transition that animates in
          lockstep with the sidebar's width transition. */}
      <div className="flex min-h-screen flex-col pb-[var(--bottomnav-h)] md:pb-0 transition-[padding-left] duration-300 ease-out md:pl-[var(--sidebar-current-w)]">
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
