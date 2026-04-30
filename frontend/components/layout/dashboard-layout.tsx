/**
 * FILE: frontend/components/layout/dashboard-layout.tsx
 * PURPOSE: Main dashboard layout wrapper.
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 * UPDATED:
 *   2026-04-30 — mobile-responsive shell (#452). Sidebar collapses to
 *                off-canvas drawer on <md; Header gains hamburger.
 *   2026-04-30 — A4 desktop collapse toggle (this PR). Sidebar can be
 *                shrunk to a 72px icon-only rail on md+ via chevron
 *                button. State persists to localStorage and is mirrored
 *                onto <html data-sidebar="collapsed"> so first paint
 *                matches the saved state (no width-snap flicker).
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";

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
        /* localStorage blocked; class change still wins for the session. */
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

      {/* Right column. Mobile: no left padding (sidebar is off-canvas).
          md+: reserves --sidebar-current-w (232px expanded ↔ 72px
          collapsed). The 300ms transition matches the sidebar's
          width transition so they animate in lockstep. */}
      <div
        className="flex min-h-screen flex-col transition-[padding-left] duration-300 ease-out md:pl-[var(--sidebar-current-w)]"
      >
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
