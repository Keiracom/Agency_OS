/**
 * FILE: frontend/components/plasmic/MeetingItem.tsx
 * PURPOSE: Meeting list item - Plasmic design spec
 * DESIGN: Date/time + name/company + type badge
 */

"use client";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

type MeetingType = "discovery" | "demo" | "follow_up";

interface MeetingItemProps {
  leadName: string;
  company?: string;
  scheduledAt: string; // Formatted like "Today 2:00 PM"
  meetingType: MeetingType;
  duration?: number; // minutes
  className?: string;
}

const typeConfig: Record<MeetingType, { label: string; bg: string; text: string }> = {
  discovery: { label: "Discovery", bg: "bg-[#DBEAFE]", text: "text-[#1D4ED8]" },
  demo: { label: "Demo", bg: "bg-[#D1FAE5]", text: "text-[#047857]" },
  follow_up: { label: "Follow-up", bg: "bg-[#FEF3C7]", text: "text-[#B45309]" },
};

export function MeetingItem({
  leadName,
  company,
  scheduledAt,
  meetingType,
  duration = 30,
  className,
}: MeetingItemProps) {
  const config = typeConfig[meetingType];

  // Parse scheduledAt into day and time parts
  const [dayPart, timePart] = scheduledAt.includes(" ")
    ? [scheduledAt.split(" ")[0], scheduledAt.split(" ").slice(1).join(" ")]
    : ["", scheduledAt];

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3 rounded-lg",
        "hover:bg-white/5 transition-colors",
        className
      )}
    >
      {/* Date/Time */}
      <div className="w-20 shrink-0">
        <p className="text-xs text-white/40">{dayPart}</p>
        <p className="text-sm font-medium text-white">{timePart}</p>
      </div>

      {/* Divider */}
      <div className="w-px h-10 bg-white/10" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-white truncate">{leadName}</p>
        {company && (
          <p className="text-sm text-white/50 truncate">{company}</p>
        )}
      </div>

      {/* Type Badge + Duration */}
      <div className="flex flex-col items-end gap-1">
        <Badge className={cn("text-xs font-medium", config.bg, config.text)}>
          {config.label}
        </Badge>
        <span className="text-xs text-white/40">{duration} min</span>
      </div>
    </div>
  );
}

export default MeetingItem;
