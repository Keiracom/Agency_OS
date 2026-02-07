/**
 * ChannelIcon.tsx - Channel Type Icon Component
 * Phase: Operation Modular Cockpit
 * 
 * Displays channel-specific icons with appropriate colors.
 */

"use client";

import {
  Mail,
  Linkedin,
  MessageCircle,
  Phone,
  type LucideIcon,
} from "lucide-react";
import type { ChannelType } from "@/lib/api/types";

// ============================================
// Types
// ============================================

interface ChannelIconProps {
  channel: ChannelType | string;
  size?: "sm" | "md" | "lg";
  /** Show just the icon without background */
  bare?: boolean;
  /** Custom class name */
  className?: string;
}

// ============================================
// Configuration
// ============================================

const channelConfig: Record<string, { bg: string; icon: LucideIcon }> = {
  email: { bg: "bg-blue-100 text-blue-600", icon: Mail },
  linkedin: { bg: "bg-sky-100 text-sky-600", icon: Linkedin },
  sms: { bg: "bg-emerald-100 text-emerald-600", icon: MessageCircle },
  voice: { bg: "bg-purple-100 text-purple-600", icon: Phone },
  mail: { bg: "bg-amber-100 text-amber-600", icon: Mail }, // Physical mail
};

const sizeConfig = {
  sm: { container: "w-6 h-6", icon: "w-3 h-3" },
  md: { container: "w-8 h-8", icon: "w-4 h-4" },
  lg: { container: "w-10 h-10", icon: "w-5 h-5" },
};

// ============================================
// Component
// ============================================

export function ChannelIcon({
  channel,
  size = "sm",
  bare = false,
  className = "",
}: ChannelIconProps) {
  const config = channelConfig[channel.toLowerCase()] ?? channelConfig.email;
  const sizeClasses = sizeConfig[size];
  const Icon = config.icon;

  if (bare) {
    return <Icon className={`${sizeClasses.icon} ${className}`} />;
  }

  return (
    <div
      className={`${sizeClasses.container} rounded-full ${config.bg} flex items-center justify-center ${className}`}
    >
      <Icon className={sizeClasses.icon} />
    </div>
  );
}

export default ChannelIcon;
