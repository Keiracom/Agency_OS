/**
 * Sidebar Navigation - Navy blue design from mockup
 * Open in Codux to adjust colors, icons, spacing
 */

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Target,
  Users,
  MessageSquare,
  BarChart3,
  Settings,
  Zap
} from "lucide-react";

const navItems = [
  { label: "Dashboard", href: "/dashboard-v2", icon: LayoutDashboard },
  { label: "Campaigns", href: "/dashboard-v2/campaigns", icon: Target },
  { label: "Leads", href: "/dashboard-v2/leads", icon: Users },
  { label: "Replies", href: "/dashboard-v2/replies", icon: MessageSquare },
  { label: "Reports", href: "/dashboard-v2/reports", icon: BarChart3 },
  { label: "Settings", href: "/dashboard-v2/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 bg-[#1E3A5F] border-r border-[#2D4A6F]">
      {/* Logo */}
      <div className="flex h-16 items-center px-6 border-b border-[#2D4A6F]">
        <Zap className="h-6 w-6 text-[#3B82F6] mr-2" />
        <span className="text-xl font-bold text-white tracking-tight">
          AGENCY OS
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href ||
            (item.href !== "/dashboard-v2" && pathname.startsWith(item.href));
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-lg
                text-sm font-medium transition-all duration-200
                ${isActive
                  ? "bg-[#2563EB] text-white shadow-lg shadow-blue-500/25"
                  : "text-[#94A3B8] hover:text-white hover:bg-[#2D4A6F]"
                }
              `}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Bottom Help Section */}
      <div className="absolute bottom-6 left-4 right-4">
        <div className="rounded-lg bg-[#2D4A6F] p-4">
          <p className="text-xs text-[#94A3B8] mb-1">Need help?</p>
          <a href="mailto:support@agencyos.com" className="text-sm text-[#3B82F6] hover:underline">
            Contact Support
          </a>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
