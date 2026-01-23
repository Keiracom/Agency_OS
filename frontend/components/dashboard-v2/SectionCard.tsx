/**
 * Section Card - Container for dashboard sections
 * Open in Codux to adjust padding, borders
 */

"use client";

import { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  action?: { label: string; onClick: () => void };
  badge?: { label: string; variant?: "live" | "count" };
  children: ReactNode;
  className?: string;
}

export function SectionCard({ title, action, badge, children, className = "" }: SectionCardProps) {
  return (
    <div className={`bg-white rounded-xl border border-[#E2E8F0] shadow-sm ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#E2E8F0]">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
            {title}
          </h2>
          {badge && (
            <span className={`
              px-2 py-0.5 rounded-full text-xs font-medium
              ${badge.variant === "live"
                ? "bg-[#D1FAE5] text-[#047857] animate-pulse"
                : "bg-[#F1F5F9] text-[#64748B]"
              }
            `}>
              {badge.variant === "live" && (
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#10B981] mr-1.5" />
              )}
              {badge.label}
            </span>
          )}
        </div>
        {action && (
          <button
            onClick={action.onClick}
            className="text-sm font-medium text-[#3B82F6] hover:text-[#2563EB] transition-colors"
          >
            {action.label}
          </button>
        )}
      </div>

      {/* Content */}
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}

export default SectionCard;
