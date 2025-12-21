/**
 * FILE: frontend/app/dashboard/reports/page.tsx
 * PURPOSE: Reports and analytics page
 * PHASE: 8 (Frontend)
 * TASK: FE-013
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Download, Calendar } from "lucide-react";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            Analytics and performance metrics for your campaigns
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Calendar className="mr-2 h-4 w-4" />
            Last 30 days
          </Button>
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        {[
          { label: "Total Sent", value: "12,450", change: "+8.2%" },
          { label: "Total Opens", value: "4,890", change: "+5.4%" },
          { label: "Total Replies", value: "342", change: "+12.1%" },
          { label: "Meetings Booked", value: "28", change: "+15.3%" },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              <p className="text-3xl font-bold mt-1">{stat.value}</p>
              <p className="text-sm text-green-600 mt-1">{stat.change} vs last period</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Channel Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Channel Performance</CardTitle>
          <CardDescription>Metrics broken down by outreach channel</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="p-3 text-left text-sm font-medium">Channel</th>
                  <th className="p-3 text-right text-sm font-medium">Sent</th>
                  <th className="p-3 text-right text-sm font-medium">Delivered</th>
                  <th className="p-3 text-right text-sm font-medium">Opened</th>
                  <th className="p-3 text-right text-sm font-medium">Replied</th>
                  <th className="p-3 text-right text-sm font-medium">Reply Rate</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { channel: "Email", sent: 8500, delivered: 8245, opened: 3450, replied: 245, rate: 2.9 },
                  { channel: "SMS", sent: 2100, delivered: 2089, opened: null, replied: 67, rate: 3.2 },
                  { channel: "LinkedIn", sent: 1850, delivered: 1823, opened: 1440, replied: 30, rate: 1.6 },
                ].map((row) => (
                  <tr key={row.channel} className="border-b">
                    <td className="p-3 font-medium">{row.channel}</td>
                    <td className="p-3 text-right">{row.sent.toLocaleString()}</td>
                    <td className="p-3 text-right">{row.delivered.toLocaleString()}</td>
                    <td className="p-3 text-right">{row.opened?.toLocaleString() ?? "N/A"}</td>
                    <td className="p-3 text-right">{row.replied.toLocaleString()}</td>
                    <td className="p-3 text-right">
                      <Badge variant={row.rate >= 3 ? "active" : "secondary"}>
                        {row.rate}%
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Campaign Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Campaign Performance</CardTitle>
          <CardDescription>Compare performance across all campaigns</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="p-3 text-left text-sm font-medium">Campaign</th>
                  <th className="p-3 text-left text-sm font-medium">Status</th>
                  <th className="p-3 text-right text-sm font-medium">Leads</th>
                  <th className="p-3 text-right text-sm font-medium">Contacted</th>
                  <th className="p-3 text-right text-sm font-medium">Replied</th>
                  <th className="p-3 text-right text-sm font-medium">Converted</th>
                  <th className="p-3 text-right text-sm font-medium">Conv. Rate</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { name: "Tech Startups Q1", status: "active", leads: 450, contacted: 234, replied: 45, converted: 12 },
                  { name: "SaaS Decision Makers", status: "active", leads: 320, contacted: 180, replied: 28, converted: 8 },
                  { name: "E-commerce Brands", status: "paused", leads: 280, contacted: 150, replied: 22, converted: 5 },
                ].map((campaign) => (
                  <tr key={campaign.name} className="border-b">
                    <td className="p-3 font-medium">{campaign.name}</td>
                    <td className="p-3">
                      <Badge variant={campaign.status as "active" | "paused"} className="capitalize">
                        {campaign.status}
                      </Badge>
                    </td>
                    <td className="p-3 text-right">{campaign.leads}</td>
                    <td className="p-3 text-right">{campaign.contacted}</td>
                    <td className="p-3 text-right">{campaign.replied}</td>
                    <td className="p-3 text-right">{campaign.converted}</td>
                    <td className="p-3 text-right">
                      <Badge variant="outline">
                        {((campaign.converted / campaign.contacted) * 100).toFixed(1)}%
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
