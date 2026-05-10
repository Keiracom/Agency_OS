/**
 * FILE: frontend/app/admin/clients/[id]/page.tsx
 * PURPOSE: Admin client detail page
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Client Detail
 */

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { createBrowserClient } from "@/lib/supabase";
import {
  ArrowLeft,
  Eye,
  Pause,
  X,
  Target,
  Users,
  Activity,
  CreditCard,
  Building2,
  Calendar,
  Clock,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ClientHealthIndicator } from "@/components/admin/ClientHealthIndicator";

// Phase 4 admin Tier A wiring (2026-05-10): replaces hardcoded mockClient
// with live `clients` JOIN `memberships` JOIN `users` for the team list.
// Nested arrays (campaigns / recentActivity / billing) default to empty —
// pre-revenue (no campaigns sent, no Stripe, no activity yet). Each
// section's wire-up is a separate follow-up once outbound flows + Stripe
// are unblocked.
type ClientDetail = {
  id: string;
  name: string;
  tier: "ignition" | "velocity" | "spark";
  mrr: number;
  status: "active" | "trialing" | "past_due" | "paused" | "cancelled";
  healthScore: number;
  creditsRemaining: number;
  creditsTotal: number;
  createdAt: Date;
  renewalDate: Date;
  lastActivity: Date;
  team: { id: string; name: string; email: string; role: string }[];
  campaigns: { id: string; name: string; status: string; leads: number; sent: number; replies: number }[];
  recentActivity: { id: string; action: string; details: string; timestamp: Date; channel: string | null }[];
  billing: { id: string; date: Date; amount: number; status: string; invoice: string }[];
};

type ClientRow = {
  id: string;
  name: string;
  tier: string | null;
  subscription_status: string | null;
  created_at: string;
  updated_at: string;
  memberships: Array<{
    role: string | null;
    deleted_at: string | null;
    users: { id: string; email: string; full_name: string | null } | null;
  }> | null;
};

async function fetchAdminClient(clientId: string): Promise<ClientDetail | null> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const { data, error } = await client
    .from("clients")
    .select(
      "id, name, tier, subscription_status, created_at, updated_at, memberships(role, deleted_at, users(id, email, full_name))"
    )
    .eq("id", clientId)
    .maybeSingle();
  if (error || !data) return null;
  const row = data as ClientRow;
  const allowedTier: ClientDetail["tier"] = (["ignition", "velocity", "spark"].includes(row.tier ?? "")
    ? (row.tier as ClientDetail["tier"])
    : "ignition");
  const allowedStatus: ClientDetail["status"] = (
    ["active", "trialing", "past_due", "paused", "cancelled"].includes(row.subscription_status ?? "")
      ? (row.subscription_status as ClientDetail["status"])
      : "active"
  );
  const team = (row.memberships ?? [])
    .filter((m) => m.deleted_at === null && m.users)
    .map((m) => ({
      id: m.users!.id,
      name: m.users!.full_name ?? m.users!.email,
      email: m.users!.email,
      role: m.role ?? "member",
    }));
  return {
    id: row.id,
    name: row.name,
    tier: allowedTier,
    mrr: 0,
    status: allowedStatus,
    healthScore: 0,
    creditsRemaining: 0,
    creditsTotal: 0,
    createdAt: new Date(row.created_at),
    renewalDate: new Date(row.created_at),
    lastActivity: new Date(row.updated_at),
    team,
    campaigns: [],
    recentActivity: [],
    billing: [],
  };
}

const tierColors = {
  ignition: "bg-panel/10 text-amber border-default/20",
  velocity: "bg-amber/10 text-amber border-amber/20",
  spark: "bg-sky-500/10 text-sky-700 border-sky-500/20",
};

const statusColors = {
  active: "bg-amber/10 text-amber",
  trialing: "bg-panel/10 text-amber",
  past_due: "bg-amber-glow text-error",
  paused: "bg-yellow-500/10 text-yellow-700",
  cancelled: "bg-bg-surface0/10 text-ink-3",
};

const campaignStatusColors = {
  active: "bg-amber/10 text-amber border-amber/20",
  paused: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  completed: "bg-bg-surface0/10 text-ink-3 border-gray-500/20",
  draft: "bg-panel/10 text-amber border-default/20",
};

