/**
 * UserDropdown.tsx - User Profile Dropdown Menu
 * Phase: Operation Modular Cockpit
 * 
 * Glassmorphic user dropdown with avatar, profile info, and navigation.
 * Bloomberg dark mode styling with Supabase auth integration.
 */

"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import * as Avatar from "@radix-ui/react-avatar";
import {
  User,
  Settings,
  CreditCard,
  HelpCircle,
  LogOut,
  ChevronDown,
  ExternalLink,
  Sparkles,
} from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";

// ============================================
// Types
// ============================================

export interface UserData {
  id?: string;
  name: string;
  email?: string;
  avatarUrl?: string;
  tier?: "ignition" | "velocity" | "dominance";
}

export interface UserDropdownProps {
  /** User information to display */
  user?: UserData;
  /** Callback when profile is clicked */
  onProfileClick?: () => void;
  /** Callback when settings is clicked */
  onSettingsClick?: () => void;
  /** Callback when billing is clicked */
  onBillingClick?: () => void;
  /** Callback when help is clicked */
  onHelpClick?: () => void;
  /** Callback when sign out is clicked (overrides default Supabase logout) */
  onSignOut?: () => void;
  /** Whether sign out is in progress */
  isSigningOut?: boolean;
  /** Custom className for the trigger button */
  className?: string;
  /** Compact mode - just avatar, no name */
  compact?: boolean;
}

// ============================================
// Tier Badge Component
// ============================================

function TierIndicator({ tier }: { tier?: UserData["tier"] }) {
  if (!tier) return null;

  const tierConfig = {
    ignition: {
      label: "Ignition",
      gradient: "from-orange-500 to-amber-500",
      glow: "shadow-orange-500/20",
    },
    velocity: {
      label: "Velocity",
      gradient: "from-amber to-amber",
      glow: "shadow-amber/20",
    },
    dominance: {
      label: "Dominance",
      gradient: "from-amber to-amber-light",
      glow: "shadow-amber/20",
    },
  };

  const config = tierConfig[tier];

  return (
    <div
      className={`
        inline-flex items-center gap-1 px-2 py-0.5
        bg-gradient-to-r ${config.gradient}
        rounded-full text-[10px] font-semibold text-text-primary
        shadow-lg ${config.glow}
      `}
    >
      <Sparkles className="w-2.5 h-2.5" />
      {config.label}
    </div>
  );
}

// ============================================
// Menu Item Component
// ============================================

interface MenuItemProps {
  icon: React.ElementType;
  label: string;
  onClick?: () => void;
  href?: string;
  external?: boolean;
  danger?: boolean;
  disabled?: boolean;
}

function MenuItem({
  icon: Icon,
  label,
  onClick,
  href,
  external,
  danger,
  disabled,
}: MenuItemProps) {
  const content = (
    <>
      <Icon className="w-4 h-4" />
      <span className="flex-1">{label}</span>
      {external && <ExternalLink className="w-3 h-3 opacity-50" />}
    </>
  );

  const className = `
    flex items-center gap-3 w-full px-3 py-2.5
    text-sm font-medium rounded-lg
    transition-all duration-150 outline-none
    ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
    ${danger
      ? "text-amber hover:bg-amber-glow focus:bg-amber-glow"
      : "text-text-secondary hover:text-text-primary hover:bg-bg-surface/5 focus:bg-bg-surface/5"
    }
  `;

  if (href && !disabled) {
    return (
      <DropdownMenu.Item asChild>
        <a
          href={href}
          target={external ? "_blank" : undefined}
          rel={external ? "noopener noreferrer" : undefined}
          className={className}
        >
          {content}
        </a>
      </DropdownMenu.Item>
    );
  }

  return (
    <DropdownMenu.Item
      className={className}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
    >
      {content}
    </DropdownMenu.Item>
  );
}

// ============================================
// Main Component
// ============================================

