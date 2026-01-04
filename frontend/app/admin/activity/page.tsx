/**
 * FILE: frontend/app/admin/activity/page.tsx
 * PURPOSE: Global activity log for admin (LIVE DATA)
 * PHASE: 18 (Admin Dashboard Fixes)
 */

"use client";

import { useState } from "react";
import { Search, RefreshCw, Mail, MessageSquare, Linkedin, Phone, Package } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useGlobalActivity } from "@/hooks/use-admin";

const channelIcons: Record<string, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
  voice: Phone,
  mail: Package,
};

const channelColors: Record<string, string> = {
  email: "bg-blue-500/10 text-blue-600",
  sms: "bg-green-500/10 text-green-600",
  linkedin: "bg-sky-500/10 text-sky-600",
  voice: "bg-purple-500/10 text-purple-600",
  mail: "bg-orange-500/10 text-orange-600",
};

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function TableSkeleton() {
  return (
    <div className="space-y-3 p-4">
      {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
        <div key={i} className="flex gap-4">
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-8 w-10" />
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-8 w-48" />
        </div>
      ))}
    </div>
  );
}

export default function AdminActivityPage() {
  const [search, setSearch] = useState("");
  const [channelFilter, setChannelFilter] = useState("all");

  const { data: activities, isLoading, error, refetch } = useGlobalActivity(100);

  // Filter activities
  const filteredActivities = (activities || []).filter((activity) => {
    const matchesSearch =
      activity.client_name?.toLowerCase().includes(search.toLowerCase()) ||
      activity.details?.toLowerCase().includes(search.toLowerCase()) ||
      activity.action?.toLowerCase().includes(search.toLowerCase());
    const matchesChannel =
      channelFilter === "all" || activity.channel === channelFilter;
    return matchesSearch && matchesChannel;
  });

  // Count by channel
  const channelCounts = (activities || []).reduce((acc, a) => {
    if (a.channel) {
      acc[a.channel] = (acc[a.channel] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Activity Log</h1>
          <p className="text-muted-foreground">
            Real-time activity across all clients
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
            Live
          </Badge>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : (activities?.length || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Mail className="h-4 w-4" />
              Emails
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : (channelCounts.email || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Linkedin className="h-4 w-4" />
              LinkedIn
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : (channelCounts.linkedin || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              SMS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : (channelCounts.sms || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Phone className="h-4 w-4" />
              Voice
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : (channelCounts.voice || 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search activity..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={channelFilter} onValueChange={setChannelFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="sms">SMS</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
                <SelectItem value="voice">Voice</SelectItem>
                <SelectItem value="mail">Mail</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <TableSkeleton />
          ) : error ? (
            <div className="p-8 text-center text-muted-foreground">
              <p>Failed to load activity</p>
              <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
              </Button>
            </div>
          ) : filteredActivities.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground">
              No activity found
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Client</TableHead>
                  <TableHead>Channel</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredActivities.map((activity) => {
                  const Icon = activity.channel
                    ? channelIcons[activity.channel]
                    : null;
                  return (
                    <TableRow key={activity.id}>
                      <TableCell className="text-muted-foreground">
                        {formatTimeAgo(activity.timestamp || activity.created_at)}
                      </TableCell>
                      <TableCell className="font-medium">{activity.client_name}</TableCell>
                      <TableCell>
                        {activity.channel && Icon && (
                          <div
                            className={`inline-flex items-center justify-center h-8 w-8 rounded ${
                              channelColors[activity.channel] || ""
                            }`}
                          >
                            <Icon className="h-4 w-4" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell>{activity.action}</TableCell>
                      <TableCell className="text-muted-foreground text-sm max-w-[300px] truncate">
                        {activity.details}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
