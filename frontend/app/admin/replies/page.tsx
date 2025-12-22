/**
 * FILE: frontend/app/admin/replies/page.tsx
 * PURPOSE: Global reply inbox for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Replies
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, Mail, MessageSquare, Linkedin, ExternalLink } from "lucide-react";
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

// Mock data
const mockReplies: Reply[] = [
  {
    id: "1",
    client: "LeadGen Pro",
    clientId: "cl1",
    leadEmail: "john@acme.com",
    leadId: "l1",
    leadName: "John Smith",
    channel: "email",
    intent: "interested",
    message: "Thanks for reaching out! I'd love to learn more about your services.",
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
  },
  {
    id: "2",
    client: "GrowthLab",
    clientId: "cl2",
    leadEmail: "sarah@tech.co",
    leadId: "l2",
    leadName: "Sarah Johnson",
    channel: "email",
    intent: "meeting_request",
    message: "Can we schedule a call for next Tuesday?",
    timestamp: new Date(Date.now() - 1000 * 60 * 45),
  },
  {
    id: "3",
    client: "ScaleUp Co",
    clientId: "cl3",
    leadEmail: "mike@startup.io",
    leadId: "l3",
    leadName: "Mike Wilson",
    channel: "linkedin",
    intent: "question",
    message: "What are your pricing options for small teams?",
    timestamp: new Date(Date.now() - 1000 * 60 * 90),
  },
  {
    id: "4",
    client: "Marketing Plus",
    clientId: "cl4",
    leadEmail: "lisa@enterprise.com",
    leadId: "l4",
    leadName: "Lisa Brown",
    channel: "sms",
    intent: "not_interested",
    message: "Not interested at this time, thanks.",
    timestamp: new Date(Date.now() - 1000 * 60 * 120),
  },
  {
    id: "5",
    client: "Enterprise Co",
    clientId: "cl5",
    leadEmail: "david@agency.com",
    leadId: "l5",
    leadName: "David Lee",
    channel: "email",
    intent: "out_of_office",
    message: "I'm out of the office until January 5th.",
    timestamp: new Date(Date.now() - 1000 * 60 * 180),
  },
  {
    id: "6",
    client: "LeadGen Pro",
    clientId: "cl1",
    leadEmail: "emma@corp.net",
    leadId: "l6",
    leadName: "Emma Davis",
    channel: "email",
    intent: "unsubscribe",
    message: "Please remove me from your mailing list.",
    timestamp: new Date(Date.now() - 1000 * 60 * 240),
  },
];

const intentColors: Record<string, string> = {
  interested: "bg-green-500/10 text-green-700 border-green-500/20",
  meeting_request: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  question: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  not_interested: "bg-red-500/10 text-red-700 border-red-500/20",
  unsubscribe: "bg-red-500/10 text-red-700 border-red-500/20",
  out_of_office: "bg-gray-500/10 text-gray-700 border-gray-500/20",
  auto_reply: "bg-gray-500/10 text-gray-700 border-gray-500/20",
};

const channelIcons = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
};

const channelColors = {
  email: "bg-blue-500/10 text-blue-600",
  sms: "bg-green-500/10 text-green-600",
  linkedin: "bg-sky-500/10 text-sky-600",
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

  const clients = Array.from(new Set(mockReplies.map((r) => r.client)));

  const filteredReplies = mockReplies.filter((reply) => {
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
  const interestedCount = mockReplies.filter((r) => r.intent === "interested").length;
  const meetingCount = mockReplies.filter((r) => r.intent === "meeting_request").length;
  const questionCount = mockReplies.filter((r) => r.intent === "question").length;

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
            <div className="text-2xl font-bold">{mockReplies.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Interested
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{interestedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Meeting Requests
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{meetingCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Questions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{questionCount}</div>
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
