/**
 * FILE: frontend/app/admin/ops/page.tsx
 * PURPOSE: Operations panel — real-time pre-revenue ops metrics from
 *          live Supabase queries. Phase 1 deliverable from the
 *          2026-05-08 audit ("Operations panel" Aiden-assigned).
 *
 *          Server component reading direct from Supabase via the SSR
 *          client. RLS-scoped via auth.uid(); platform-admin gate
 *          handled by frontend/app/admin/layout.tsx.
 *
 *          Honest empty state when zero data — pre-revenue (0
 *          customers / 0 emails sent / 0 meetings) renders honest
 *          zeros rather than fake numbers. The "no real data yet"
 *          framing is the truth.
 */

export const dynamic = "force-dynamic";

import { createClient } from "@/lib/supabase/server";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Activity,
  Calendar,
  Database,
  DollarSign,
  TrendingDown,
  Zap,
} from "lucide-react";

interface CostBreakdownRow {
  group: string;
  cost: number;
  calls: number;
}

interface BUUpdates {
  last1h: number;
  last24h: number;
}

interface ChannelActivity {
  channel: string;
  count: number;
}

async function fetchOpsData() {
  const supabase = await createClient();

  const todayISO = new Date().toISOString().split("T")[0];
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
  const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

  const [
    { data: sdkRows, error: sdkErr },
    { data: vendorRows, error: vendorErr },
    { count: bu1h, error: bu1hErr },
    { count: bu24h, error: bu24hErr },
    { count: meetingsToday, error: meetingsErr },
    { data: activityRows, error: activityErr },
  ] = await Promise.all([
    supabase
      .from("sdk_usage_log")
      .select("agent_type, cost_aud")
      .gte("created_at", `${todayISO}T00:00:00Z`),
    supabase
      .from("vendor_usage_log")
      .select("vendor, cost_aud")
      .gte("created_at", `${todayISO}T00:00:00Z`),
    supabase
      .from("business_universe")
      .select("*", { count: "exact", head: true })
      .gte("updated_at", oneHourAgo),
    supabase
      .from("business_universe")
      .select("*", { count: "exact", head: true })
      .gte("updated_at", dayAgo),
    supabase
      .from("meetings")
      .select("*", { count: "exact", head: true })
      .gte("scheduled_at", `${todayISO}T00:00:00Z`)
      .lt("scheduled_at", `${todayISO}T23:59:59Z`),
    supabase
      .from("activities")
      .select("channel")
      .gte("created_at", dayAgo),
  ]);

  const errors = [sdkErr, vendorErr, bu1hErr, bu24hErr, meetingsErr, activityErr]
    .filter(Boolean)
    .map((e) => e?.message ?? "unknown")
    .join("; ");

  // Cost: aggregate by agent_type for SDK, by vendor for vendor table
  const sdkBreakdown: CostBreakdownRow[] = aggregateCost(
    (sdkRows ?? []) as Array<{ agent_type: string | null; cost_aud: string | number }>,
    (r) => r.agent_type ?? "unknown",
  );
  const vendorBreakdown: CostBreakdownRow[] = aggregateCost(
    (vendorRows ?? []) as Array<{ vendor: string | null; cost_aud: string | number }>,
    (r) => r.vendor ?? "unknown",
  );

  const sdkTotal = sdkBreakdown.reduce((s, r) => s + r.cost, 0);
  const vendorTotal = vendorBreakdown.reduce((s, r) => s + r.cost, 0);
  const totalToday = sdkTotal + vendorTotal;

  // Activity by channel
  const channelCounts = new Map<string, number>();
  for (const row of (activityRows ?? []) as Array<{ channel: string | null }>) {
    const ch = row.channel ?? "unknown";
    channelCounts.set(ch, (channelCounts.get(ch) ?? 0) + 1);
  }
  const channelActivity: ChannelActivity[] = Array.from(
    channelCounts.entries(),
  )
    .map(([channel, count]) => ({ channel, count }))
    .sort((a, b) => b.count - a.count);

  return {
    cost: { sdkTotal, vendorTotal, totalToday, sdkBreakdown, vendorBreakdown },
    bu: { last1h: bu1h ?? 0, last24h: bu24h ?? 0 } satisfies BUUpdates,
    meetingsToday: meetingsToday ?? 0,
    channelActivity,
    activityTotal24h: activityRows?.length ?? 0,
    errors: errors || null,
  };
}

