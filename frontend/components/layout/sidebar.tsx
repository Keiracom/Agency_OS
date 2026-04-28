/**
 * FILE: frontend/components/layout/sidebar.tsx
 * PURPOSE: 232px dark sidebar with amber active borders + Playfair logo accent.
 *          Ported from dashboard-master-agency-desk.html (PR1 rebuild).
 * PHASE: 8 (Frontend) — Dashboard rebuild PR 1 of 4
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Megaphone,
  MessageSquareReply,
  BarChart3,
  Settings,
  Radio,
  Inbox,
  Calendar,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: "Today",
    items: [
      { title: "Command Center", href: "/dashboard", icon: LayoutDashboard },
      { title: "Live Pipeline",  href: "/dashboard/pipeline", icon: Radio },
      { title: "Inbox",          href: "/dashboard/inbox", icon: Inbox },
      { title: "Meetings",       href: "/dashboard/meetings", icon: Calendar },
    ],
  },
  {
    title: "Workflow",
    items: [
      { title: "Leads",     href: "/dashboard/leads", icon: Users },
      { title: "Campaigns", href: "/dashboard/campaigns", icon: Megaphone },
      { title: "Replies",   href: "/dashboard/replies", icon: MessageSquareReply },
    ],
  },
  {
    title: "Insights",
    items: [
      { title: "Reports",  href: "/dashboard/reports", icon: BarChart3 },
      { title: "Settings", href: "/dashboard/settings", icon: Settings },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="fixed left-0 top-0 bottom-0 w-sidebar bg-brand-bar text-white/80 flex flex-col z-50 overflow-y-auto"
      style={{ borderRight: "1px solid rgba(255,255,255,0.06)" }}
    >
      {/* Logo block — Playfair Display with amber italic accent */}
      <div
        className="px-5 pt-[22px] pb-[18px]"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div className="font-display font-bold text-[20px] tracking-[-0.02em] text-white">
          Agency<em className="text-amber not-italic-fallback" style={{ fontStyle: "italic" }}>OS</em>
        </div>
        <div className="font-mono text-[9px] tracking-[0.14em] uppercase text-white/30 mt-[3px]">
          Agency Desk
        </div>
      </div>

      {/* Nav sections */}
      <nav className="flex-1">
        {navSections.map((section) => (
          <div key={section.title} className="pt-4 pb-1">
            <div className="font-mono text-[9px] tracking-[0.14em] uppercase text-white/30 px-5 pb-2">
              {section.title}
            </div>
            {section.items.map((item) => {
              const isActive =
                pathname === item.href ||
                (item.href !== "/dashboard" && pathname.startsWith(item.href + "/"));
              const Icon = item.icon;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-5 py-[9px] text-[13px] transition-colors",
                    "border-l-2",
                    isActive
                      ? "text-white bg-amber-soft border-amber font-medium"
                      : "text-white/70 border-transparent hover:text-white hover:bg-white/[0.03]",
                  )}
                >
                  <Icon
                    className={cn(
                      "w-4 h-4 shrink-0",
                      isActive ? "text-amber opacity-100" : "opacity-75",
                    )}
                  />
                  <span>{item.title}</span>
                  {item.badge && (
                    <span className="ml-auto font-mono text-[10px] bg-amber text-on-amber px-[6px] py-[1px] rounded-[10px] min-w-[20px] text-center font-semibold">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Footer — avatar block (matches prototype .sb-foot) */}
      <div
        className="mt-auto px-5 py-4 flex items-center gap-[10px]"
        style={{ borderTop: "1px solid rgba(255,255,255,0.06)" }}
      >
        <div className="w-[30px] h-[30px] rounded-full bg-amber text-on-amber grid place-items-center font-display font-bold text-[12px] shrink-0">
          M
        </div>
        <div className="leading-tight">
          <div className="text-[13px] text-white">Maya</div>
          <div className="font-mono text-[10.5px] tracking-[0.06em] text-white/40">
            BDR · ON
          </div>
        </div>
      </div>
    </aside>
  );
}
