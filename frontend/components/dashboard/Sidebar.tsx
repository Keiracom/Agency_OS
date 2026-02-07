/**
 * Sidebar.tsx - Navigation Sidebar Component
 * Phase: Operation Modular Cockpit
 * 
 * Extracted from prototype/page.tsx
 * Handles navigation with animations and badges.
 */

"use client";

import { useState } from "react";
import {
  LayoutDashboard,
  Target,
  Users,
  MessageSquare,
  BarChart3,
  Settings,
  Zap,
  type LucideIcon,
} from "lucide-react";

// ============================================
// Types
// ============================================

export type PageKey = 
  | "dashboard" 
  | "campaigns" 
  | "leads" 
  | "replies" 
  | "reports" 
  | "settings";

interface NavItem {
  key: PageKey;
  label: string;
  icon: LucideIcon;
  badge?: string;
}

interface SidebarProps {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
  /** Override default badges */
  badges?: Partial<Record<PageKey, string>>;
  /** Custom logo component */
  logo?: React.ReactNode;
  /** User info for footer */
  user?: {
    name: string;
    plan?: string;
    initial?: string;
  };
}

// ============================================
// Default Configuration
// ============================================

const defaultNavItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "campaigns", label: "Campaigns", icon: Target, badge: "3" },
  { key: "leads", label: "Leads", icon: Users, badge: "150" },
  { key: "replies", label: "Replies", icon: MessageSquare, badge: "8" },
  { key: "reports", label: "Reports", icon: BarChart3 },
  { key: "settings", label: "Settings", icon: Settings },
];

// ============================================
// Component
// ============================================

export function Sidebar({
  activePage,
  onNavigate,
  badges,
  logo,
  user = { name: "Acme Agency", plan: "Velocity Plan", initial: "A" },
}: SidebarProps) {
  const [clickedItem, setClickedItem] = useState<PageKey | null>(null);

  // Merge custom badges with defaults
  const navItems = defaultNavItems.map((item) => ({
    ...item,
    badge: badges?.[item.key] ?? item.badge,
  }));

  const handleNavClick = (key: PageKey) => {
    if (key === activePage) return;
    setClickedItem(key);
    // Small delay for click animation before navigation
    setTimeout(() => {
      onNavigate(key);
      setClickedItem(null);
    }, 150);
  };

  return (
    <div className="w-60 bg-[#0F172A] flex flex-col h-screen fixed left-0 top-0 z-40">
      {/* Logo */}
      <div className="p-4 border-b border-[#1E293B]">
        {logo ?? (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center animate-pulse">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-white">Agency OS</span>
          </div>
        )}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => handleNavClick(item.key)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 transform ${
              activePage === item.key
                ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30 scale-100"
                : clickedItem === item.key
                ? "bg-blue-500 text-white scale-95"
                : "text-slate-400 hover:text-white hover:bg-slate-800 hover:scale-[1.02] active:scale-95"
            }`}
          >
            <item.icon
              className={`w-5 h-5 transition-transform duration-200 ${
                clickedItem === item.key ? "rotate-12" : ""
              }`}
            />
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && (
              <span
                className={`px-2 py-0.5 rounded-full text-xs transition-all duration-200 ${
                  activePage === item.key
                    ? "bg-blue-500 text-white"
                    : "bg-slate-700 text-slate-300"
                } ${clickedItem === item.key ? "scale-110" : ""}`}
              >
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-[#1E293B]">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center text-white text-sm font-medium">
            {user.initial ?? user.name.charAt(0)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">{user.name}</p>
            {user.plan && (
              <p className="text-xs text-slate-500">{user.plan}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
