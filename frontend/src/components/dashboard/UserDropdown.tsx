"use client";

/**
 * FILE: frontend/src/components/dashboard/UserDropdown.tsx
 * PURPOSE: User profile dropdown for header navigation
 * PHASE: 8 (Frontend)
 * FEATURES:
 *   - Avatar with initials/image
 *   - User name and email display
 *   - Menu items: Profile, Settings, Billing, Help, Sign Out
 *   - Keyboard accessible (Radix UI)
 *   - Click outside to close
 *   - Bloomberg dark mode + glassmorphic styling
 */

import React from "react";
import { useRouter } from "next/navigation";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { motion, AnimatePresence } from "motion/react";
import {
  User,
  Settings,
  DollarSign,
  HelpCircle,
  LogOut,
  ChevronDown,
} from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";
import { cn, getInitials, getAvatarColor } from "@/lib/utils";

interface UserDropdownProps {
  user: {
    id: string;
    email: string;
    full_name?: string | null;
    avatar_url?: string | null;
  };
  className?: string;
}

interface MenuItem {
  label: string;
  icon: React.ReactNode;
  href?: string;
  onClick?: () => void;
  variant?: "default" | "danger";
}

export function UserDropdown({ user, className }: UserDropdownProps) {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [isSigningOut, setIsSigningOut] = React.useState(false);

  const displayName = user.full_name || user.email.split("@")[0];
  const initials = getInitials(displayName);
  const avatarColor = getAvatarColor(displayName);

  const handleSignOut = async () => {
    setIsSigningOut(true);
    try {
      const supabase = createBrowserClient();
      await supabase.auth.signOut();
      router.push("/login");
      router.refresh();
    } catch (error) {
      console.error("Sign out error:", error);
      setIsSigningOut(false);
    }
  };

  const menuItems: MenuItem[] = [
    {
      label: "Profile",
      icon: <User className="h-4 w-4" />,
      href: "/dashboard/profile",
    },
    {
      label: "Settings",
      icon: <Settings className="h-4 w-4" />,
      href: "/dashboard/settings",
    },
    {
      label: "Billing",
      icon: <DollarSign className="h-4 w-4" />,
      href: "/dashboard/billing",
    },
    {
      label: "Help",
      icon: <HelpCircle className="h-4 w-4" />,
      href: "/help",
    },
  ];

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger asChild>
        <button
          className={cn(
            "flex items-center gap-2 rounded-lg px-2 py-1.5",
            "transition-all duration-200 ease-out",
            "hover:bg-white/5 focus:bg-white/5",
            "focus:outline-none focus:ring-2 focus:ring-cyan-500/50",
            "border border-transparent hover:border-white/10",
            className
          )}
          aria-label="User menu"
        >
          {/* Avatar */}
          <div
            className={cn(
              "relative h-8 w-8 rounded-full flex items-center justify-center",
              "text-sm font-medium text-white",
              "ring-2 ring-white/20",
              user.avatar_url ? "" : avatarColor
            )}
          >
            {user.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={displayName}
                className="h-full w-full rounded-full object-cover"
              />
            ) : (
              <span>{initials}</span>
            )}
            {/* Online indicator */}
            <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-neutral-900" />
          </div>

          {/* Name (hidden on mobile) */}
          <span className="hidden sm:block text-sm font-medium text-neutral-200 max-w-[120px] truncate">
            {displayName}
          </span>

          {/* Chevron */}
          <ChevronDown
            className={cn(
              "h-4 w-4 text-neutral-400 transition-transform duration-200",
              open && "rotate-180"
            )}
          />
        </button>
      </DropdownMenu.Trigger>

      <AnimatePresence>
        {open && (
          <DropdownMenu.Portal forceMount>
            <DropdownMenu.Content
              align="end"
              sideOffset={8}
              asChild
            >
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
                className={cn(
                  "z-50 min-w-[220px] overflow-hidden rounded-xl",
                  // Glassmorphic styling
                  "bg-neutral-900/90 backdrop-blur-xl",
                  "border border-white/10",
                  "shadow-2xl shadow-black/50",
                  // Bloomberg dark mode accents
                  "ring-1 ring-inset ring-white/5"
                )}
              >
                {/* User Info Header */}
                <div className="px-3 py-3 border-b border-white/10">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "h-10 w-10 rounded-full flex items-center justify-center",
                        "text-sm font-semibold text-white",
                        user.avatar_url ? "" : avatarColor
                      )}
                    >
                      {user.avatar_url ? (
                        <img
                          src={user.avatar_url}
                          alt={displayName}
                          className="h-full w-full rounded-full object-cover"
                        />
                      ) : (
                        <span>{initials}</span>
                      )}
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-white truncate max-w-[150px]">
                        {displayName}
                      </span>
                      <span className="text-xs text-neutral-400 truncate max-w-[150px]">
                        {user.email}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="py-1.5">
                  {menuItems.map((item) => (
                    <DropdownMenu.Item key={item.label} asChild>
                      <a
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 mx-1.5 rounded-lg",
                          "text-sm text-neutral-300",
                          "cursor-pointer transition-colors duration-150",
                          "hover:bg-white/10 hover:text-white",
                          "focus:bg-white/10 focus:text-white focus:outline-none",
                          "data-[highlighted]:bg-white/10 data-[highlighted]:text-white"
                        )}
                      >
                        <span className="text-neutral-400 group-hover:text-neutral-300">
                          {item.icon}
                        </span>
                        {item.label}
                      </a>
                    </DropdownMenu.Item>
                  ))}
                </div>

                {/* Sign Out */}
                <div className="py-1.5 border-t border-white/10">
                  <DropdownMenu.Item asChild>
                    <button
                      onClick={handleSignOut}
                      disabled={isSigningOut}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 mx-1.5 rounded-lg w-[calc(100%-12px)]",
                        "text-sm text-red-400",
                        "cursor-pointer transition-colors duration-150",
                        "hover:bg-red-500/10 hover:text-red-300",
                        "focus:bg-red-500/10 focus:text-red-300 focus:outline-none",
                        "data-[highlighted]:bg-red-500/10 data-[highlighted]:text-red-300",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                      )}
                    >
                      <LogOut className="h-4 w-4" />
                      {isSigningOut ? "Signing out..." : "Sign Out"}
                    </button>
                  </DropdownMenu.Item>
                </div>
              </motion.div>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        )}
      </AnimatePresence>
    </DropdownMenu.Root>
  );
}

export default UserDropdown;
