/**
 * FILE: frontend/components/layout/header.tsx
 * PURPOSE: Dashboard header with page title, live badge, and user menu
 * PHASE: 8 (Frontend)
 * TASK: FE-004
 * UPDATED: Sprint 1 - Ported styling from HTML prototype (dashboard-v3.html)
 */

"use client";

import { useState } from "react";
import { Bell, Search, LogOut, User, Settings, Menu } from "lucide-react";
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
import { ThemeToggle } from "./theme-toggle";
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
  /** Mobile hamburger callback — wired by DashboardLayout to open the
   *  off-canvas Sidebar drawer. Button is visible only on <md viewports. */
  onOpenMenu?: () => void;
}

export function Header({ title = "Dashboard", user, client, onOpenMenu }: HeaderProps) {
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
    <header
      className="hidden md:flex sticky top-0 z-40 h-topbar items-center justify-between border-b border-rule px-6"
      style={{
        // Cream + blur (matches prototype #topbar but on cream backdrop)
        backgroundColor: "rgba(247, 243, 238, 0.85)",
        backdropFilter: "saturate(140%) blur(8px)",
        WebkitBackdropFilter: "saturate(140%) blur(8px)",
      }}
    >
      {/* Left: hamburger (mobile only) + Page title with LIVE badge */}
      <div className="flex items-center gap-3 md:gap-4">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-label="Open navigation"
          className="md:hidden -ml-2 p-2 rounded-md text-ink hover:bg-rule transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
        <h1 className="font-display font-bold text-[18px] md:text-[20px] tracking-[-0.01em] text-ink truncate">
          {title}
        </h1>

        {/* LIVE Status Badge — muted green on cream. Hidden on small
            screens to save room for the title + hamburger. */}
        <div
          className="hidden sm:flex items-center gap-2 rounded-full px-3 py-1"
          style={{ backgroundColor: "rgba(107,142,90,0.16)" }}
        >
          <span className="relative flex h-2 w-2">
            <span
              className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75"
              style={{ backgroundColor: "var(--green)" }}
            />
            <span
              className="relative inline-flex h-2 w-2 rounded-full"
              style={{ backgroundColor: "var(--green)" }}
            />
          </span>
          <span className="font-mono text-[10px] tracking-[0.1em] uppercase text-green">
            Live
          </span>
        </div>
      </div>

      {/* Center: Search */}
      <div className="hidden flex-1 justify-center md:flex">
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-3" />
          <Input
            placeholder="Search campaigns, leads…"
            className="w-full border-rule bg-panel pl-9 text-ink placeholder:text-ink-3"
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

        {/* Theme toggle (sun ↔ moon) — A2 dark-mode dispatch */}
        <ThemeToggle />

        {/* Credits Badge */}
        <div className="hidden md:block">
          <CreditsBadge />
        </div>

        {/* Notifications */}
        <Button 
          variant="ghost" 
          size="icon" 
          className="relative text-ink-2 hover:bg-panel hover:text-ink"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-status-error text-[10px] font-medium text-ink">
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
            className="w-56 border-rule bg-bg-panel" 
            align="end" 
            forceMount
          >
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none text-ink">
                  {displayName}
                </p>
                <p className="text-xs leading-none text-ink-3">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-border-subtle" />
            {client && (
              <>
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-xs text-ink-3">Organization</p>
                    <p className="text-sm font-medium text-ink">{client.name}</p>
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
            <DropdownMenuItem className="text-ink-2 hover:bg-panel hover:text-ink">
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem className="text-ink-2 hover:bg-panel hover:text-ink">
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
