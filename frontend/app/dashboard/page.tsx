/**
 * FILE: frontend/app/dashboard/page.tsx
 * PURPOSE: Dashboard home with activity feed and metrics
 * PHASE: 8 (Frontend)
 * TASK: FE-007
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Target,
  Users,
  MessageSquare,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  Mail,
  Phone,
  Linkedin,
} from "lucide-react";

// Placeholder data - would come from API
const stats = [
  {
    title: "Active Campaigns",
    value: "12",
    change: "+2",
    changeType: "positive",
    icon: Target,
  },
  {
    title: "Total Leads",
    value: "2,847",
    change: "+124",
    changeType: "positive",
    icon: Users,
  },
  {
    title: "Replies This Week",
    value: "89",
    change: "+23%",
    changeType: "positive",
    icon: MessageSquare,
  },
  {
    title: "Conversion Rate",
    value: "3.2%",
    change: "-0.1%",
    changeType: "negative",
    icon: TrendingUp,
  },
];

const recentActivity = [
  {
    id: 1,
    type: "reply",
    channel: "email",
    leadName: "Sarah Johnson",
    company: "TechCorp",
    message: "Thanks for reaching out! I'd love to learn more...",
    intent: "interested",
    time: "5 minutes ago",
  },
  {
    id: 2,
    type: "sent",
    channel: "linkedin",
    leadName: "Michael Chen",
    company: "StartupXYZ",
    message: "Connection request sent",
    time: "12 minutes ago",
  },
  {
    id: 3,
    type: "reply",
    channel: "sms",
    leadName: "Emma Wilson",
    company: "Growth Agency",
    message: "Yes, let's schedule a call for next week",
    intent: "meeting_request",
    time: "1 hour ago",
  },
  {
    id: 4,
    type: "enriched",
    channel: null,
    leadName: "David Brown",
    company: "Enterprise Co",
    message: "Lead enriched with Apollo data",
    time: "2 hours ago",
  },
];

const channelIcon = {
  email: Mail,
  sms: Phone,
  linkedin: Linkedin,
};

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome back! Here&apos;s what&apos;s happening with your campaigns.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <div className="flex items-center text-xs text-muted-foreground">
                {stat.changeType === "positive" ? (
                  <ArrowUpRight className="mr-1 h-3 w-3 text-green-500" />
                ) : (
                  <ArrowDownRight className="mr-1 h-3 w-3 text-red-500" />
                )}
                <span
                  className={
                    stat.changeType === "positive"
                      ? "text-green-500"
                      : "text-red-500"
                  }
                >
                  {stat.change}
                </span>
                <span className="ml-1">from last week</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Activity Feed */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>
              Latest interactions across all campaigns
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.map((activity) => {
                const ChannelIcon = activity.channel
                  ? channelIcon[activity.channel as keyof typeof channelIcon]
                  : null;

                return (
                  <div
                    key={activity.id}
                    className="flex items-start gap-4 rounded-lg border p-4"
                  >
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                      {ChannelIcon ? (
                        <ChannelIcon className="h-5 w-5 text-muted-foreground" />
                      ) : (
                        <Users className="h-5 w-5 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{activity.leadName}</span>
                        <span className="text-sm text-muted-foreground">
                          at {activity.company}
                        </span>
                        {activity.intent && (
                          <Badge
                            variant={
                              activity.intent === "interested" ||
                              activity.intent === "meeting_request"
                                ? "active"
                                : "secondary"
                            }
                            className="text-xs"
                          >
                            {activity.intent.replace("_", " ")}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-1">
                        {activity.message}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {activity.time}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="col-span-1">
          <CardHeader>
            <CardTitle>ALS Tier Distribution</CardTitle>
            <CardDescription>
              Lead quality breakdown across all campaigns
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { tier: "Hot", count: 234, percent: 8, color: "bg-red-500" },
                { tier: "Warm", count: 567, percent: 20, color: "bg-orange-500" },
                { tier: "Cool", count: 891, percent: 31, color: "bg-blue-500" },
                { tier: "Cold", count: 1023, percent: 36, color: "bg-gray-400" },
                { tier: "Dead", count: 132, percent: 5, color: "bg-gray-200" },
              ].map((item) => (
                <div key={item.tier} className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={item.tier.toLowerCase() as "hot" | "warm" | "cool" | "cold" | "dead"}
                      >
                        {item.tier}
                      </Badge>
                      <span className="text-muted-foreground">
                        {item.count.toLocaleString()} leads
                      </span>
                    </div>
                    <span className="font-medium">{item.percent}%</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted">
                    <div
                      className={`h-2 rounded-full ${item.color}`}
                      style={{ width: `${item.percent}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
