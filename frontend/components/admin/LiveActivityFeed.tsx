/**
 * FILE: frontend/components/admin/LiveActivityFeed.tsx
 * PURPOSE: Real-time activity feed for admin dashboard
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Components
 */

"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Mail, MessageSquare, Linkedin, Phone, Package } from "lucide-react";

export interface Activity {
  id: string;
  client_name: string;
  action: string;
  details: string;
  timestamp: Date;
  channel?: "email" | "sms" | "linkedin" | "voice" | "mail";
}

interface LiveActivityFeedProps {
  activities: Activity[];
  maxItems?: number;
  loading?: boolean;
  className?: string;
}

export function LiveActivityFeed({
  activities,
  maxItems = 10,
  loading = false,
  className,
}: LiveActivityFeedProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Live Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1">
                  <Skeleton className="h-4 w-full mb-1" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const displayedActivities = activities.slice(0, maxItems);

  const getChannelIcon = (channel?: Activity["channel"]) => {
    switch (channel) {
      case "email":
        return <Mail className="h-4 w-4" />;
      case "sms":
        return <MessageSquare className="h-4 w-4" />;
      case "linkedin":
        return <Linkedin className="h-4 w-4" />;
      case "voice":
        return <Phone className="h-4 w-4" />;
      case "mail":
        return <Package className="h-4 w-4" />;
      default:
        return null;
    }
  };

  const getChannelColor = (channel?: Activity["channel"]) => {
    switch (channel) {
      case "email":
        return "bg-blue-500/10 text-blue-600";
      case "sms":
        return "bg-green-500/10 text-green-600";
      case "linkedin":
        return "bg-sky-500/10 text-sky-600";
      case "voice":
        return "bg-purple-500/10 text-purple-600";
      case "mail":
        return "bg-orange-500/10 text-orange-600";
      default:
        return "bg-gray-500/10 text-gray-600";
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Live Activity</CardTitle>
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs text-muted-foreground">Live</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {displayedActivities.length === 0 ? (
          <p className="text-sm text-muted-foreground">No recent activity</p>
        ) : (
          <div className="space-y-3">
            {displayedActivities.map((activity) => (
              <div
                key={activity.id}
                className="flex items-start gap-3 text-sm"
              >
                <span className="text-xs text-muted-foreground shrink-0 w-12">
                  {formatTime(activity.timestamp)}
                </span>
                {activity.channel && (
                  <div
                    className={cn(
                      "flex items-center justify-center h-6 w-6 rounded shrink-0",
                      getChannelColor(activity.channel)
                    )}
                  >
                    {getChannelIcon(activity.channel)}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <span className="font-medium">{activity.client_name}</span>
                  <span className="text-muted-foreground mx-1">-</span>
                  <span className="text-muted-foreground">{activity.details}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
