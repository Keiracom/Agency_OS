/**
 * FILE: frontend/components/plasmic/Header.tsx
 * PURPOSE: Dashboard header with search, notifications, profile
 * DESIGN: White header bar with subtle border
 */

"use client";

import { cn } from "@/lib/utils";
import { Bell, Search, ChevronDown, User } from "lucide-react";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  className?: string;
  title?: string;
  clientName?: string;
}

export function Header({ className, title = "Dashboard", clientName = "Acme Agency" }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const notificationCount = 3; // TODO: Hook up to real notifications

  return (
    <header
      className={cn(
        "sticky top-0 z-30 flex h-16 items-center justify-between",
        "bg-white border-b border-[#E5E7EB] px-6",
        className
      )}
    >
      {/* Left: Page Title */}
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-[#1F2937]">{title}</h1>
      </div>

      {/* Center: Search */}
      <div className="hidden md:flex flex-1 max-w-md mx-8">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#9CA3AF]" />
          <Input
            type="search"
            placeholder="Search leads, campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 bg-[#F5F7FA] border-0 focus:ring-2 focus:ring-[#2196F3]/20"
          />
        </div>
      </div>

      {/* Right: Notifications + Profile */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="h-5 w-5 text-[#6B7280]" />
              {notificationCount > 0 && (
                <Badge
                  className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 bg-[#EF4444] text-white text-xs"
                >
                  {notificationCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <div className="px-4 py-3 border-b">
              <p className="text-sm font-medium">Notifications</p>
            </div>
            <DropdownMenuItem className="px-4 py-3">
              <div>
                <p className="text-sm font-medium">New meeting booked</p>
                <p className="text-xs text-muted-foreground">Sarah Chen - 2 min ago</p>
              </div>
            </DropdownMenuItem>
            <DropdownMenuItem className="px-4 py-3">
              <div>
                <p className="text-sm font-medium">Reply received</p>
                <p className="text-xs text-muted-foreground">Mike Johnson - 15 min ago</p>
              </div>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="justify-center text-[#2196F3]">
              View all notifications
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Profile Dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 px-2">
              <div className="h-8 w-8 rounded-full bg-[#2196F3] flex items-center justify-center">
                <User className="h-4 w-4 text-white" />
              </div>
              <span className="hidden md:block text-sm font-medium text-[#1F2937]">
                {clientName}
              </span>
              <ChevronDown className="h-4 w-4 text-[#6B7280]" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <div className="px-4 py-3 border-b">
              <p className="text-sm font-medium">{clientName}</p>
              <p className="text-xs text-muted-foreground">Growth Plan</p>
            </div>
            <DropdownMenuItem>Account Settings</DropdownMenuItem>
            <DropdownMenuItem>Billing</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-red-600">Sign out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

export default Header;
