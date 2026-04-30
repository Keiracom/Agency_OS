"use client";

import { ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Megaphone,
  MessageSquareReply,
  BarChart3,
  Settings,
  Check,
  Radio,
  Menu,
  X,
} from "lucide-react";
import { DemoBanner } from "@/components/demo/DemoBanner";
import { useDemoMode } from "@/lib/demo-context";

interface AppShellProps {
  children: ReactNode;
  pageTitle?: string;
}

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Command Center" },
  { href: "/dashboard/pipeline", icon: Radio, label: "Live Pipeline" },
  { href: "/leads", icon: Users, label: "Leads" },
  { href: "/campaigns", icon: Megaphone, label: "Campaigns" },
  { href: "/replies", icon: MessageSquareReply, label: "Replies" },
  { href: "/reports", icon: BarChart3, label: "Reports" },
  { href: "/settings", icon: Settings, label: "Settings" },
];

export function AppShell({ children, pageTitle = 'Agency OS' }: AppShellProps) {
  const pathname = usePathname();
  const isDemo = useDemoMode();

  // Mobile drawer state — desktop ignores. Auto-closes on route change
  // and locks body scroll while open so the page can't pan through the
  // backdrop. Mirrors components/layout/dashboard-layout.tsx behaviour.
  const [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => { setMobileOpen(false); }, [pathname]);
  useEffect(() => {
    if (typeof document === "undefined") return;
    if (mobileOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => { document.body.style.overflow = prev; };
    }
  }, [mobileOpen]);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Demo Mode Banner */}
      <DemoBanner />

      {/* Base background — uses CSS var so it responds to data-theme */}
      <div className="fixed inset-0 -z-10" style={{ backgroundColor: "var(--bg-cream)" }} />

      {/* Mobile backdrop */}
      <div
        className={`fixed inset-0 z-40 bg-black/55 backdrop-blur-[2px] md:hidden transition-opacity ${
          mobileOpen ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={() => setMobileOpen(false)}
        aria-hidden="true"
      />

      {/* Fixed Left Sidebar — 72px desktop, off-canvas drawer on <md */}
      <aside
        className={`fixed left-0 h-full w-[72px] bg-bg-panel border-r border-[var(--border-default)] flex flex-col items-center py-4 z-50 transition-transform duration-300 ease-out ${
          isDemo ? 'top-10' : 'top-0'
        } ${mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
        aria-label="Primary navigation"
      >
        {/* Mobile close button */}
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation"
          className="md:hidden absolute top-2 right-2 p-1 text-ink-3 hover:text-ink"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Logo */}
        <div className="mb-8">
          <div className="w-[42px] h-[42px] bg-amber-glow border border-[var(--border-amber)] rounded-xl flex items-center justify-center shadow-glow-sm">
            <Check className="w-5 h-5 text-amber" strokeWidth={3} />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2 flex-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className={`
                  group relative w-11 h-11 rounded-xl flex items-center justify-center
                  transition-all duration-200
                  ${
                    isActive
                      ? "bg-amber-glow text-amber"
                      : "text-ink-3 hover:bg-panel hover:text-ink"
                  }
                `}
                title={item.label}
              >
                <Icon className="w-5 h-5" />
                {/* Tooltip */}
                <span className="absolute left-14 px-2 py-1 bg-panel text-ink text-xs rounded opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area — full-width on mobile, 72px reservation on md+ */}
      <div className={`md:ml-[72px] min-h-screen flex flex-col ${isDemo ? 'pt-10' : ''}`}>
        {/* Top Header Bar */}
        <header className={`h-16 bg-bg-panel border-b border-rule flex items-center justify-between px-4 md:px-6 sticky z-40 ${isDemo ? 'top-10' : 'top-0'}`}>
          <div className="flex items-center gap-3 md:gap-4 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open navigation"
              className="md:hidden -ml-1 p-2 rounded-md text-ink-3 hover:text-ink hover:bg-panel transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <h1 className="text-base md:text-lg font-semibold text-ink truncate">
              {pageTitle}
            </h1>
            <span className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-status-success/15 border border-status-success/30 rounded-full text-xs font-semibold text-status-success">
              <span className="w-1.5 h-1.5 bg-status-success rounded-full animate-pulse" />
              LIVE
            </span>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1">{children}</main>
      </div>

      {/* Maya AI Bubble - Fixed Bottom Right */}
      <div className="fixed bottom-6 right-6 z-50">
        <button
          className="relative w-14 h-14 rounded-full bg-amber
            flex items-center justify-center shadow-glow-md hover:shadow-glow-lg transition-shadow"
          title="Maya AI Assistant"
        >
          {/* Avatar placeholder - using "M" for Maya */}
          <span className="text-bg-cream font-bold text-lg">M</span>
          {/* Online indicator */}
          <span className="absolute bottom-0 right-0 w-3.5 h-3.5 bg-[#10B981] rounded-full border-2 border-bg-cream">
            <span className="absolute inset-0 bg-[#10B981] rounded-full animate-ping opacity-75" />
          </span>
        </button>
      </div>
    </div>
  );
}
