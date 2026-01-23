"use client";

import { Search, Bell, ChevronDown } from "lucide-react";

/**
 * Header props
 */
export interface HeaderProps {
  /** Page title displayed in the header */
  title: string;
  /** Notification count for the badge */
  notificationCount?: number;
  /** User/agency name */
  userName?: string;
  /** User avatar URL (optional, uses initials if not provided) */
  avatarUrl?: string;
}

/**
 * Header - White header bar component
 *
 * Features:
 * - Page title
 * - Search bar (placeholder)
 * - Notification bell with badge
 * - User avatar with name
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Background: #FFFFFF (card-bg)
 * - Border: #E2E8F0 (card-border)
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 * - Accent: #3B82F6
 */
export function Header({
  title,
  notificationCount = 3,
  userName = "Acme Agency",
  avatarUrl,
}: HeaderProps) {
  // Get initials from user name for avatar fallback
  const initials = userName
    .split(" ")
    .map((word) => word[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <header className="h-16 bg-white border-b border-[#E2E8F0] flex items-center justify-between px-6">
      {/* Page Title */}
      <h1 className="text-2xl font-semibold text-[#1E293B]">{title}</h1>

      {/* Right Section */}
      <div className="flex items-center gap-4">
        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#94A3B8]" />
          <input
            type="text"
            placeholder="Search leads, campaigns..."
            className="w-64 pl-10 pr-4 py-2 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg text-sm text-[#1E293B] placeholder-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6] focus:border-transparent transition-all"
          />
        </div>

        {/* Notification Bell */}
        <button className="relative p-2 text-[#64748B] hover:text-[#1E293B] hover:bg-[#F8FAFC] rounded-lg transition-colors">
          <Bell className="h-5 w-5" />
          {notificationCount > 0 && (
            <span className="absolute top-1 right-1 min-w-[18px] h-[18px] flex items-center justify-center px-1 bg-[#EF4444] text-white text-[10px] font-bold rounded-full">
              {notificationCount > 99 ? "99+" : notificationCount}
            </span>
          )}
        </button>

        {/* Divider */}
        <div className="h-8 w-px bg-[#E2E8F0]" />

        {/* User Profile */}
        <button className="flex items-center gap-3 p-2 hover:bg-[#F8FAFC] rounded-lg transition-colors">
          {/* Avatar */}
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt={userName}
              className="w-8 h-8 rounded-full object-cover"
            />
          ) : (
            <div className="w-8 h-8 bg-[#3B82F6] rounded-full flex items-center justify-center">
              <span className="text-xs font-semibold text-white">{initials}</span>
            </div>
          )}
          {/* Name */}
          <span className="text-sm font-medium text-[#1E293B]">{userName}</span>
          <ChevronDown className="h-4 w-4 text-[#94A3B8]" />
        </button>
      </div>
    </header>
  );
}

export default Header;
