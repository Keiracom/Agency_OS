/**
 * Sidebar.tsx - Navigation Sidebar Component
 * Phase: Operation Modular Cockpit
 * 
 * Extracted from prototype/page.tsx
 * Handles navigation with animations, badges, and collapse/expand.
 * Bloomberg dark mode styling with glassmorphic effects.
 * 
 * Updated: Now uses Next.js Link for proper routing.
 */

"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Target,
  Users,
  MessageSquare,
  BarChart3,
  Settings,
  Zap,
  ChevronLeft,
  ChevronRight,
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
  href: string;
}

interface SidebarProps {
  /** @deprecated Use automatic route detection instead */
  activePage?: PageKey;
  /** @deprecated Navigation now uses Next.js Link */
  onNavigate?: (page: PageKey) => void;
  /** Override default badges */
  badges?: Partial<Record<PageKey, string>>;
  /** Custom logo component */
  logo?: React.ReactNode;
  /** User info for footer */
  user?: {
    name: string;
    email?: string;
    plan?: string;
    initial?: string;
    avatarUrl?: string;
  };
  /** Controlled collapsed state */
  collapsed?: boolean;
  /** Callback when collapse state changes */
  onCollapsedChange?: (collapsed: boolean) => void;
  /** Default collapsed state for uncontrolled mode */
  defaultCollapsed?: boolean;
}

// ============================================
// Default Configuration
// ============================================

const defaultNavItems: NavItem[] = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, href: "/prototype" },
  { key: "campaigns", label: "Campaigns", icon: Target, badge: "3", href: "/prototype/campaigns" },
  { key: "leads", label: "Leads", icon: Users, badge: "150", href: "/prototype/leads" },
  { key: "replies", label: "Replies", icon: MessageSquare, badge: "8", href: "/prototype/replies" },
  { key: "reports", label: "Reports", icon: BarChart3, href: "/prototype/reports" },
  { key: "settings", label: "Settings", icon: Settings, href: "/prototype/settings" },
];

/**
 * Derive active page from pathname
 */
function getActivePageFromPath(pathname: string): PageKey {
  if (pathname === "/prototype" || pathname === "/prototype/") return "dashboard";
  const segment = pathname.split("/")[2]; // /prototype/{segment}
  if (segment && ["campaigns", "leads", "replies", "reports", "settings"].includes(segment)) {
    return segment as PageKey;
  }
  return "dashboard";
}

// ============================================
// Component
// ============================================

