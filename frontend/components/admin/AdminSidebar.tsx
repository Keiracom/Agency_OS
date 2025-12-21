/**
 * FILE: frontend/components/admin/AdminSidebar.tsx
 * PURPOSE: Admin dashboard navigation sidebar
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Foundation
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  Target,
  Building2,
  BarChart3,
  DollarSign,
  Activity,
  Mail,
  Server,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
  Cpu,
  CreditCard,
  AlertTriangle,
  UserCog,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface NavItem {
  title: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  children?: NavItem[];
}

const navItems: NavItem[] = [
  {
    title: "Command Center",
    href: "/admin",
    icon: LayoutDashboard,
  },
  {
    title: "Revenue",
    href: "/admin/revenue",
    icon: DollarSign,
  },
  {
    title: "Clients",
    href: "/admin/clients",
    icon: Building2,
  },
  {
    title: "Campaigns",
    href: "/admin/campaigns",
    icon: Target,
  },
  {
    title: "Leads",
    href: "/admin/leads",
    icon: Users,
  },
  {
    title: "Activity",
    href: "/admin/activity",
    icon: Activity,
  },
  {
    title: "Replies",
    href: "/admin/replies",
    icon: Mail,
  },
  {
    title: "AI Spend",
    href: "/admin/costs/ai",
    icon: Cpu,
  },
  {
    title: "Channel Costs",
    href: "/admin/costs/channels",
    icon: CreditCard,
  },
  {
    title: "System Status",
    href: "/admin/system",
    icon: Server,
  },
  {
    title: "Suppression List",
    href: "/admin/compliance/suppression",
    icon: Shield,
  },
  {
    title: "Bounces",
    href: "/admin/compliance/bounces",
    icon: AlertTriangle,
  },
  {
    title: "Settings",
    href: "/admin/settings",
    icon: Settings,
  },
  {
    title: "Users",
    href: "/admin/settings/users",
    icon: UserCog,
  },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) => {
    if (href === "/admin") {
      return pathname === "/admin";
    }
    return pathname.startsWith(href);
  };

  return (
    <aside
      className={cn(
        "flex flex-col border-r bg-background transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-4">
        {!collapsed && (
          <Link href="/admin" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-600 text-white font-bold">
              A
            </div>
            <span className="font-semibold">Admin Console</span>
          </Link>
        )}
        {collapsed && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-600 text-white font-bold mx-auto">
            A
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2 overflow-y-auto">
        {navItems.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-red-600 text-white"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
                collapsed && "justify-center"
              )}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {!collapsed && <span>{item.title}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Back to Dashboard Link */}
      <div className="border-t p-2">
        <Link
          href="/dashboard"
          className={cn(
            "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors",
            collapsed && "justify-center"
          )}
        >
          <BarChart3 className="h-5 w-5 shrink-0" />
          {!collapsed && <span>User Dashboard</span>}
        </Link>
      </div>

      {/* Collapse Toggle */}
      <div className="border-t p-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-center"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4 mr-2" />
              Collapse
            </>
          )}
        </Button>
      </div>
    </aside>
  );
}
