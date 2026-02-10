/**
 * FILE: frontend/components/layout/header.tsx
 * PURPOSE: Dashboard header with page title, live badge, and user menu
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 * UPDATED: Sprint 1 - Ported styling from HTML prototype (dashboard-v3.html)
 */

"use client";

import { useState } from "react";
import { Bell, Search, LogOut, User, Settings } from "lucide-react";
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
import { CreditsBadge } from "./credits-badge";
import { EmergencyPauseButton } from "@/components/dashboard/EmergencyPauseButton";

interface HeaderProps {
  title?: string;
  user?: {
    email: string;
    fullName?: string;
    avatarUrl?: string;
  };
  client?: {
    id: string;
    name: string;
    tier: string;
    creditsRemaining: number;
    pausedAt?: string | null;
    pauseReason?: string | null;
  };
}

export function Header({ title = "Dashboard", user, client }: HeaderProps) {
  const router = useRouter();
  const supabase = createBrowserClient();

  const [isPaused, setIsPaused] = useState(!!client?.pausedAt);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    router.push("/login");
  };

  const displayName = user?.fullName || user?.email || "User";
  const initials = getInitials(displayName);

  return (
    <header className="flex h-16 items-center justify-between border-b border-border-subtle bg-bg-surface px-6">
      {/* Left: Page title with LIVE badge */}
      <div className="flex items-center gap-4">
        <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
        
        {/* LIVE Status Badge */}
        <div className="flex items-center gap-2 rounded-full bg-status-success/10 px-3 py-1">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-status-success opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-status-success" />
          </span>
          <span className="text-xs font-medium text-status-success">LIVE</span>
        </div>
      </div>

      {/* Center: Search (placeholder for Sprint 1) */}
      <div className="hidden flex-1 justify-center md:flex">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <Input
            placeholder="Search campaigns, leads..."
            className="w-full border-border-subtle bg-bg-primary pl-9 text-text-primary placeholder:text-text-muted"
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* Emergency Pause Button */}
        {client?.id && (
          <EmergencyPauseButton
            clientId={client.id}
            isPaused={isPaused}
            pausedAt={client.pausedAt}
            pauseReason={client.pauseReason}
            onPauseChange={setIsPaused}
          />
        )}

        {/* Credits Badge */}
        <div className="hidden md:block">
          <CreditsBadge />
        </div>

        {/* Notifications */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="relative text-text-secondary hover:bg-bg-elevated hover:text-text-primary"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-status-error text-[10px] font-medium text-white">
            3
          </span>
        </Button>

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button 
              variant="ghost" 
              className="relative h-9 w-9 rounded-full ring-2 ring-border-subtle hover:ring-accent-primary"
            >
              <Avatar className="h-9 w-9">
                <AvatarImage src={user?.avatarUrl} alt={displayName} />
                <AvatarFallback className={getAvatarColor(displayName)}>
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent 
            className="w-56 border-border-subtle bg-bg-surface" 
            align="end" 
            forceMount
          >
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none text-text-primary">
                  {displayName}
                </p>
                <p className="text-xs leading-none text-text-muted">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-border-subtle" />
            {client && (
              <>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-xs text-text-muted">Organization</p>
                    <p className="text-sm font-medium text-text-primary">{client.name}</p>
                    <Badge 
                      variant="outline" 
                      className="mt-1 w-fit border-accent-primary/50 capitalize text-accent-primary"
                    >
                      {client.tier}
                    </Badge>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-border-subtle" />
              </>
            )}
            <DropdownMenuItem className="text-text-secondary hover:bg-bg-elevated hover:text-text-primary">
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem className="text-text-secondary hover:bg-bg-elevated hover:text-text-primary">
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-border-subtle" />
            <DropdownMenuItem 
              onClick={handleSignOut}
              className="text-status-error hover:bg-status-error/10 hover:text-status-error"
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