export function UserDropdown({
  user,
  onProfileClick,
  onSettingsClick,
  onBillingClick,
  onHelpClick,
  onSignOut,
  isSigningOut = false,
  className = "",
  compact = false,
}: UserDropdownProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  // Derived values
  const displayName = user?.name ?? "User";
  const displayEmail = user?.email;
  const initial = displayName.charAt(0).toUpperCase();
  const isLoading = isSigningOut || signingOut;

  // Default handlers
  const handleProfileClick = useCallback(() => {
    if (onProfileClick) {
      onProfileClick();
    } else {
      router.push("/dashboard/profile");
    }
    setOpen(false);
  }, [onProfileClick, router]);

  const handleSettingsClick = useCallback(() => {
    if (onSettingsClick) {
      onSettingsClick();
    } else {
      router.push("/dashboard/settings");
    }
    setOpen(false);
  }, [onSettingsClick, router]);

  const handleBillingClick = useCallback(() => {
    if (onBillingClick) {
      onBillingClick();
    } else {
      router.push("/dashboard/billing");
    }
    setOpen(false);
  }, [onBillingClick, router]);

  const handleHelpClick = useCallback(() => {
    if (onHelpClick) {
      onHelpClick();
    } else {
      // Open help docs in new tab
      window.open("https://docs.agency-os.com", "_blank");
    }
    setOpen(false);
  }, [onHelpClick]);

  const handleSignOut = useCallback(async () => {
    if (onSignOut) {
      onSignOut();
      setOpen(false);
      return;
    }

    // Default: Supabase sign out
    setSigningOut(true);
    try {
      const supabase = createBrowserClient();
      await supabase.auth.signOut();
      router.push("/auth/login");
      router.refresh();
    } catch (error) {
      console.error("Sign out error:", error);
      setSigningOut(false);
    }
  }, [onSignOut, router]);

  return (
    <DropdownMenu.Root open={open} onOpenChange={setOpen}>
      <DropdownMenu.Trigger asChild>
        <button
          className={`
            flex items-center gap-2
            ${compact ? "p-1" : "pl-1 pr-2.5 py-1"}
            bg-bg-surface/5 backdrop-blur-xl
            border border-white/10 hover:border-white/20
            rounded-xl
            hover:bg-bg-surface/10
            transition-all duration-200
            outline-none focus:ring-2 focus:ring-amber/40
            ${open ? "bg-bg-surface/10 border-white/20" : ""}
            ${className}
          `}
          aria-label="User menu"
        >
          {/* Avatar */}
          <Avatar.Root className="relative w-8 h-8 rounded-lg overflow-hidden">
            <Avatar.Image
              src={user?.avatarUrl}
              alt={displayName}
              className="w-full h-full object-cover"
            />
            <Avatar.Fallback
              className="
                w-full h-full flex items-center justify-center
                bg-gradient-to-br from-amber to-amber
                text-text-primary text-sm font-semibold
              "
              delayMs={100}
            >
              {initial}
            </Avatar.Fallback>
          </Avatar.Root>

          {/* Name (hidden in compact mode) */}
          {!compact && (
            <span className="text-sm font-medium text-text-primary hidden sm:block max-w-24 truncate">
              {displayName}
            </span>
          )}

          {/* Chevron */}
          <ChevronDown
            className={`
              w-4 h-4 text-text-secondary
              transition-transform duration-200
              ${open ? "rotate-180" : ""}
            `}
          />
        </button>
      </DropdownMenu.Trigger>

      <AnimatePresence>
        {open && (
          <DropdownMenu.Portal forceMount>
            <DropdownMenu.Content
              asChild
              sideOffset={8}
              align="end"
              className="z-50"
            >
              <motion.div
                initial={{ opacity: 0, y: -8, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -8, scale: 0.96 }}
                transition={{ duration: 0.15, ease: "easeOut" }}
                className="
                  w-64
                  bg-bg-void/95 backdrop-blur-xl
                  border border-white/10
                  rounded-xl shadow-2xl shadow-black/40
                  overflow-hidden
                "
              >
                {/* User Info Header */}
                <div className="px-4 py-4 border-b border-white/10 bg-gradient-to-br from-white/5 to-transparent">
                  <div className="flex items-start gap-3">
                    <Avatar.Root className="relative w-12 h-12 rounded-xl overflow-hidden ring-2 ring-white/10">
                      <Avatar.Image
                        src={user?.avatarUrl}
                        alt={displayName}
                        className="w-full h-full object-cover"
                      />
                      <Avatar.Fallback
                        className="
                          w-full h-full flex items-center justify-center
                          bg-gradient-to-br from-amber to-amber
                          text-text-primary text-lg font-semibold
                        "
                        delayMs={100}
                      >
                        {initial}
                      </Avatar.Fallback>
                    </Avatar.Root>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-text-primary truncate">
                        {displayName}
                      </p>
                      {displayEmail && (
                        <p className="text-xs text-text-secondary truncate mt-0.5">
                          {displayEmail}
                        </p>
                      )}
                      {user?.tier && (
                        <div className="mt-2">
                          <TierIndicator tier={user.tier} />
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Menu Items */}
                <div className="p-2">
                  <MenuItem
                    icon={User}
                    label="Profile"
                    onClick={handleProfileClick}
                  />
                  <MenuItem
                    icon={Settings}
                    label="Settings"
                    onClick={handleSettingsClick}
                  />
                  <MenuItem
                    icon={CreditCard}
                    label="Billing"
                    onClick={handleBillingClick}
                  />

                  <DropdownMenu.Separator className="my-2 h-px bg-bg-surface/10" />

                  <MenuItem
                    icon={HelpCircle}
                    label="Help & Support"
                    onClick={handleHelpClick}
                    external
                  />

                  <DropdownMenu.Separator className="my-2 h-px bg-bg-surface/10" />

                  <MenuItem
                    icon={LogOut}
                    label={isLoading ? "Signing out..." : "Sign Out"}
                    onClick={handleSignOut}
                    danger
                    disabled={isLoading}
                  />
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
