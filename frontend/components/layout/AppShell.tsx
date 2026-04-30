/**
 * FILE: frontend/components/layout/AppShell.tsx
 * PURPOSE: Single canonical layout shell for every authenticated route.
 *          Renders the rich 232px ↔ 72px collapsible Sidebar (PR #441 +
 *          A4), the desktop Header (with cycle indicator + pause-all +
 *          theme toggle from P3-2-1), the MobileTopbar + BottomNav
 *          (A5), and the demo banner.
 *
 *          B1 dispatch (2026-04-30) consolidates this with the former
 *          components/layout/dashboard-layout.tsx so dashboard routes
 *          stop double-rendering a sidebar (the bug: `app/dashboard/
 *          layout.tsx` wrapped sub-routes in `DashboardLayout` while
 *          each sub-route also imported `AppShell` — two sidebars).
 *
 *          Sub-routes import `AppShell` directly; `app/dashboard/
 *          layout.tsx` no longer wraps. Single sidebar everywhere.
 */

"use client";

import { ReactNode, useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { MobileTopbar } from "./mobile-topbar";
import { BottomNav } from "./bottom-nav";
import { useAppShellContext } from "./AppShellContext";
import { DemoBanner } from "@/components/demo/DemoBanner";
import { useDemoMode } from "@/lib/demo-context";

const SIDEBAR_STORAGE_KEY = "agencyos_sidebar";

interface AppShellProps {
  children: ReactNode;
  pageTitle?: string;
  /** Optional auth context — when provided, drives the user dropdown
   *  in Header and the avatar in the Sidebar footer. Demo mode passes
   *  the Demo Investor stub; pre-login routes pass nothing. */
  user?: {
    email: string;
    fullName?: string;
    avatarUrl?: string;
  };
  /** Optional client (tenant) — gates the pause-all button + credits
   *  badge in Header. */
  client?: {
    id: string;
    name: string;
    tier: string;
    creditsRemaining: number;
    pausedAt?: string | null;
    pauseReason?: string | null;
  };
}

export function AppShell({
  children, pageTitle = "Agency OS", user: userProp, client: clientProp,
}: AppShellProps) {
  const pathname = usePathname();
  const isDemo = useDemoMode();
  // Fall back to context provided by the server layout when explicit
  // props aren't passed (most sub-routes don't supply them).
  const ctx = useAppShellContext();
  const user = userProp ?? ctx.user;
  const client = clientProp ?? ctx.client;

  // Mobile drawer state — opened by either the desktop Header
  // hamburger (md:hidden inside Header) or the MobileTopbar
  // hamburger; closed by the Sidebar X / backdrop / nav-link click.
  // Always closed on route change.
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => { setMobileOpen(false); }, [pathname]);

  // A4 desktop collapse state. Hydration-safe: starts `false`, then
  // useEffect reads localStorage + the `[data-sidebar]` attr the
  // pre-paint script in app/layout.tsx wrote. The CSS var
  // --sidebar-current-w resolves at first paint, so reconciling
  // React state here doesn't cause a width-snap.
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem(SIDEBAR_STORAGE_KEY) === "collapsed");
    } catch {
      /* localStorage may be blocked; default to expanded. */
    }
  }, []);

  // Lock body scroll while the mobile drawer is open so the page
  // can't pan through the backdrop.
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

  // Sidebar footer user info — falls back to Maya BDR when no real
  // user is in scope (e.g. AppShell rendered from a marketing page).
  const sidebarUser = user
    ? {
        initials: (user.fullName || user.email || "U")
          .split(" ")
          .map(s => s[0])
          .join("")
          .slice(0, 2)
          .toUpperCase(),
        name: user.fullName || user.email,
        role: client?.tier ? `${client.tier} · CLIENT` : "Operator",
      }
    : undefined;

  return (
    <div className="min-h-screen bg-cream text-ink">
      {/* Demo Mode Banner (renders only when IS_DEMO_MODE / cookie set) */}
      <DemoBanner />

      {/* Sidebar (rich 232 ↔ 72 collapsible, mobile drawer) */}
      <Sidebar
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        collapsed={collapsed}
        onToggleCollapsed={toggleCollapsed}
        user={sidebarUser}
      />

      {/* Mobile-only topbar — replaces desktop Header on <md */}
      <MobileTopbar
        onOpenMenu={() => setMobileOpen(true)}
        client={client?.id
          ? { id: client.id, pausedAt: client.pausedAt, pauseReason: client.pauseReason }
          : undefined}
      />

      {/* Right column.
          Mobile: no left pad (sidebar is off-canvas); pb reserves space
          for the BottomNav (60px) so content isn't occluded.
          md+: padding-left tracks --sidebar-current-w (232px expanded
          ↔ 72px collapsed) with a 300ms transition that animates in
          lockstep with the sidebar's width transition.
          When the demo banner is visible, push the column down by 40px
          so its content doesn't slide under the banner. */}
      <div
        className={`flex min-h-screen flex-col transition-[padding-left] duration-300 ease-out md:pl-[var(--sidebar-current-w)] pb-[var(--bottomnav-h)] md:pb-0 ${
          isDemo ? "pt-10" : ""
        }`}
      >
        <Header
          title={pageTitle}
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
