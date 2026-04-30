/**
 * Header.tsx - Dashboard Header Component
 * Phase: Operation Modular Cockpit
 * 
 * Global header with search, credits, notifications, and user dropdown.
 * Bloomberg dark mode styling with glassmorphic effects.
 */

"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import {
  Search,
  Bell,
  ChevronDown,
  CreditCard,
  Coins,
  LogOut,
  User,
  Settings,
  HelpCircle,
  X,
  Zap,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

// ============================================
// Types
// ============================================

export interface Notification {
  id: string;
  title: string;
  message: string;
  time: string;
  read: boolean;
  type: "info" | "success" | "warning" | "error";
}

export interface UserMenuAction {
  key: string;
  label: string;
  icon: LucideIcon;
  onClick?: () => void;
  href?: string;
  danger?: boolean;
  divider?: boolean;
}

export interface HeaderProps {
  /** Current search value (deprecated - use GlobalSearch) */
  searchValue?: string;
  /** Search change handler (deprecated - use GlobalSearch) */
  onSearchChange?: (value: string) => void;
  /** Search submit handler (deprecated - use GlobalSearch) */
  onSearchSubmit?: (value: string) => void;
  /** Search placeholder */
  searchPlaceholder?: string;
  /** Handler to open global search modal */
  onGlobalSearchOpen?: () => void;
  /** Credits remaining */
  credits?: number;
  /** Max credits for display */
  maxCredits?: number;
  /** Credits label */
  creditsLabel?: string;
  /** Notifications list */
  notifications?: Notification[];
  /** Notification click handler */
  onNotificationClick?: (notification: Notification) => void;
  /** Mark all notifications read */
  onMarkAllRead?: () => void;
  /** User info */
  user?: {
    name: string;
    email?: string;
    avatarUrl?: string;
    initial?: string;
  };
  /** Custom menu actions */
  menuActions?: UserMenuAction[];
  /** Logout handler */
  onLogout?: () => void;
  /** Settings click handler */
  onSettingsClick?: () => void;
  /** Profile click handler */
  onProfileClick?: () => void;
  /** Whether sidebar is collapsed (to adjust left margin) */
  sidebarCollapsed?: boolean;
  /** Custom className */
  className?: string;
}

// ============================================
// Default Menu Actions
// ============================================

const getDefaultMenuActions = (
  onProfileClick?: () => void,
  onSettingsClick?: () => void,
  onLogout?: () => void
): UserMenuAction[] => [
  { key: "profile", label: "Profile", icon: User, onClick: onProfileClick },
  { key: "settings", label: "Settings", icon: Settings, onClick: onSettingsClick },
  { key: "help", label: "Help & Support", icon: HelpCircle, divider: true },
  { key: "logout", label: "Sign Out", icon: LogOut, onClick: onLogout, danger: true },
];

// ============================================
// Sub-components
// ============================================

function SearchTrigger({
  onOpen,
  placeholder = "Search leads, campaigns, reports...",
}: {
  onOpen: () => void;
  placeholder?: string;
}) {
  return (
    <button
      onClick={onOpen}
      className="
        relative flex items-center gap-2 w-64
        bg-bg-panel/5 backdrop-blur-xl
        border border-white/10 hover:border-white/20
        rounded-xl px-3 py-2.5
        transition-all duration-200
        hover:bg-bg-panel/10 hover:w-72
        group
      "
    >
      <Search className="w-4 h-4 text-ink-2 group-hover:text-ink-2" />
      <span className="text-sm text-ink-3 group-hover:text-ink-2 flex-1 text-left truncate">
        {placeholder}
      </span>
      <kbd className="hidden sm:flex items-center gap-1 text-[10px] text-ink-3 bg-bg-panel/5 px-1.5 py-0.5 rounded border border-white/10">
        <span className="text-xs">⌘</span>K
      </kbd>
    </button>
  );
}

