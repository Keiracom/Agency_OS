"use client";

/**
 * MeetingsWidget.tsx - Upcoming meetings list
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Features:
 * - Day/time on left
 * - Name and company
 * - Meeting type badge (Discovery, Demo, Follow-up)
 * - Duration display
 */

import { Calendar, Clock } from "lucide-react";

type MeetingType = "discovery" | "demo" | "follow_up";

interface Meeting {
  id: string;
  leadName: string;
  company: string;
  scheduledAt: string;
  dayLabel: string;
  timeLabel: string;
  meetingType: MeetingType;
  durationMinutes: number;
}

interface MeetingsWidgetProps {
  meetings: Meeting[];
}

const meetingTypeConfig: Record<MeetingType, { label: string; bgColor: string; textColor: string }> = {
  discovery: { label: "Discovery", bgColor: "bg-[#DBEAFE]", textColor: "text-[#1D4ED8]" },
  demo: { label: "Demo", bgColor: "bg-[#D1FAE5]", textColor: "text-[#047857]" },
  follow_up: { label: "Follow-up", bgColor: "bg-[#FEF3C7]", textColor: "text-[#B45309]" },
};

export function MeetingsWidget({ meetings }: MeetingsWidgetProps) {
  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-[#E2E8F0]">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Upcoming Meetings
        </h2>
      </div>

      {/* Meetings list */}
      <div className="divide-y divide-[#E2E8F0]">
        {meetings.length === 0 ? (
          <div className="px-6 py-8 text-center">
            <Calendar className="h-8 w-8 text-[#94A3B8] mx-auto mb-2" />
            <p className="text-sm text-[#64748B]">No upcoming meetings</p>
          </div>
        ) : (
          meetings.map((meeting) => {
            const typeConfig = meetingTypeConfig[meeting.meetingType];

            return (
              <div key={meeting.id} className="px-6 py-4 hover:bg-[#F8FAFC] transition-colors">
                <div className="flex items-start gap-4">
                  {/* Date/Time column */}
                  <div className="flex-shrink-0 text-center min-w-[60px]">
                    <div className="text-xs font-medium text-[#64748B] uppercase">
                      {meeting.dayLabel}
                    </div>
                    <div className="text-sm font-semibold text-[#1E293B]">
                      {meeting.timeLabel}
                    </div>
                  </div>

                  {/* Meeting details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-[#1E293B] truncate">
                        {meeting.leadName}
                      </span>
                    </div>
                    <p className="text-sm text-[#64748B] truncate">{meeting.company}</p>

                    {/* Meeting type badge + duration */}
                    <div className="flex items-center gap-2 mt-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${typeConfig.bgColor} ${typeConfig.textColor}`}
                      >
                        {typeConfig.label}
                      </span>
                      <div className="flex items-center gap-1 text-xs text-[#94A3B8]">
                        <Clock className="h-3 w-3" />
                        <span>{meeting.durationMinutes}m</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
