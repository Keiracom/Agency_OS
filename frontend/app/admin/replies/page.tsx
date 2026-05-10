/**
 * FILE: frontend/app/admin/replies/page.tsx
 * PURPOSE: Global reply inbox for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Replies
 */

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Search, Mail, MessageSquare, Linkedin, ExternalLink } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

interface Reply {
  id: string;
  client: string;
  clientId: string;
  leadEmail: string;
  leadId: string;
  leadName: string;
  channel: "email" | "sms" | "linkedin";
  intent: string;
  message: string;
  timestamp: Date;
}

// Phase 4 admin Tier A wiring (2026-05-10): replaces hardcoded mockReplies
// with live activities query filtered to reply-shaped actions, joined with
// leads + clients for sender + client display. Same action enum as
// /api/replies route (PR #639).
const REPLY_ACTIONS = ["reply.received", "reply_received", "received_reply"];

type ActivityRow = {
  id: string;
  client_id: string | null;
  lead_id: string | null;
  channel: string | null;
  intent: string | null;
  content_preview: string | null;
  created_at: string;
  leads: {
    email: string | null;
    first_name: string | null;
    last_name: string | null;
  } | null;
  clients: { name: string | null } | null;
};

const CHANNEL_OF = (raw: string | null): "email" | "sms" | "linkedin" => {
  if (raw === "sms" || raw === "linkedin") return raw;
  return "email";
};

async function fetchAdminReplies(): Promise<Reply[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const { data, error } = await client
    .from("activities")
    .select(
      "id, client_id, lead_id, channel, intent, content_preview, created_at, leads(email, first_name, last_name), clients(name)"
    )
    .in("action", REPLY_ACTIONS)
    .order("created_at", { ascending: false })
    .limit(200);
  if (error) throw error;
  return ((data ?? []) as ActivityRow[]).map((row) => ({
    id: row.id,
    client: row.clients?.name ?? "",
    clientId: row.client_id ?? "",
    leadEmail: row.leads?.email ?? "",
    leadId: row.lead_id ?? "",
    leadName:
      [row.leads?.first_name, row.leads?.last_name].filter(Boolean).join(" ") || "Unknown",
    channel: CHANNEL_OF(row.channel),
    intent: row.intent ?? "neutral",
    message: row.content_preview ?? "",
    timestamp: new Date(row.created_at),
  }));
}

const intentColors: Record<string, string> = {
  interested: "bg-amber/10 text-amber border-amber/20",
  meeting_request: "bg-panel/10 text-amber border-default/20",
  question: "bg-amber/10 text-amber border-amber/20",
  not_interested: "bg-amber-glow text-error border-amber/20",
  unsubscribe: "bg-amber-glow text-error border-amber/20",
  out_of_office: "bg-bg-surface0/10 text-ink-3 border-gray-500/20",
  auto_reply: "bg-bg-surface0/10 text-ink-3 border-gray-500/20",
};

const channelIcons = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
};

const channelColors = {
  email: "bg-panel/10 text-ink-2",
  sms: "bg-amber/10 text-amber",
  linkedin: "bg-amber-glow text-amber",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminRepliesPage() {
  const [search, setSearch] = useState("");
  const [intentFilter, setIntentFilter] = useState("all");
  const [clientFilter, setClientFilter] = useState("all");
  const [channelFilter, setChannelFilter] = useState("all");

  const { data: replies = [], isLoading } = useQuery({
    queryKey: ["admin-replies"],
    queryFn: fetchAdminReplies,
    staleTime: 30 * 1000,
  });

  const clients = Array.from(new Set(replies.map((r) => r.client).filter(Boolean)));

  const filteredReplies = replies.filter((reply) => {
    const matchesSearch =
      reply.leadEmail.toLowerCase().includes(search.toLowerCase()) ||
      reply.leadName.toLowerCase().includes(search.toLowerCase()) ||
      reply.message.toLowerCase().includes(search.toLowerCase());
    const matchesIntent = intentFilter === "all" || reply.intent === intentFilter;
    const matchesClient = clientFilter === "all" || reply.client === clientFilter;
    const matchesChannel = channelFilter === "all" || reply.channel === channelFilter;
    return matchesSearch && matchesIntent && matchesClient && matchesChannel;
  });

  // Stats
  const interestedCount = replies.filter((r) => r.intent === "interested").length;
  const meetingCount = replies.filter((r) => r.intent === "meeting_request").length;
  const questionCount = replies.filter((r) => r.intent === "question").length;
  void isLoading; // surfaced via row count "0" pre-revenue; loading flag unused for stats

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Reply Inbox</h1>
        <p className="text-muted-foreground">
          All replies across all clients
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Replies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{replies.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Interested
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber">{interestedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Meeting Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-ink-2">{meetingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Questions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber">{questionCount}</div>
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
                placeholder="Search replies..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={intentFilter} onValueChange={setIntentFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Intent" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Intents</SelectItem>
                <SelectItem value="interested">Interested</SelectItem>
                <SelectItem value="meeting_request">Meeting Request</SelectItem>
                <SelectItem value="question">Question</SelectItem>
                <SelectItem value="not_interested">Not Interested</SelectItem>
                <SelectItem value="unsubscribe">Unsubscribe</SelectItem>
                <SelectItem value="out_of_office">Out of Office</SelectItem>
              </SelectContent>
            </Select>
            <Select value={clientFilter} onValueChange={setClientFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Client" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Clients</SelectItem>
                {clients.map((client) => (
                  <SelectItem key={client} value={client}>
                    {client}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={channelFilter} onValueChange={setChannelFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Channels</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="sms">SMS</SelectItem>
                <SelectItem value="linkedin">LinkedIn</SelectItem>
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
                <TableHead>Lead</TableHead>
                <TableHead>Intent</TableHead>
                <TableHead className="max-w-[300px]">Message</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredReplies.map((reply) => {
                const Icon = channelIcons[reply.channel];
                return (
                  <TableRow key={reply.id}>
                    <TableCell className="text-muted-foreground whitespace-nowrap">
                      {formatTimeAgo(reply.timestamp)}
                    </TableCell>
                    <TableCell className="font-medium">{reply.client}</TableCell>
                    <TableCell>
                      <div
                        className={`inline-flex items-center justify-center h-8 w-8 rounded ${
                          channelColors[reply.channel]
                        }`}
                      >
                        <Icon className="h-4 w-4" />
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium">{reply.leadName}</p>
                        <p className="text-sm text-muted-foreground">{reply.leadEmail}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className={intentColors[reply.intent] || ""}
                      >
                        {reply.intent.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="max-w-[300px] truncate text-muted-foreground">
                      {reply.message}
                    </TableCell>
                    <TableCell>
                      <Button variant="ghost" size="icon" asChild>
                        <Link href={`/admin/clients/${reply.clientId}`}>
                          <ExternalLink className="h-4 w-4" />
                        </Link>
                      </Button>
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
