/**
 * FILE: frontend/components/layout/sidebar.tsx
 * PURPOSE: Dashboard sidebar navigation - ported from HTML prototype
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Zap,
  MessageSquare,
  BarChart3,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Main",
    items: [
      { title: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { title: "Leads", href: "/dashboard/leads", icon: Users },
      { title: "Campaigns", href: "/dashboard/campaigns", icon: Zap },
      { title: "Replies", href: "/dashboard/replies", icon: MessageSquare },
    ],
  },
  {
    title: "Analytics",
    items: [
      { title: "Reports", href: "/dashboard/reports", icon: BarChart3 },
    ],
  },
  {
    title: "Settings",
    items: [
      { title: "Settings", href: "/dashboard/settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-bg-surface border-r border-border-default py-5 z-50">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 mb-8">
        <div className="w-9 h-9 rounded-[10px] bg-gradient-to-br from-accent-primary to-accent-primary-hover flex items-center justify-center">
          <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5">
            <path
              d="M5 12L10 17L19 8"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <span className="font-bold text-lg text-text-primary">Agency OS</span>
      </div>

      {/* Navigation Sections */}
      <nav className="space-y-6">
        {navSections.map((section) => (
          <div key={section.title}>
            <div className="px-5 text-[11px] font-semibold text-text-muted uppercase tracking-wide mb-2">
              {section.title}
            </div>
            {section.items.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
              
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-5 py-3 text-sm font-medium transition-all duration-200",
                    isActive
                      ? "bg-accent-primary/10 text-accent-primary-hover border-r-2 border-accent-primary"
                      : "text-text-secondary hover:bg-bg-surface-hover hover:text-text-primary"
                  )}
                >
                  <item.icon className="w-5 h-5 shrink-0" />
                  <span>{item.title}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
