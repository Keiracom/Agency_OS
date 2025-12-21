/**
 * FILE: frontend/app/admin/clients/[id]/page.tsx
 * PURPOSE: Admin client detail page
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Client Detail
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
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

// Mock client data
const mockClient = {
  id: "1",
  name: "LeadGen Pro",
  tier: "dominance" as const,
  mrr: 999,
  status: "active" as const,
  healthScore: 92,
  creditsRemaining: 2500,
  creditsTotal: 5000,
  createdAt: new Date("2024-06-15"),
  renewalDate: new Date("2025-01-15"),
  lastActivity: new Date(Date.now() - 1000 * 60 * 5),
  team: [
    { id: "1", name: "John Smith", email: "john@leadgenpro.com", role: "owner" },
    { id: "2", name: "Jane Doe", email: "jane@leadgenpro.com", role: "admin" },
    { id: "3", name: "Bob Wilson", email: "bob@leadgenpro.com", role: "member" },
  ],
  campaigns: [
    { id: "1", name: "Q4 Outreach", status: "active", leads: 450, sent: 380, replies: 23 },
    { id: "2", name: "Tech Startups", status: "active", leads: 320, sent: 290, replies: 18 },
    { id: "3", name: "Enterprise Push", status: "paused", leads: 890, sent: 750, replies: 45 },
    { id: "4", name: "SMB Nurture", status: "completed", leads: 680, sent: 680, replies: 52 },
  ],
  recentActivity: [
    { id: "1", action: "Email sent", details: "to john@acme.com", timestamp: new Date(Date.now() - 1000 * 60 * 5), channel: "email" },
    { id: "2", action: "Lead enriched", details: "ALS: 82", timestamp: new Date(Date.now() - 1000 * 60 * 15), channel: null },
    { id: "3", action: "Reply received", details: "from sarah@tech.co", timestamp: new Date(Date.now() - 1000 * 60 * 45), channel: "email" },
    { id: "4", action: "LinkedIn sent", details: "connection request", timestamp: new Date(Date.now() - 1000 * 60 * 60), channel: "linkedin" },
  ],
  billing: [
    { id: "1", date: new Date("2024-12-01"), amount: 999, status: "paid", invoice: "INV-2024-1201" },
    { id: "2", date: new Date("2024-11-01"), amount: 999, status: "paid", invoice: "INV-2024-1101" },
    { id: "3", date: new Date("2024-10-01"), amount: 999, status: "paid", invoice: "INV-2024-1001" },
  ],
};

const tierColors = {
  ignition: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  velocity: "bg-purple-500/10 text-purple-700 border-purple-500/20",
  dominance: "bg-amber-500/10 text-amber-700 border-amber-500/20",
};

const statusColors = {
  active: "bg-green-500/10 text-green-700",
  trialing: "bg-blue-500/10 text-blue-700",
  past_due: "bg-red-500/10 text-red-700",
  paused: "bg-yellow-500/10 text-yellow-700",
  cancelled: "bg-gray-500/10 text-gray-700",
};

const campaignStatusColors = {
  active: "bg-green-500/10 text-green-700 border-green-500/20",
  paused: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  completed: "bg-gray-500/10 text-gray-700 border-gray-500/20",
  draft: "bg-blue-500/10 text-blue-700 border-blue-500/20",
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
  const [activeTab, setActiveTab] = useState("overview");

  // In production, fetch client data based on params.id
  const client = mockClient;

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
                          className="bg-green-500/10 text-green-700 border-green-500/20"
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
