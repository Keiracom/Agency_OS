/**
 * FILE: frontend/components/dashboard-v4/WeekAheadCard.tsx
 * PURPOSE: Card showing upcoming meetings for the week
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calendar, ArrowRight, Clock } from "lucide-react";
import type { UpcomingMeeting } from "./types";

interface WeekAheadCardProps {
  meetings: UpcomingMeeting[];
}

function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `$${(value / 1000).toFixed(0)}K`;
  }
  return `$${value}`;
}

function MeetingItem({ meeting }: { meeting: UpcomingMeeting }) {
  return (
    <Link
      href={`/dashboard/leads/${meeting.id}`}
      className="flex items-center gap-4 p-4 rounded-xl bg-muted/50 hover:bg-muted transition-colors"
    >
      <div className="text-center min-w-[50px]">
        <p className="text-xs text-muted-foreground uppercase font-medium">
          {meeting.dayLabel}
        </p>
        <p className="text-2xl font-extrabold text-foreground">
          {meeting.dayNumber}
        </p>
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-foreground truncate">{meeting.name}</p>
        <p className="text-sm text-muted-foreground truncate">{meeting.company}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-xs text-primary font-medium">{meeting.time}</span>
          <span className="text-xs text-muted-foreground flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {meeting.type} • {meeting.duration}
          </span>
        </div>
      </div>
      <div className="text-right flex-shrink-0">
        <p className="text-lg font-bold text-emerald-500">
          {formatCurrency(meeting.potentialValue)}
        </p>
        <p className="text-[10px] text-muted-foreground">Potential</p>
      </div>
    </Link>
  );
}

export function WeekAheadCard({ meetings }: WeekAheadCardProps) {
  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">Your Week Ahead</CardTitle>
          </div>
          <Link 
            href="/dashboard/settings?tab=integrations" 
            className="text-sm text-primary font-medium hover:underline flex items-center gap-1"
          >
            See calendar <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {meetings.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No meetings scheduled this week. Time to book some!
          </p>
        ) : (
          <div className="space-y-3">
            {meetings.map((meeting) => (
              <MeetingItem key={meeting.id} meeting={meeting} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
