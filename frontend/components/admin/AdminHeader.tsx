/**
 * FILE: frontend/components/admin/AdminHeader.tsx
 * PURPOSE: Admin dashboard header with alerts and user menu
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Foundation
 */

"use client";

import { Bell, Search, LogOut, User, Settings, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { createBrowserClient } from "@/lib/supabase";
import { useRouter } from "next/navigation";
import { getInitials, getAvatarColor } from "@/lib/utils";

interface AdminHeaderProps {
  user?: {
    email: string;
    fullName?: string;
    avatarUrl?: string;
  };
  alertCount?: number;
}

export function AdminHeader({ user, alertCount = 0 }: AdminHeaderProps) {
  const router = useRouter();
  const supabase = createBrowserClient();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const displayName = user?.fullName || user?.email || "Admin";
  const initials = getInitials(displayName);

  return (
    <header className="flex h-16 items-center justify-between border-b bg-background px-6">
      {/* Left side - Admin badge and search */}
      <div className="flex items-center gap-4 flex-1">
        <Badge variant="destructive" className="flex items-center gap-1">
          <Shield className="h-3 w-3" />
          ADMIN
        </Badge>
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search clients, campaigns, leads..."
            className="pl-9"
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-4">
        {/* Last updated */}
        <span className="hidden md:inline text-xs text-muted-foreground">
          Last updated: {new Date().toLocaleTimeString()}
        </span>

        {/* Alerts */}
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {alertCount > 0 && (
            <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full">
              <Avatar>
                <AvatarImage src={user?.avatarUrl} alt={displayName} />
                <AvatarFallback className={getAvatarColor(displayName)}>
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{displayName}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user?.email}
                </p>
                <Badge variant="destructive" className="w-fit mt-1">
                  Platform Admin
                </Badge>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleSignOut}>
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