function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminClientDetailPage() {
  const params = useParams();
  const clientId = (params?.id ?? "") as string;
  const [activeTab, setActiveTab] = useState("overview");

  const { data: client, isLoading } = useQuery({
    queryKey: ["admin-client", clientId],
    queryFn: () => fetchAdminClient(clientId),
    enabled: !!clientId,
    staleTime: 30 * 1000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <p className="text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!client) {
    return (
      <div className="space-y-6">
        <Link
          href="/admin/clients"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Clients
        </Link>
        <p className="text-sm text-muted-foreground">Client not found.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <Link
        href="/admin/clients"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Clients
      </Link>

      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-xl">
            {client.name.charAt(0)}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{client.name}</h1>
              <Badge variant="outline" className={tierColors[client.tier]}>
                {client.tier}
              </Badge>
              <Badge className={statusColors[client.status]}>
                {client.status}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Client since {formatDate(client.createdAt)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <ClientHealthIndicator score={client.healthScore} size="lg" />
          <div className="flex gap-2">
            <Button variant="outline">
              <Eye className="mr-2 h-4 w-4" />
              Impersonate
            </Button>
            <Button variant="outline">
              <Pause className="mr-2 h-4 w-4" />
              Pause
            </Button>
            <Button variant="destructive">
              <X className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="campaigns">Campaigns</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  MRR
                </CardTitle>
                <CreditCard className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">${client.mrr}</div>
                <p className="text-xs text-muted-foreground">
                  Renews {formatDate(client.renewalDate)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Credits
                </CardTitle>
                <Target className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {client.creditsRemaining.toLocaleString()}
                </div>
                <p className="text-xs text-muted-foreground">
                  of {client.creditsTotal.toLocaleString()} remaining
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Active Campaigns
                </CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {client.campaigns.filter((c) => c.status === "active").length}
                </div>
                <p className="text-xs text-muted-foreground">
                  {client.campaigns.length} total
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Last Activity
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {formatTimeAgo(client.lastActivity)}
                </div>
                <p className="text-xs text-muted-foreground">Email sent</p>
              </CardContent>
            </Card>
          </div>

          {/* Team Members */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Team Members
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {client.team.map((member) => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between py-2 border-b last:border-0"
                  >
                    <div>
                      <p className="font-medium">{member.name}</p>
                      <p className="text-sm text-muted-foreground">{member.email}</p>
                    </div>
                    <Badge variant="outline" className="capitalize">
                      {member.role}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Campaigns Tab */}
        <TabsContent value="campaigns">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Campaign</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Leads</TableHead>
                    <TableHead>Sent</TableHead>
                    <TableHead>Replies</TableHead>
                    <TableHead>Reply Rate</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {client.campaigns.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell className="font-medium">{campaign.name}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={campaignStatusColors[campaign.status as keyof typeof campaignStatusColors]}
                        >
                          {campaign.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{campaign.leads}</TableCell>
                      <TableCell>{campaign.sent}</TableCell>
                      <TableCell>{campaign.replies}</TableCell>
                      <TableCell>
                        {campaign.sent > 0
                          ? ((campaign.replies / campaign.sent) * 100).toFixed(1)
                          : 0}
                        %
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Activity Tab */}
        <TabsContent value="activity">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                {client.recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center gap-4 py-2 border-b last:border-0"
                  >
                    <span className="text-sm text-muted-foreground w-20">
                      {formatTimeAgo(activity.timestamp)}
                    </span>
                    <div className="flex-1">
                      <span className="font-medium">{activity.action}</span>
                      <span className="text-muted-foreground ml-2">
                        {activity.details}
                      </span>
                    </div>
                    {activity.channel && (
                      <Badge variant="outline">{activity.channel}</Badge>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Billing Tab */}
        <TabsContent value="billing">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Invoice</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {client.billing.map((payment) => (
                    <TableRow key={payment.id}>
                      <TableCell>{formatDate(payment.date)}</TableCell>
                      <TableCell className="font-mono text-sm">
                        {payment.invoice}
                      </TableCell>
                      <TableCell>${payment.amount}</TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className="bg-amber/10 text-amber border-amber/20"
                        >
                          {payment.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