function aggregateCost<T>(
  rows: Array<T & { cost_aud: string | number }>,
  groupFn: (row: T) => string,
): CostBreakdownRow[] {
  const map = new Map<string, { cost: number; calls: number }>();
  for (const row of rows) {
    const key = groupFn(row);
    const cost = typeof row.cost_aud === "string" ? Number(row.cost_aud) : row.cost_aud;
    const cur = map.get(key) ?? { cost: 0, calls: 0 };
    map.set(key, { cost: cur.cost + (cost || 0), calls: cur.calls + 1 });
  }
  return Array.from(map.entries())
    .map(([group, v]) => ({ group, ...v }))
    .sort((a, b) => b.cost - a.cost);
}

function formatAUD(amount: number): string {
  return amount.toFixed(amount >= 10 ? 2 : 4);
}

export default async function OpsPanelPage() {
  const data = await fetchOpsData();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Operations</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Real-time view of cost, pipeline activity, and conversion. All
          data live from Supabase. Pre-revenue means honest zeros where
          there&apos;s no traffic yet.
        </p>
        {data.errors && (
          <p className="text-xs text-red-600 mt-2">
            Some queries failed: {data.errors}
          </p>
        )}
      </div>

      {/* Top KPIs */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <DollarSign className="w-3 h-3" /> Cost today (AUD)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${formatAUD(data.cost.totalToday)}</div>
            <p className="text-xs text-muted-foreground mt-1">
              SDK ${formatAUD(data.cost.sdkTotal)} + vendor ${formatAUD(data.cost.vendorTotal)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Database className="w-3 h-3" /> BU updates (1h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.bu.last1h}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.bu.last24h} in last 24h
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Calendar className="w-3 h-3" /> Meetings today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.meetingsToday}</div>
            <p className="text-xs text-muted-foreground mt-1">scheduled_at = today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground flex items-center gap-2">
              <Activity className="w-3 h-3" /> Activities (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.activityTotal24h}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {data.channelActivity.length} channel{data.channelActivity.length === 1 ? "" : "s"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Cost breakdown */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Zap className="w-4 h-4" /> SDK cost today (by agent_type)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.cost.sdkBreakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No SDK calls recorded today.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-xs text-muted-foreground uppercase">
                  <tr className="border-b">
                    <th className="text-left pb-2 font-medium">agent_type</th>
                    <th className="text-right pb-2 font-medium">calls</th>
                    <th className="text-right pb-2 font-medium">AUD</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cost.sdkBreakdown.map((row) => (
                    <tr key={row.group} className="border-b last:border-0">
                      <td className="py-2 font-mono text-xs">{row.group}</td>
                      <td className="py-2 text-right font-mono">{row.calls}</td>
                      <td className="py-2 text-right font-mono">${formatAUD(row.cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <TrendingDown className="w-4 h-4" /> Vendor cost today (by vendor)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.cost.vendorBreakdown.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No vendor calls recorded today. Vendor instrumentation
                deployed via PR #649; client wiring pending DFS-402
                top-up decision.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-xs text-muted-foreground uppercase">
                  <tr className="border-b">
                    <th className="text-left pb-2 font-medium">vendor</th>
                    <th className="text-right pb-2 font-medium">calls</th>
                    <th className="text-right pb-2 font-medium">AUD</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cost.vendorBreakdown.map((row) => (
                    <tr key={row.group} className="border-b last:border-0">
                      <td className="py-2 font-mono text-xs">{row.group}</td>
                      <td className="py-2 text-right font-mono">{row.calls}</td>
                      <td className="py-2 text-right font-mono">${formatAUD(row.cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Channel activity */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Activity by channel (24h)</CardTitle>
        </CardHeader>
        <CardContent>
          {data.channelActivity.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No outbound activity recorded in the last 24 hours.
            </p>
          ) : (
            <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
              {data.channelActivity.map((c) => (
                <div
                  key={c.channel}
                  className="rounded-md border bg-background p-3"
                >
                  <div className="text-xs uppercase tracking-wider text-muted-foreground">
                    {c.channel}
                  </div>
                  <div className="text-xl font-bold mt-1 font-mono">{c.count}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
