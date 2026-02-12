"use client";

/**
 * FILE: frontend/components/layout/AppShell.tsx
 * PURPOSE: Dashboard shell with sidebar navigation
 * SPRINT: Dashboard Sprint 1 - Theme Foundation
 * REFERENCE: dashboard-v4-customer.html layout structure
 */

import { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Inbox,
  Calendar,
  Megaphone,
  Users,
  BarChart3,
  Zap,
} from "lucide-react";

interface AppShellProps {
  children: ReactNode;
  pageTitle?: string;
  agencyName?: string;
}

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/dashboard/inbox", icon: Inbox, label: "Inbox", badge: 7 },
  { href: "/dashboard/meetings", icon: Calendar, label: "Meetings" },
  { href: "/dashboard/campaigns", icon: Megaphone, label: "Campaigns" },
  { href: "/dashboard/leads", icon: Users, label: "Prospects" },
  { href: "/reports", icon: BarChart3, label: "Reports" },
];

export function AppShell({ 
  children, 
  pageTitle = 'Dashboard',
  agencyName = 'Agency OS'
}: AppShellProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#0C0A08' }}>
      {/* Fixed Left Sidebar - 220px */}
      <aside className="fixed left-0 top-0 h-full w-[220px] glass-surface flex flex-col py-6 z-50">
        {/* Logo */}
        <div className="px-6 mb-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-premium flex items-center justify-center shadow-glow-sm">
              <Zap className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
            <span className="text-lg font-semibold text-text-primary font-serif">
              {agencyName}
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-1 px-3 flex-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(item.href + '/');
            const Icon = item.icon;
            const badge = 'badge' in item ? item.badge : undefined;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center gap-3 px-3 py-2.5 rounded-lg
                  transition-all duration-200 relative
                  ${
                    isActive
                      ? "bg-accent-primary/15 text-accent-primary border-l-2 border-accent-primary"
                      : "text-text-muted hover:text-text-secondary hover:bg-white/[0.03]"
                  }
                `}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm font-medium">{item.label}</span>
                {badge && badge > 0 && (
                  <span className="ml-auto min-w-[20px] h-5 px-1.5 rounded-full bg-status-error text-white text-xs font-bold flex items-center justify-center">
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom spacer */}
        <div className="px-6 py-4 border-t border-border-subtle">
          <p className="text-xs text-text-muted">Agency OS v1.0</p>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="ml-[220px] min-h-screen flex flex-col">
        {/* Top Header Bar */}
        <header className="h-16 glass-surface border-b border-border-subtle flex items-center justify-between px-8 sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <h1 className="text-lg font-semibold text-text-primary font-serif">
              {pageTitle}
            </h1>
          </div>
          
          {/* Right side - Maya Avatar placeholder */}
          <div className="flex items-center gap-4">
            <button 
              className="w-9 h-9 rounded-full gradient-ai flex items-center justify-center 
                shadow-glow-ai-sm hover:shadow-glow-ai-md transition-shadow"
              title="Maya AI Assistant"
            >
              <span className="text-white font-bold text-sm">M</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-8 max-w-[1100px]">
          {children}
        </main>
      </div>

      {/* Maya AI Bubble - Fixed Bottom Right (AI uses violet) */}
      <MayaChatBubble />
    </div>
  );
}

/** Maya chat bubble placeholder - uses violet for AI indicator */
function MayaChatBubble() {
  return (
    <div className="fixed bottom-6 right-6 z-50">
      <button
        className="relative w-14 h-14 rounded-full gradient-ai
          flex items-center justify-center shadow-glow-ai-md hover:shadow-glow-ai-md 
          transition-all animate-pulse-glow-ai"
        title="Maya AI Assistant"
      >
        {/* Avatar placeholder - using "M" for Maya */}
        <span className="text-white font-bold text-xl">M</span>
        {/* Online indicator */}
        <span className="absolute bottom-0 right-0 w-4 h-4 bg-status-success rounded-full border-2" style={{ borderColor: '#0C0A08' }}>
          <span className="absolute inset-0.5 bg-status-success rounded-full animate-ping opacity-75" />
        </span>
      </button>
    </div>
  );
}

export { MayaChatBubble };
