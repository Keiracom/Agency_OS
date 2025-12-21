/**
 * FILE: frontend/app/admin/costs/channels/page.tsx
 * PURPOSE: Channel costs breakdown for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Channel Costs
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
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
const mockChannelCosts = {
  total: 1599.69,
  channels: [
    {
      name: "Email",
      provider: "Resend",
      icon: Mail,
      color: "bg-blue-500",
      sent: 18470,
      cost: 456.23,
      costPer: 0.025,
      budget: 600,
    },
    {
      name: "SMS",
      provider: "Twilio",
      icon: MessageSquare,
      color: "bg-green-500",
      sent: 2340,
      cost: 389.45,
      costPer: 0.166,
      budget: 500,
    },
    {
      name: "LinkedIn",
      provider: "HeyReach",
      icon: Linkedin,
      color: "bg-sky-500",
      sent: 4560,
      cost: 534.12,
      costPer: 0.117,
      budget: 700,
    },
    {
      name: "Voice",
      provider: "Synthflow",
      icon: Phone,
      color: "bg-purple-500",
      sent: 156,
      cost: 156.00,
      costPer: 1.00,
      budget: 300,
    },
    {
      name: "Mail",
      provider: "Lob",
      icon: Package,
      color: "bg-orange-500",
      sent: 45,
      cost: 63.89,
      costPer: 1.42,
      budget: 200,
    },
  ],
  byClient: [
    { client: "LeadGen Pro", email: 123.45, sms: 89.20, linkedin: 156.78, voice: 45.00, mail: 12.34 },
    { client: "GrowthLab", email: 98.76, sms: 67.89, linkedin: 123.45, voice: 34.00, mail: 8.90 },
    { client: "Enterprise Co", email: 87.65, sms: 78.90, linkedin: 89.12, voice: 28.00, mail: 15.67 },
    { client: "ScaleUp Co", email: 65.43, sms: 45.67, linkedin: 67.89, voice: 22.00, mail: 9.87 },
    { client: "Marketing Plus", email: 45.12, sms: 34.56, linkedin: 45.67, voice: 15.00, mail: 6.78 },
  ],
};

export default function AdminChannelCostsPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Channel Costs</h1>
        <p className="text-muted-foreground">
          Per-channel spend breakdown - December 2025
        </p>
      </div>

      {/* Total */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Channel Costs MTD
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">${mockChannelCosts.total.toLocaleString()}</div>
        </CardContent>
      </Card>

      {/* Channel Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        {mockChannelCosts.channels.map((channel) => {
          const Icon = channel.icon;
          const usagePercent = Math.round((channel.cost / channel.budget) * 100);
          return (
            <Card key={channel.name}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <div className={`p-1.5 rounded ${channel.color} text-white`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  {channel.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-2xl font-bold">${channel.cost.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">
                    {channel.sent.toLocaleString()} sent @ ${channel.costPer.toFixed(3)}/ea
                  </p>
                </div>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span>Budget</span>
                    <span>${channel.budget}</span>
                  </div>
                  <Progress value={usagePercent} className="h-2" />
                  <p className="text-xs text-muted-foreground text-right">
                    {usagePercent}% used
                  </p>
                </div>
                <Badge variant="outline" className="w-full justify-center">
                  {channel.provider}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* By Client Table */}
      <Card>
        <CardHeader>
          <CardTitle>Costs by Client</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead className="text-right">Email</TableHead>
                <TableHead className="text-right">SMS</TableHead>
                <TableHead className="text-right">LinkedIn</TableHead>
                <TableHead className="text-right">Voice</TableHead>
                <TableHead className="text-right">Mail</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockChannelCosts.byClient.map((row) => {
                const total = row.email + row.sms + row.linkedin + row.voice + row.mail;
                return (
                  <TableRow key={row.client}>
                    <TableCell className="font-medium">{row.client}</TableCell>
                    <TableCell className="text-right">${row.email.toFixed(2)}</TableCell>
                    <TableCell className="text-right">${row.sms.toFixed(2)}</TableCell>
                    <TableCell className="text-right">${row.linkedin.toFixed(2)}</TableCell>
                    <TableCell className="text-right">${row.voice.toFixed(2)}</TableCell>
                    <TableCell className="text-right">${row.mail.toFixed(2)}</TableCell>
                    <TableCell className="text-right font-bold">${total.toFixed(2)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Cost Breakdown Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Channel Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockChannelCosts.channels.map((channel) => {
              const percentage = Math.round((channel.cost / mockChannelCosts.total) * 100);
              const Icon = channel.icon;
              return (
                <div key={channel.name} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{channel.name}</span>
                    </div>
                    <span className="text-muted-foreground">
                      ${channel.cost.toFixed(2)} ({percentage}%)
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={channel.color}
                      style={{ width: `${percentage}%`, height: "100%" }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
