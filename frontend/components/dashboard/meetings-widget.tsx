/**
 * FILE: frontend/components/dashboard/meetings-widget.tsx
 * PURPOSE: Widget showing upcoming meetings
 * PHASE: 14 (Missing UI)
 * TASK: MUI-002
 */

"use client";

import Link from "next/link";
import { Calendar, Clock, ArrowRight, Settings } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useUpcomingMeetings, type Meeting } from "@/hooks/use-meetings";
import { Skeleton } from "@/components/ui/loading-skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { getInitials, getAvatarColor } from "@/lib/utils";

function formatMeetingTime(dateString: string | null): string {
  if (!dateString) return "Time TBD";

  const date = new Date(dateString);
  const now = new Date();
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);

  const timeStr = date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });

  // Same day
  if (date.toDateString() === now.toDateString()) {
    return `Today at ${timeStr}`;
  }

  // Tomorrow
  if (date.toDateString() === tomorrow.toDateString()) {
    return `Tomorrow at ${timeStr}`;
  }

  // Within 7 days
  const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 7) {
    const dayName = date.toLocaleDateString("en-US", { weekday: "long" });
    return `${dayName} at ${timeStr}`;
  }

  // Beyond 7 days
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function MeetingItem({ meeting }: { meeting: Meeting }) {
  const initials = getInitials(meeting.lead_name);

  return (
    <Link
      href={`/dashboard/leads/${meeting.lead_id}`}
      className="flex items-center gap-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
    >
      <Avatar className="h-10 w-10">
        <AvatarFallback className={getAvatarColor(meeting.lead_name)}>
          {initials}
        </AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate">{meeting.lead_name}</p>
        {meeting.lead_company && (
          <p className="text-sm text-muted-foreground truncate">
            {meeting.lead_company}
          </p>
        )}
      </div>
      <div className="text-right">
        <p className="text-sm font-medium">
          {formatMeetingTime(meeting.scheduled_at)}
        </p>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          {meeting.duration_minutes}min
        </div>
      </div>
    </Link>
  );
}

function MeetingsWidgetSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-3 p-3 rounded-lg border">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="flex-1">
            <Skeleton className="h-4 w-24 mb-1" />
            <Skeleton className="h-3 w-16" />
          </div>
          <div className="text-right">
            <Skeleton className="h-4 w-20 mb-1" />
            <Skeleton className="h-3 w-12" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function MeetingsWidget() {
  const { data, isLoading, error } = useUpcomingMeetings(5);

  const meetings = data?.items || [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-lg">Upcoming Meetings</CardTitle>
          </div>
          <Link href="/dashboard/settings?tab=integrations">
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <Settings className="h-4 w-4" />
            </Button>
          </Link>
        </div>
        <CardDescription>
          Meetings booked through Agency OS
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <MeetingsWidgetSkeleton />
        ) : error ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            Unable to load meetings
          </p>
        ) : meetings.length === 0 ? (
          <EmptyState
            icon={Calendar}
            title="No upcoming meetings"
            description="Meetings will appear here when leads book time with you"
            className="py-6"
          />
        ) : (
          <div className="space-y-2">
            {meetings.map((meeting) => (
              <MeetingItem key={meeting.id} meeting={meeting} />
            ))}
            {data && data.total > 5 && (
              <Link href="/dashboard/meetings">
                <Button variant="ghost" className="w-full mt-2">
                  View all {data.total} meetings
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default MeetingsWidget;
