/**
 * FILE: frontend/app/admin/campaigns/page.tsx
 * PURPOSE: Global campaigns view for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Campaigns
 */

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Filter } from "lucide-react";
import { createBrowserClient } from "@/lib/supabase";
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

// Phase 4 admin Tier A wiring (2026-05-10): replaces hardcoded mockCampaigns
// with live `campaigns` + `clients` join. Activity-derived metrics
// (leads / sent / replies / replyRate) currently render 0 — pre-revenue
// (0 emails sent ever per audit). Real aggregation deferred to a follow-up
// once outbound flows are wired (Stripe + Salesforge unblock).
interface Campaign {
  id: string;
  name: string;
  client: string;
  status: string;
  leads: number;
  sent: number;
  replies: number;
  replyRate: number;
}

type CampaignRow = {
  id: string;
  name: string;
  status: string | null;
  clients: { name: string | null } | null;
};

async function fetchAdminCampaigns(): Promise<Campaign[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const { data, error } = await client
    .from("campaigns")
    .select("id, name, status, clients(name)")
    .order("created_at", { ascending: false })
    .limit(500);
  if (error) throw error;
  return ((data ?? []) as CampaignRow[]).map((row) => ({
    id: row.id,
    name: row.name,
    client: row.clients?.name ?? "",
    status: row.status ?? "draft",
    leads: 0,
    sent: 0,
    replies: 0,
    replyRate: 0,
  }));
}

const statusColors = {
  active: "bg-amber/10 text-amber border-amber/20",
  paused: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  completed: "bg-bg-surface0/10 text-ink-3 border-gray-500/20",
  draft: "bg-panel/10 text-amber border-default/20",
};

export default function AdminCampaignsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const { data: campaigns = [] } = useQuery({
    queryKey: ["admin-campaigns"],
    queryFn: fetchAdminCampaigns,
    staleTime: 30 * 1000,
  });

  const filteredCampaigns = campaigns.filter((campaign) => {
    const matchesSearch =
      campaign.name.toLowerCase().includes(search.toLowerCase()) ||
      campaign.client.toLowerCase().includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || campaign.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const totalLeads = filteredCampaigns.reduce((sum, c) => sum + c.leads, 0);
  const totalSent = filteredCampaigns.reduce((sum, c) => sum + c.sent, 0);
  const totalReplies = filteredCampaigns.reduce((sum, c) => sum + c.replies, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Campaigns</h1>
        <p className="text-muted-foreground">
          All campaigns across all clients
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Campaigns
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredCampaigns.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Leads
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalLeads.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Messages Sent
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalSent.toLocaleString()}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Replies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalReplies.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              {totalSent > 0 ? ((totalReplies / totalSent) * 100).toFixed(1) : 0}% avg reply rate
            </p>
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
                placeholder="Search campaigns or clients..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="paused">Paused</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="draft">Draft</SelectItem>
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
                <TableHead>Campaign</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Leads</TableHead>
                <TableHead>Sent</TableHead>
                <TableHead>Replies</TableHead>
                <TableHead>Reply Rate</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCampaigns.map((campaign) => (
                <TableRow key={campaign.id}>
                  <TableCell className="font-medium">{campaign.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {campaign.client}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={statusColors[campaign.status as keyof typeof statusColors]}
                    >
                      {campaign.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{campaign.leads.toLocaleString()}</TableCell>
                  <TableCell>{campaign.sent.toLocaleString()}</TableCell>
                  <TableCell>{campaign.replies}</TableCell>
                  <TableCell>
                    {campaign.replyRate > 0 ? `${campaign.replyRate}%` : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
