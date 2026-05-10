/**
 * FILE: frontend/app/admin/costs/channels/page.tsx
 * PURPOSE: Channel costs breakdown for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Channel Costs
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { createBrowserClient } from "@/lib/supabase";
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

// Phase 4 admin Tier A wiring (2026-05-10): live aggregates from
// vendor_usage_log GROUP BY vendor (channel mapping) + per client_id
// for byClient breakdown. Pre-revenue: 0 vendors fired, all rows render
// 0. Real fill on E1 R3 PR 2/3 client wiring landing.
type ChannelRow = {
  name: string;
  provider: string;
  icon: typeof Mail;
  color: string;
  sent: number;
  cost: number;
  costPer: number;
  budget: number;
};

type ChannelCosts = {
  total: number;
  channels: ChannelRow[];
  byClient: Array<{ client: string; email: number; sms: number; linkedin: number; voice: number; mail: number }>;
};

type VendorRow = { vendor: string | null; cost_aud: string | number; client_id: string | null };

const CHANNEL_DEFS: Array<{ name: string; provider: string; icon: typeof Mail; color: string; budget: number }> = [
  { name: "Email", provider: "Resend / Salesforge", icon: Mail, color: "bg-panel", budget: 600 },
  { name: "SMS", provider: "Telnyx", icon: MessageSquare, color: "bg-amber", budget: 500 },
  { name: "LinkedIn", provider: "Unipile", icon: Linkedin, color: "bg-amber", budget: 700 },
  { name: "Voice", provider: "ElevenAgents", icon: Phone, color: "bg-amber", budget: 300 },
  { name: "Mail", provider: "—", icon: Package, color: "bg-orange-500", budget: 200 },
];

function vendorToChannel(v: string): "email" | "sms" | "linkedin" | "voice" | "mail" {
  const x = v.toLowerCase();
  if (x.includes("salesforge") || x.includes("resend") || x.includes("postmark")) return "email";
  if (x.includes("telnyx") || x.includes("twilio")) return "sms";
  if (x.includes("unipile") || x.includes("heyreach") || x.includes("linkedin")) return "linkedin";
  if (x.includes("vapi") || x.includes("voice") || x.includes("eleven")) return "voice";
  if (x.includes("mail") || x.includes("postal")) return "mail";
  return "email";
}

async function fetchChannelCosts(): Promise<ChannelCosts> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString();

  const { data: vendorRows } = await client
    .from("vendor_usage_log")
    .select("vendor, cost_aud, client_id")
    .gte("created_at", monthStart);
  const { data: clientRows } = await client.from("clients").select("id, name");

  const clientNameById = new Map<string, string>();
  for (const c of (clientRows ?? []) as Array<{ id: string; name: string }>) {
    clientNameById.set(c.id, c.name);
  }

  const channelTotals: Record<string, number> = { email: 0, sms: 0, linkedin: 0, voice: 0, mail: 0 };
  const byClientMap = new Map<string, { email: number; sms: number; linkedin: number; voice: number; mail: number }>();
  let total = 0;

  for (const row of (vendorRows ?? []) as VendorRow[]) {
    const cost = typeof row.cost_aud === "string" ? Number(row.cost_aud) : row.cost_aud || 0;
    const ch = vendorToChannel(row.vendor ?? "");
    channelTotals[ch] += cost;
    total += cost;
    if (row.client_id) {
      const cur = byClientMap.get(row.client_id) ?? { email: 0, sms: 0, linkedin: 0, voice: 0, mail: 0 };
      cur[ch] += cost;
      byClientMap.set(row.client_id, cur);
    }
  }

  const channels: ChannelRow[] = CHANNEL_DEFS.map((def) => {
    const key = vendorToChannel(def.name);
    return { ...def, sent: 0, cost: channelTotals[key] ?? 0, costPer: 0 };
  });

  const byClient = Array.from(byClientMap.entries()).map(([clientId, breakdown]) => ({
    client: clientNameById.get(clientId) ?? "Unknown",
    ...breakdown,
  }));

  return { total, channels, byClient };
}

const EMPTY_CHANNEL_COSTS: ChannelCosts = {
  total: 0,
  channels: CHANNEL_DEFS.map((def) => ({ ...def, sent: 0, cost: 0, costPer: 0 })),
  byClient: [],
};

export default function AdminChannelCostsPage() {
  const { data: mockChannelCosts = EMPTY_CHANNEL_COSTS } = useQuery({
    queryKey: ["admin-channel-costs"],
    queryFn: fetchChannelCosts,
    staleTime: 30 * 1000,
  });

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
                  <div className={`p-1.5 rounded ${channel.color} text-ink`}>
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
