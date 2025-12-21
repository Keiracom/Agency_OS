/**
 * FILE: frontend/app/admin/activity/page.tsx
 * PURPOSE: Global activity log for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Activity
 */

"use client";

import { useState } from "react";
import { Search, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { Mail, MessageSquare, Linkedin, Phone, Package } from "lucide-react";

// Mock data
const mockActivities = [
  { id: "1", client: "LeadGen Pro", action: "Email sent", lead: "john@acme.com", channel: "email", timestamp: new Date(Date.now() - 1000 * 60 * 2) },
  { id: "2", client: "GrowthLab", action: "Lead enriched", lead: "sarah@tech.co", channel: null, timestamp: new Date(Date.now() - 1000 * 60 * 5) },
  { id: "3", client: "ScaleUp Co", action: "Reply received", lead: "mike@startup.io", channel: "email", timestamp: new Date(Date.now() - 1000 * 60 * 8) },
  { id: "4", client: "Marketing Plus", action: "SMS sent", lead: "lisa@enterprise.com", channel: "sms", timestamp: new Date(Date.now() - 1000 * 60 * 12) },
  { id: "5", client: "Enterprise Co", action: "LinkedIn connection", lead: "david@agency.com", channel: "linkedin", timestamp: new Date(Date.now() - 1000 * 60 * 15) },
  { id: "6", client: "LeadGen Pro", action: "Voice call completed", lead: "emma@corp.net", channel: "voice", timestamp: new Date(Date.now() - 1000 * 60 * 20) },
  { id: "7", client: "GrowthLab", action: "Direct mail queued", lead: "james@biz.com", channel: "mail", timestamp: new Date(Date.now() - 1000 * 60 * 25) },
  { id: "8", client: "ScaleUp Co", action: "Email opened", lead: "anna@global.io", channel: "email", timestamp: new Date(Date.now() - 1000 * 60 * 30) },
  { id: "9", client: "Marketing Plus", action: "Lead scored", lead: "tom@sales.co", channel: null, timestamp: new Date(Date.now() - 1000 * 60 * 35) },
  { id: "10", client: "Enterprise Co", action: "Email bounced", lead: "invalid@bounce.net", channel: "email", timestamp: new Date(Date.now() - 1000 * 60 * 40) },
];

const channelIcons = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
  voice: Phone,
  mail: Package,
};

const channelColors = {
  email: "bg-blue-500/10 text-blue-600",
  sms: "bg-green-500/10 text-green-600",
  linkedin: "bg-sky-500/10 text-sky-600",
  voice: "bg-purple-500/10 text-purple-600",
  mail: "bg-orange-500/10 text-orange-600",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminActivityPage() {
  const [search, setSearch] = useState("");
  const [channelFilter, setChannelFilter] = useState("all");

  const filteredActivities = mockActivities.filter((activity) => {
    const matchesSearch =
      activity.client.toLowerCase().includes(search.toLowerCase()) ||
      activity.lead.toLowerCase().includes(search.toLowerCase()) ||
      activity.action.toLowerCase().includes(search.toLowerCase());
    const matchesChannel =
      channelFilter === "all" || activity.channel === channelFilter;
    return matchesSearch && matchesChannel;
  });

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
        <Badge variant="outline" className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
          Live
        </Badge>
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
            <div className="text-2xl font-bold">2,847</div>
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
            <div className="text-2xl font-bold">1,847</div>
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
            <div className="text-2xl font-bold">456</div>
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
            <div className="text-2xl font-bold">234</div>
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
            <div className="text-2xl font-bold">89</div>
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
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Channel</TableHead>
                <TableHead>Action</TableHead>
                <TableHead>Lead</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredActivities.map((activity) => {
                const Icon = activity.channel
                  ? channelIcons[activity.channel as keyof typeof channelIcons]
                  : null;
                return (
                  <TableRow key={activity.id}>
                    <TableCell className="text-muted-foreground">
                      {formatTimeAgo(activity.timestamp)}
                    </TableCell>
                    <TableCell className="font-medium">{activity.client}</TableCell>
                    <TableCell>
                      {activity.channel && Icon && (
                        <div
                          className={`inline-flex items-center justify-center h-8 w-8 rounded ${
                            channelColors[activity.channel as keyof typeof channelColors]
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                        </div>
                      )}
                    </TableCell>
                    <TableCell>{activity.action}</TableCell>
                    <TableCell className="text-muted-foreground font-mono text-sm">
                      {activity.lead}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
