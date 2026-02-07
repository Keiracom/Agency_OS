"use client";

/**
 * Bloomberg Terminal Sidebar
 * Matches: dashboard-v3.html sidebar design
 * Theme: #0A0A12 base, #7C3AED purple accent
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Zap,
  MessageSquare,
  BarChart3,
  Settings,
  CreditCard,
  LucideIcon,
} from "lucide-react";

interface NavItem {
  key: string;
  label: string;
  icon: LucideIcon;
  href: string;
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: "Main",
    items: [
      { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
      { key: "leads", label: "Leads", icon: Users, href: "/dashboard/leads" },
      { key: "campaigns", label: "Campaigns", icon: Zap, href: "/dashboard/campaigns" },
      { key: "replies", label: "Replies", icon: MessageSquare, href: "/dashboard/replies" },
    ],
  },
  {
    title: "Analytics",
    items: [
      { key: "reports", label: "Reports", icon: BarChart3, href: "/dashboard/reports" },
    ],
  },
  {
    title: "Settings",
    items: [
      { key: "settings", label: "Settings", icon: Settings, href: "/dashboard/settings" },
      { key: "billing", label: "Billing", icon: CreditCard, href: "/dashboard/billing" },
    ],
  },
];

export function BloombergSidebar() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-60 bg-[#12121A] border-r border-[#2A2A3A] z-50 flex flex-col">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#7C3AED] to-[#9D5CFF] flex items-center justify-center shadow-lg shadow-purple-500/20">
          <svg viewBox="0 0 36 36" fill="none" className="w-5 h-5">
            <path d="M10 18L15 23L26 12" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span className="text-lg font-bold text-white">Agency OS</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {navSections.map((section) => (
          <div key={section.title} className="mb-6">
            <div className="px-5 mb-2">
              <span className="text-[11px] font-semibold text-[#6B6B7B] uppercase tracking-wider">
                {section.title}
              </span>
            </div>
            {section.items.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={item.key}
                  href={item.href}
                  className={`
                    flex items-center gap-3 px-5 py-3 mx-0 text-sm font-medium transition-all
                    ${active 
                      ? "bg-[#7C3AED]/10 text-[#9D5CFF] border-r-2 border-[#7C3AED]" 
                      : "text-[#A0A0B0] hover:bg-[#1A1A24] hover:text-white"
                    }
                  `}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}
