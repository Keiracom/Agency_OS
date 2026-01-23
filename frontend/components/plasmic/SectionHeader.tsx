/**
 * FILE: frontend/components/plasmic/SectionHeader.tsx
 * PURPOSE: Section header with title and optional action
 * DESIGN: Uppercase label style with optional badge/button
 */

"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

interface SectionHeaderProps {
  title: string;
  action?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
  };
  badge?: {
    label: string;
    variant?: "live" | "count" | "status";
  };
  className?: string;
}

export function SectionHeader({ title, action, badge, className }: SectionHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between mb-4", className)}>
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-white/60 uppercase tracking-wider">
          {title}
        </h2>
        {badge && (
          <Badge
            className={cn(
              "text-xs",
              badge.variant === "live"
                ? "bg-[#10B981]/20 text-[#10B981] animate-pulse"
                : badge.variant === "count"
                ? "bg-white/10 text-white/60"
                : "bg-[#2196F3]/20 text-[#2196F3]"
            )}
          >
            {badge.variant === "live" && (
              <span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-[#10B981] inline-block" />
            )}
            {badge.label}
          </Badge>
        )}
      </div>
      {action && (
        <Button
          variant="ghost"
          size="sm"
          onClick={action.onClick}
          className="text-[#2196F3] hover:text-[#2196F3] hover:bg-[#2196F3]/10"
        >
          {action.icon || <Plus className="h-4 w-4 mr-1" />}
          {action.label}
        </Button>
      )}
    </div>
  );
}

export default SectionHeader;
