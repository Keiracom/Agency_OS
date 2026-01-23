/**
 * Meeting Item - Shows upcoming meeting
 * Open in Codux to adjust badge colors, layout
 */

"use client";

type MeetingType = "discovery" | "demo" | "follow_up";

interface MeetingItemProps {
  name: string;
  company?: string;
  time: string;
  day: string;
  type: MeetingType;
  duration?: number;
}

const typeStyles: Record<MeetingType, { bg: string; text: string; label: string }> = {
  discovery: { bg: "bg-[#DBEAFE]", text: "text-[#1D4ED8]", label: "Discovery" },
  demo: { bg: "bg-[#D1FAE5]", text: "text-[#047857]", label: "Demo" },
  follow_up: { bg: "bg-[#FEF3C7]", text: "text-[#B45309]", label: "Follow-up" },
};

export function MeetingItem({ name, company, time, day, type, duration = 30 }: MeetingItemProps) {
  const style = typeStyles[type];

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-[#F8FAFC] transition-colors">
      {/* Date/Time */}
      <div className="w-20 shrink-0">
        <p className="text-xs text-[#94A3B8]">{day}</p>
        <p className="text-sm font-medium text-[#1E293B]">{time}</p>
      </div>

      {/* Divider */}
      <div className="w-px h-10 bg-[#E2E8F0]" />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-[#1E293B] truncate">{name}</p>
        {company && <p className="text-sm text-[#94A3B8] truncate">{company}</p>}
      </div>

      {/* Badge + Duration */}
      <div className="flex flex-col items-end gap-1">
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${style.bg} ${style.text}`}>
          {style.label}
        </span>
        <span className="text-xs text-[#94A3B8]">{duration} min</span>
      </div>
    </div>
  );
}

export default MeetingItem;
