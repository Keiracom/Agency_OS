"use client";

import {
  Zap,
  LayoutDashboard,
  Target,
  Users,
  MessageSquare,
  BarChart3,
  Settings,
  HelpCircle,
} from "lucide-react";

/**
 * Navigation item configuration
 */
interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

/**
 * Sidebar props
 */
export interface SidebarProps {
  /** Currently active path for highlighting */
  activePath?: string;
  /** Click handler for navigation items */
  onNavigate?: (path: string) => void;
}

/**
 * Navigation items for the sidebar
 */
const navItems: NavItem[] = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Campaigns", href: "/campaigns", icon: Target },
  { label: "Leads", href: "/leads", icon: Users },
  { label: "Replies", href: "/replies", icon: MessageSquare },
  { label: "Reports", href: "/reports", icon: BarChart3 },
  { label: "Settings", href: "/settings", icon: Settings },
];

/**
 * Sidebar - Navy sidebar navigation component
 *
 * Features:
 * - Logo with Zap icon
 * - Navigation items with active state highlighting
 * - Support card at bottom
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #1E3A5F (sidebar-bg)
 * - Active state: #2563EB (sidebar-active)
 * - Inactive text: #94A3B8 (sidebar-text)
 * - Active text: #FFFFFF (sidebar-text-active)
 * - Width: 256px (sidebar-width)
 */
export function Sidebar({ activePath = "/dashboard", onNavigate }: SidebarProps) {
  const handleClick = (path: string) => {
    if (onNavigate) {
      onNavigate(path);
    }
  };

  return (
    <aside className="fixed left-0 top-0 bottom-0 w-64 bg-[#1E3A5F] flex flex-col">
      {/* Logo */}
      <div className="px-6 py-6 border-b border-[#2D4A6F]">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#2563EB] rounded-lg">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <span className="text-lg font-bold text-white tracking-wide">
            AGENCY OS
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navItems.map((item) => {
          const isActive = activePath === item.href;
          const Icon = item.icon;

          return (
            <button
              key={item.href}
              onClick={() => handleClick(item.href)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? "bg-[#2563EB] text-white shadow-lg shadow-blue-500/25"
                  : "text-[#94A3B8] hover:text-white hover:bg-[#2D4A6F]"
              }`}
            >
              <Icon className="h-5 w-5" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Support Card */}
      <div className="px-4 py-6 border-t border-[#2D4A6F]">
        <div className="bg-[#2D4A6F] rounded-lg p-4">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-[#1E3A5F] rounded-lg">
              <HelpCircle className="h-4 w-4 text-[#94A3B8]" />
            </div>
            <span className="text-sm font-medium text-white">Need help?</span>
          </div>
          <p className="text-xs text-[#94A3B8] mb-3">
            Check our documentation or contact support for assistance.
          </p>
          <button className="w-full px-3 py-2 bg-[#1E3A5F] hover:bg-[#162D4D] text-white text-xs font-medium rounded-lg transition-colors">
            View Documentation
          </button>
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