export function Sidebar({
  activePage: activePageProp,
  onNavigate,
  badges,
  logo,
  user = { name: "Acme Agency", plan: "Velocity Plan", initial: "A" },
  collapsed: controlledCollapsed,
  onCollapsedChange,
  defaultCollapsed = false,
}: SidebarProps) {
  const pathname = usePathname();
  const [clickedItem, setClickedItem] = useState<PageKey | null>(null);
  const [internalCollapsed, setInternalCollapsed] = useState(defaultCollapsed);
  
  // Derive active page from pathname, fall back to prop for backward compat
  const activePage = activePageProp ?? getActivePageFromPath(pathname);
  
  // Support both controlled and uncontrolled modes
  const isControlled = controlledCollapsed !== undefined;
  const collapsed = isControlled ? controlledCollapsed : internalCollapsed;
  
  const toggleCollapsed = useCallback(() => {
    const newValue = !collapsed;
    if (!isControlled) {
      setInternalCollapsed(newValue);
    }
    onCollapsedChange?.(newValue);
  }, [collapsed, isControlled, onCollapsedChange]);

  // Merge custom badges with defaults
  const navItems = defaultNavItems.map((item) => ({
    ...item,
    badge: badges?.[item.key] ?? item.badge,
  }));

  const handleNavClick = (key: PageKey) => {
    if (key === activePage) return;
    setClickedItem(key);
    // Legacy callback support
    if (onNavigate) {
      setTimeout(() => {
        onNavigate(key);
        setClickedItem(null);
      }, 150);
    } else {
      // Just handle animation, Link does navigation
      setTimeout(() => setClickedItem(null), 150);
    }
  };

  return (
    <div 
      className={`
        ${collapsed ? "w-[72px]" : "w-60"} 
        bg-bg-cream/80 backdrop-blur-xl 
        flex flex-col h-screen fixed left-0 top-0 z-40 
        border-r border-white/10
        transition-all duration-300 ease-in-out
      `}
    >
      {/* Logo */}
      <div className="p-4 border-b border-white/10 relative">
        {logo ?? (
          <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>
            <div className="w-9 h-9 bg-gradient-to-br from-amber to-amber rounded-xl flex items-center justify-center shadow-lg shadow-amber/30 flex-shrink-0">
              <Zap className="w-5 h-5 text-ink" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <span className="text-lg font-bold text-ink drop-shadow-sm whitespace-nowrap">
                  Agency OS
                </span>
              </div>
            )}
          </div>
        )}
        
        {/* Collapse Toggle Button */}
        <button
          onClick={toggleCollapsed}
          className={`
            absolute -right-3 top-1/2 -translate-y-1/2
            w-6 h-6 rounded-full
            bg-panel border border-white/20
            flex items-center justify-center
            text-ink-2 hover:text-ink hover:bg-slate-700
            transition-all duration-200
            shadow-lg
            z-50
          `}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>
      </div>

      {/* Nav Items */}
      <nav className={`flex-1 ${collapsed ? "p-2" : "p-3"} space-y-1 overflow-y-auto`}>
        {navItems.map((item) => (
          <Link
            key={item.key}
            href={item.href}
            onClick={() => handleNavClick(item.key)}
            title={collapsed ? item.label : undefined}
            className={`
              w-full flex items-center relative
              ${collapsed ? "justify-center px-2" : "gap-3 px-3"} 
              py-2.5 rounded-lg text-sm font-medium 
              transition-all duration-200 transform
              ${activePage === item.key
                ? "bg-panel/80 text-ink shadow-lg shadow-amber/30 scale-100 backdrop-blur-sm"
                : clickedItem === item.key
                ? "bg-panel/60 text-ink scale-95"
                : "text-ink-2 hover:text-ink hover:bg-bg-panel/10 hover:scale-[1.02] active:scale-95"
              }
            `}
          >
            <item.icon
              className={`w-5 h-5 flex-shrink-0 transition-transform duration-200 ${
                clickedItem === item.key ? "rotate-12" : ""
              }`}
            />
            {!collapsed && (
              <>
                <span className="flex-1 text-left truncate">{item.label}</span>
                {item.badge && (
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs transition-all duration-200 ${
                      activePage === item.key
                        ? "bg-panel/50 text-ink"
                        : "bg-bg-panel/10 text-ink-2 border border-white/10"
                    } ${clickedItem === item.key ? "scale-110" : ""}`}
                  >
                    {item.badge}
                  </span>
                )}
              </>
            )}
            {/* Badge indicator when collapsed */}
            {collapsed && item.badge && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-panel rounded-full" />
            )}
          </Link>
        ))}
      </nav>

      {/* User */}
      <div className="p-3 border-t border-white/10">
        <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3 px-2"} py-2`}>
          {user.avatarUrl ? (
            <img 
              src={user.avatarUrl} 
              alt={user.name}
              className="w-9 h-9 rounded-full object-cover flex-shrink-0 ring-2 ring-white/20"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-amber to-emerald-600 flex items-center justify-center text-ink text-sm font-bold shadow-lg shadow-amber/30 flex-shrink-0">
              {user.initial ?? user.name.charAt(0).toUpperCase()}
            </div>
          )}
          {!collapsed && (
            <div className="flex-1 min-w-0 overflow-hidden">
              <p className="text-sm font-medium text-ink truncate">{user.name}</p>
              {user.plan && (
                <p className="text-xs text-ink-2 truncate">{user.plan}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
