/**
 * FILE: frontend/app/admin/page.tsx
 * PURPOSE: Admin Command Center - main dashboard (LIVE DATA)
 * PHASE: 18 (Admin Dashboard Fixes)
 */

"use client";

import { DollarSign, Users, Target, Cpu, RefreshCw } from "lucide-react";
import {
  KPICard,
  AlertBanner,
  SystemStatusIndicator,
  LiveActivityFeed,
  type Alert,
  type ServiceStatus,
  type Activity,
} from "@/components/admin";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  useAdminStats,
  useSystemHealth,
  useAlerts,
  useGlobalActivity,
} from "@/hooks/use-admin";

function KPISkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardHeader className="pb-2">
            <Skeleton className="h-4 w-24" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-32 mb-2" />
            <Skeleton className="h-3 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function KPISection() {
  const { data: stats, isLoading, error, refetch } = useAdminStats();

  if (isLoading) return <KPISkeleton />;

  if (error || !stats) {
    return (
      <Card className="p-6">
        <div className="text-center text-muted-foreground">
          <p>Failed to load stats</p>
          <Button variant="outline" size="sm" className="mt-2" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  const spendLimit = stats.ai_spend_limit ?? 100;
  const spendToday = stats.ai_spend_today ?? 0;
  const aiSpendPercent = spendLimit > 0
    ? Math.round((Number(spendToday) / Number(spendLimit)) * 100)
    : 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KPICard
        title="MRR"
        value={`$${Number(stats.mrr ?? stats.mrr_aud ?? 0).toLocaleString()}`}
        change={stats.mrr_change ?? 0}
        changeLabel="MoM"
        icon={<DollarSign className="h-4 w-4" />}
      />
      <KPICard
        title="Active Clients"
        value={stats.active_clients}
        change={stats.new_clients_this_month ?? 0}
        changeLabel="new this month"
        icon={<Users className="h-4 w-4" />}
      />
      <KPICard
        title="Leads Today"
        value={(stats.leads_today ?? 0).toLocaleString()}
        change={stats.leads_change ?? 0}
        changeLabel="vs yesterday"
        icon={<Target className="h-4 w-4" />}
      />
      <KPICard
        title="AI Spend Today"
        value={`$${Number(spendToday).toFixed(0)} / $${Number(spendLimit).toFixed(0)}`}
        change={aiSpendPercent}
        changeLabel="of daily limit"
        icon={<Cpu className="h-4 w-4" />}
      />
    </div>
  );
}

function SystemStatusSection() {
  const { data: health, isLoading, error } = useSystemHealth();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-16 w-24" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !health) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Failed to load system status</p>
        </CardContent>
      </Card>
    );
  }

  const services: ServiceStatus[] = health.services.map((s) => ({
    name: s.name,
    status: s.status as "healthy" | "degraded" | "down",
    latency: s.latency_ms ?? undefined,
    message: s.message ?? undefined,
  }));

  return <SystemStatusIndicator services={services} />;
}

function AlertsSection() {
  const { data: alertsData, isLoading, error } = useAlerts();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !alertsData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Failed to load alerts</p>
        </CardContent>
      </Card>
    );
  }

  const alerts: Alert[] = alertsData.map((a) => ({
    id: a.id,
    severity: a.severity,
    message: a.title || a.description,
    timestamp: new Date(a.created_at),
    link: undefined,
    dismissible: !a.acknowledged,
  }));

  return <AlertBanner alerts={alerts} />;
}

function ActivitySection() {
  const { data: activities, isLoading, error } = useGlobalActivity(10);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Live Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !activities) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Live Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Failed to load activity</p>
        </CardContent>
      </Card>
    );
  }

  const activityItems: Activity[] = activities.map((a) => ({
    id: a.id,
    client_name: a.client_name || "Unknown",
    action: a.action,
    details: a.details || "",
    timestamp: new Date(a.timestamp || a.created_at),
    channel: a.channel ?? undefined,
  }));

  return <LiveActivityFeed activities={activityItems} maxItems={10} />;
}

export default function AdminCommandCenter() {
  const { data: stats } = useAdminStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Command Center</h1>
          <p className="text-muted-foreground">
            Platform overview and system status
          </p>
        </div>
      </div>

      {/* KPIs */}
      <KPISection />

      {/* System Status */}
      <SystemStatusSection />

      {/* Alerts and Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        <AlertsSection />
        <ActivitySection />
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Campaigns Running
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats ? "—" : "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              across {stats?.active_clients ?? "—"} clients
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Leads Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.leads_today?.toLocaleString() ?? "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.leads_change ? `${stats.leads_change > 0 ? "+" : ""}${stats.leads_change.toFixed(1)}% vs yesterday` : "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              AI Budget Used
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats ? `${Math.round((Number(stats.ai_spend_today) / Number(stats.ai_spend_limit)) * 100)}%` : "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              ${stats ? Number(stats.ai_spend_today).toFixed(2) : "—"} of ${stats ? Number(stats.ai_spend_limit).toFixed(0) : "—"} daily limit
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