function CreditsDisplay({
  credits = 0,
  maxCredits = 10000,
  label = "Credits",
}: {
  credits?: number;
  maxCredits?: number;
  label?: string;
}) {
  const percentage = Math.min((credits / maxCredits) * 100, 100);
  const isLow = percentage < 20;
  const isMedium = percentage >= 20 && percentage < 50;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-bg-panel/5 backdrop-blur-xl rounded-xl border border-white/10">
      <div className={`p-1.5 rounded-lg ${isLow ? "bg-amber/20" : isMedium ? "bg-amber-500/20" : "bg-amber/20"}`}>
        <Coins className={`w-4 h-4 ${isLow ? "text-amber" : isMedium ? "text-amber-400" : "text-amber"}`} />
      </div>
      <div className="flex flex-col">
        <span className="text-xs text-ink-2">{label}</span>
        <span className={`text-sm font-semibold ${isLow ? "text-amber" : isMedium ? "text-amber-400" : "text-ink"}`}>
          {credits.toLocaleString()}
        </span>
      </div>
    </div>
  );
}

function NotificationBell({
  notifications = [],
  onNotificationClick,
  onMarkAllRead,
}: {
  notifications?: Notification[];
  onNotificationClick?: (n: Notification) => void;
  onMarkAllRead?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const unreadCount = notifications.filter((n) => !n.read).length;

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const typeStyles = {
    info: "bg-bg-elevated/20 text-ink-2",
    success: "bg-amber/20 text-amber",
    warning: "bg-amber-500/20 text-amber-400",
    error: "bg-amber/20 text-amber",
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`
          relative p-2.5 rounded-xl
          bg-bg-panel/5 backdrop-blur-xl border border-white/10
          text-ink-2 hover:text-ink hover:bg-bg-panel/10
          transition-all duration-200
          ${open ? "bg-bg-panel/10 text-ink" : ""}
        `}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber rounded-full flex items-center justify-center text-[10px] font-bold text-ink animate-pulse">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-bg-cream/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <h3 className="text-sm font-semibold text-ink">Notifications</h3>
            {unreadCount > 0 && onMarkAllRead && (
              <button
                onClick={() => {
                  onMarkAllRead();
                  setOpen(false);
                }}
                className="text-xs text-ink-2 hover:text-amber-light transition-colors"
              >
                Mark all read
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <Bell className="w-8 h-8 text-ink-3 mx-auto mb-2" />
                <p className="text-sm text-ink-3">No notifications</p>
              </div>
            ) : (
              notifications.map((notification) => (
                <button
                  key={notification.id}
                  onClick={() => {
                    onNotificationClick?.(notification);
                    setOpen(false);
                  }}
                  className={`
                    w-full px-4 py-3 text-left
                    hover:bg-bg-panel/5 transition-colors
                    border-b border-white/5 last:border-0
                    ${!notification.read ? "bg-bg-elevated/5" : ""}
                  `}
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-1.5 rounded-lg mt-0.5 ${typeStyles[notification.type]}`}>
                      <Sparkles className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium truncate ${!notification.read ? "text-ink" : "text-ink-2"}`}>
                        {notification.title}
                      </p>
                      <p className="text-xs text-ink-3 truncate mt-0.5">
                        {notification.message}
                      </p>
                      <p className="text-[10px] text-ink-3 mt-1">
                        {notification.time}
                      </p>
                    </div>
                    {!notification.read && (
                      <div className="w-2 h-2 bg-bg-elevated rounded-full mt-2" />
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function UserDropdown({
  user,
  menuActions,
}: {
  user?: HeaderProps["user"];
  menuActions: UserMenuAction[];
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const displayName = user?.name ?? "User";
  const displayEmail = user?.email;
  const initial = user?.initial ?? displayName.charAt(0).toUpperCase();

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`
          flex items-center gap-2 pl-1 pr-2 py-1
          bg-bg-panel/5 backdrop-blur-xl border border-white/10
          rounded-xl
          hover:bg-bg-panel/10 transition-all duration-200
          ${open ? "bg-bg-panel/10" : ""}
        `}
      >
        {user?.avatarUrl ? (
          <img
            src={user.avatarUrl}
            alt={displayName}
            className="w-8 h-8 rounded-lg object-cover"
          />
        ) : (
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber to-amber flex items-center justify-center text-ink text-sm font-semibold">
            {initial}
          </div>
        )}
        <span className="text-sm font-medium text-ink hidden sm:block max-w-24 truncate">
          {displayName}
        </span>
        <ChevronDown className={`w-4 h-4 text-ink-2 transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-bg-cream/95 backdrop-blur-xl border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50">
          {/* User Info Header */}
          <div className="px-4 py-3 border-b border-white/10">
            <p className="text-sm font-medium text-ink truncate">{displayName}</p>
            {displayEmail && (
              <p className="text-xs text-ink-2 truncate">{displayEmail}</p>
            )}
          </div>

          {/* Menu Items */}
          <div className="py-1">
            {menuActions.map((action, idx) => (
              <div key={action.key}>
                {action.divider && idx > 0 && (
                  <div className="my-1 border-t border-white/10" />
                )}
                <button
                  onClick={() => {
                    action.onClick?.();
                    setOpen(false);
                  }}
                  className={`
                    w-full flex items-center gap-3 px-4 py-2.5
                    text-sm transition-colors
                    ${action.danger
                      ? "text-amber hover:bg-amber-glow"
                      : "text-ink-2 hover:text-ink hover:bg-bg-panel/5"
                    }
                  `}
                >
                  <action.icon className="w-4 h-4" />
                  <span>{action.label}</span>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function Header({
  searchValue: controlledSearchValue,
  onSearchChange,
  onSearchSubmit,
  searchPlaceholder = "Search leads, campaigns, reports...",
  onGlobalSearchOpen,
  credits,
  maxCredits = 10000,
  creditsLabel = "Credits",
  notifications = [],
  onNotificationClick,
  onMarkAllRead,
  user,
  menuActions,
  onLogout,
  onSettingsClick,
  onProfileClick,
  sidebarCollapsed = false,
  className = "",
}: HeaderProps) {
  // Merge custom menu actions with defaults
  const actions = menuActions ?? getDefaultMenuActions(onProfileClick, onSettingsClick, onLogout);

  // Fallback handler for global search open
  const handleSearchOpen = useCallback(() => {
    if (onGlobalSearchOpen) {
      onGlobalSearchOpen();
    } else {
      // Fallback: dispatch custom event for GlobalSearch hook to catch
      window.dispatchEvent(new CustomEvent("open-global-search"));
    }
  }, [onGlobalSearchOpen]);

  return (
    <header
      className={`
        fixed top-0 right-0 z-30
        ${sidebarCollapsed ? "left-[72px]" : "left-60"}
        h-16 px-6
        bg-slate-950/80 backdrop-blur-xl
        border-b border-white/10
        flex items-center justify-between gap-4
        transition-all duration-300
        ${className}
      `}
    >
      {/* Left: Search Trigger (opens GlobalSearch modal) */}
      <div className="flex-1 max-w-md">
        <SearchTrigger
          onOpen={handleSearchOpen}
          placeholder={searchPlaceholder}
        />
      </div>

      {/* Right: Credits, Notifications, User */}
      <div className="flex items-center gap-3">
        {credits !== undefined && (
          <CreditsDisplay
            credits={credits}
            maxCredits={maxCredits}
            label={creditsLabel}
          />
        )}
        
        <NotificationBell
          notifications={notifications}
          onNotificationClick={onNotificationClick}
          onMarkAllRead={onMarkAllRead}
        />
        
        <UserDropdown user={user} menuActions={actions} />
      </div>
    </header>
  );
}

export default Header;
