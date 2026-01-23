/**
 * Header Bar - White with search and profile
 * Open in Codux to adjust layout and styling
 */

"use client";

import { Bell, Search, ChevronDown, User } from "lucide-react";

interface HeaderProps {
  title?: string;
}

export function Header({ title = "Dashboard" }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between bg-white border-b border-[#E2E8F0] px-6">
      {/* Page Title */}
      <h1 className="text-xl font-semibold text-[#1E293B]">{title}</h1>

      {/* Search Bar */}
      <div className="flex-1 max-w-md mx-8">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#94A3B8]" />
          <input
            type="search"
            placeholder="Search leads, campaigns..."
            className="w-full h-10 pl-10 pr-4 rounded-lg bg-[#F1F5F9] border-0 text-sm placeholder:text-[#94A3B8] focus:outline-none focus:ring-2 focus:ring-[#3B82F6]/20"
          />
        </div>
      </div>

      {/* Right Actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <button className="relative p-2 rounded-lg hover:bg-[#F1F5F9] transition-colors">
          <Bell className="h-5 w-5 text-[#64748B]" />
          <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-[#EF4444]" />
        </button>

        {/* Profile */}
        <button className="flex items-center gap-2 p-2 rounded-lg hover:bg-[#F1F5F9] transition-colors">
          <div className="h-8 w-8 rounded-full bg-[#3B82F6] flex items-center justify-center">
            <User className="h-4 w-4 text-white" />
          </div>
          <span className="text-sm font-medium text-[#1E293B]">Acme Agency</span>
          <ChevronDown className="h-4 w-4 text-[#64748B]" />
        </button>
      </div>
    </header>
  );
}

export default Header;
