/**
 * FILE: frontend/app/admin/revenue/page.tsx
 * PURPOSE: Revenue dashboard for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Revenue
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Users,
  AlertCircle,
} from "lucide-react";

// Mock data
const mockRevenue = {
  mrr: 47500,
  arr: 570000,
  newMrr: 2497,
  churnedMrr: 499,
  netGrowth: 1998,
  churnRate: 1.05,
  arpu: 2500,
};

const mockTierBreakdown = [
  { tier: "Dominance", clients: 8, mrr: 7992, percentage: 16.8 },
  { tier: "Velocity", clients: 7, mrr: 3493, percentage: 7.4 },
  { tier: "Ignition", clients: 4, mrr: 796, percentage: 1.7 },
];

const mockRecentTransactions = [
  { date: new Date(Date.now() - 1000 * 60 * 60 * 2), client: "LeadGen Pro", type: "renewal", amount: 999, status: "succeeded" },
  { date: new Date(Date.now() - 1000 * 60 * 60 * 24), client: "Marketing Plus", type: "new", amount: 199, status: "succeeded" },
  { date: new Date(Date.now() - 1000 * 60 * 60 * 48), client: "GrowthLab", type: "renewal", amount: 499, status: "succeeded" },
  { date: new Date(Date.now() - 1000 * 60 * 60 * 72), client: "Enterprise Co", type: "upgrade", amount: 500, status: "succeeded" },
];

const mockUpcomingRenewals = [
  { client: "ScaleUp Co", tier: "velocity", renewalDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 5), amount: 499 },
  { client: "StartupXYZ", tier: "ignition", renewalDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 12), amount: 199 },
  { client: "TechVentures", tier: "dominance", renewalDate: new Date(Date.now() + 1000 * 60 * 60 * 24 * 18), amount: 999 },
];

const mockAtRisk = [
  { client: "StartupXYZ", tier: "ignition", status: "past_due", daysPastDue: 3 },
];

function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminRevenuePage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Revenue</h1>
        <p className="text-muted-foreground">Financial metrics and billing</p>
      </div>

      {/* KPIs */}
      <div className="grid gap-4 md:grid-cols-4 lg:grid-cols-7">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              MRR
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${mockRevenue.mrr.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              ARR
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${mockRevenue.arr.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              New MRR
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              +${mockRevenue.newMrr.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Churned MRR
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              -${mockRevenue.churnedMrr.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Net Growth
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              +${mockRevenue.netGrowth.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Churn Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockRevenue.churnRate}%</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              ARPU
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${mockRevenue.arpu.toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tier Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Revenue by Tier</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockTierBreakdown.map((tier) => (
              <div key={tier.tier} className="flex items-center gap-4">
                <div className="w-24 font-medium">{tier.tier}</div>
                <div className="flex-1 h-4 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary"
                    style={{ width: `${tier.percentage * 5}%` }}
                  />
                </div>
                <div className="w-24 text-right">
                  ${tier.mrr.toLocaleString()}
                </div>
                <div className="w-16 text-right text-muted-foreground">
                  {tier.clients} clients
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Recent Transactions */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Transactions</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockRecentTransactions.map((tx, i) => (
                  <TableRow key={i}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{tx.client}</p>
                        <p className="text-xs text-muted-foreground">
                          {formatTimeAgo(tx.date)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell className="capitalize">{tx.type}</TableCell>
                    <TableCell>${tx.amount}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="bg-green-500/10 text-green-700"
                      >
                        {tx.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Upcoming Renewals */}
        <Card>
          <CardHeader>
            <CardTitle>Upcoming Renewals (30 days)</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Renewal</TableHead>
                  <TableHead>Amount</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockUpcomingRenewals.map((renewal, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{renewal.client}</TableCell>
                    <TableCell className="capitalize">{renewal.tier}</TableCell>
                    <TableCell>{formatDate(renewal.renewalDate)}</TableCell>
                    <TableCell>${renewal.amount}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* At Risk */}
      {mockAtRisk.length > 0 && (
        <Card className="border-red-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertCircle className="h-5 w-5" />
              At-Risk Clients
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Client</TableHead>
                  <TableHead>Tier</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Days Past Due</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mockAtRisk.map((client, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{client.client}</TableCell>
                    <TableCell className="capitalize">{client.tier}</TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="bg-red-500/10 text-red-700"
                      >
                        {client.status.replace("_", " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-red-600">
                      {client.daysPastDue} days
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
