"use client";

/**
 * Bloomberg-style Quick Actions
 * Matches: dashboard-v3.html quick-action design
 */

import Link from "next/link";
import { Zap, Users, Settings, LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface QuickAction {
  label: string;
  icon: LucideIcon;
  href: string;
}

const defaultActions: QuickAction[] = [
  { label: "Create Campaign", icon: Zap, href: "/dashboard/campaigns/new" },
  { label: "View Leads", icon: Users, href: "/dashboard/leads" },
  { label: "Settings", icon: Settings, href: "/dashboard/settings" },
];

interface QuickActionsProps {
  actions?: QuickAction[];
  className?: string;
}

export function QuickActions({ actions = defaultActions, className }: QuickActionsProps) {
  return (
    <div className={cn("bg-[#12121A] border border-[#2A2A3A] rounded-2xl", className)}>
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#2A2A3A]">
        <h3 className="font-semibold text-white">Quick Actions</h3>
      </div>

      {/* Actions */}
      <div className="p-4 space-y-2.5">
        {actions.map((action, index) => (
          <Link
            key={index}
            href={action.href}
            className="flex items-center gap-3 px-4 py-3.5 bg-[#1A1A24] border border-[#2A2A3A] rounded-xl cursor-pointer transition-all hover:border-[#7C3AED] hover:bg-[#7C3AED]/5 group"
          >
            <action.icon className="w-5 h-5 text-[#7C3AED]" />
            <span className="text-sm font-medium text-white group-hover:text-[#9D5CFF] transition-colors">
              {action.label}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
