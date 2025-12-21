/**
 * FILE: frontend/app/admin/page.tsx
 * PURPOSE: Admin Command Center - main dashboard
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Foundation
 */

import { Suspense } from "react";
import { DollarSign, Users, Target, Cpu } from "lucide-react";
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

// Mock data - would be fetched from API in production
const mockKPIs = {
  mrr: 47500,
  mrrChange: 12,
  activeClients: 19,
  newClients: 2,
  leadsToday: 1247,
  aiSpend: 89,
  aiLimit: 500,
};

const mockAlerts: Alert[] = [
  {
    id: "1",
    severity: "critical",
    message: 'Client "GrowthLab" - 3 failed enrichments',
    timestamp: new Date(Date.now() - 1000 * 60 * 15),
    link: "/admin/clients/growthlab",
    dismissible: true,
  },
  {
    id: "2",
    severity: "warning",
    message: "Apollo API rate limit 80% consumed",
    timestamp: new Date(Date.now() - 1000 * 60 * 30),
    link: "/admin/system/rate-limits",
    dismissible: true,
  },
  {
    id: "3",
    severity: "warning",
    message: 'Client "ScaleUp" - no activity 48hrs',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
    link: "/admin/clients/scaleup",
    dismissible: true,
  },
];

const mockServices: ServiceStatus[] = [
  { name: "API", status: "healthy", latency: 45 },
  { name: "Database", status: "healthy", latency: 12 },
  { name: "Redis", status: "healthy", latency: 3 },
  { name: "Prefect", status: "healthy", message: "2 running" },
  { name: "Webhooks", status: "healthy" },
];

const mockActivities: Activity[] = [
  {
    id: "1",
    client_name: "LeadGen Pro",
    action: "email_sent",
    details: "Email sent to john@acme.com",
    timestamp: new Date(Date.now() - 1000 * 60 * 2),
    channel: "email",
  },
  {
    id: "2",
    client_name: "GrowthLab",
    action: "lead_enriched",
    details: "Lead enriched (ALS: 78)",
    timestamp: new Date(Date.now() - 1000 * 60 * 3),
  },
  {
    id: "3",
    client_name: "ScaleUp Co",
    action: "reply_received",
    details: "Reply received (interested)",
    timestamp: new Date(Date.now() - 1000 * 60 * 3),
    channel: "email",
  },
  {
    id: "4",
    client_name: "LeadGen Pro",
    action: "linkedin_sent",
    details: "LinkedIn connection sent",
    timestamp: new Date(Date.now() - 1000 * 60 * 4),
    channel: "linkedin",
  },
  {
    id: "5",
    client_name: "Marketing Plus",
    action: "sms_sent",
    details: "SMS sent to +1234567890",
    timestamp: new Date(Date.now() - 1000 * 60 * 5),
    channel: "sms",
  },
  {
    id: "6",
    client_name: "GrowthLab",
    action: "voice_call",
    details: "Voice call completed (2m 34s)",
    timestamp: new Date(Date.now() - 1000 * 60 * 8),
    channel: "voice",
  },
  {
    id: "7",
    client_name: "Enterprise Co",
    action: "mail_sent",
    details: "Direct mail queued",
    timestamp: new Date(Date.now() - 1000 * 60 * 10),
    channel: "mail",
  },
];

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

async function KPISection() {
  // In production, fetch from API:
  // const stats = await fetch('/api/v1/admin/stats').then(r => r.json())

  const aiSpendPercent = Math.round((mockKPIs.aiSpend / mockKPIs.aiLimit) * 100);

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <KPICard
        title="MRR"
        value={`$${mockKPIs.mrr.toLocaleString()}`}
        change={mockKPIs.mrrChange}
        changeLabel="MoM"
        icon={<DollarSign className="h-4 w-4" />}
      />
      <KPICard
        title="Active Clients"
        value={mockKPIs.activeClients}
        change={mockKPIs.newClients}
        changeLabel="new this month"
        icon={<Users className="h-4 w-4" />}
      />
      <KPICard
        title="Leads Today"
        value={mockKPIs.leadsToday.toLocaleString()}
        icon={<Target className="h-4 w-4" />}
      />
      <KPICard
        title="AI Spend Today"
        value={`$${mockKPIs.aiSpend} / $${mockKPIs.aiLimit}`}
        change={aiSpendPercent}
        changeLabel="of daily limit"
        icon={<Cpu className="h-4 w-4" />}
      />
    </div>
  );
}

async function SystemStatusSection() {
  // In production, fetch from API:
  // const status = await fetch('/api/v1/admin/system/status').then(r => r.json())

  return <SystemStatusIndicator services={mockServices} />;
}

async function AlertsSection() {
  // In production, fetch from API:
  // const alerts = await fetch('/api/v1/admin/alerts').then(r => r.json())

  return <AlertBanner alerts={mockAlerts} />;
}

async function ActivitySection() {
  // In production, fetch from API:
  // const activity = await fetch('/api/v1/admin/activity?limit=10').then(r => r.json())

  return <LiveActivityFeed activities={mockActivities} maxItems={10} />;
}

export default function AdminCommandCenter() {
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
      <Suspense fallback={<KPISkeleton />}>
        <KPISection />
      </Suspense>

      {/* System Status */}
      <Suspense
        fallback={
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
        }
      >
        <SystemStatusSection />
      </Suspense>

      {/* Alerts and Activity */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Suspense
          fallback={
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Alerts</CardTitle>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          }
        >
          <AlertsSection />
        </Suspense>

        <Suspense
          fallback={
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Live Activity</CardTitle>
              </CardHeader>
              <CardContent>
                <Skeleton className="h-32 w-full" />
              </CardContent>
            </Card>
          }
        >
          <ActivitySection />
        </Suspense>
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
            <div className="text-2xl font-bold">23</div>
            <p className="text-xs text-muted-foreground">across 19 clients</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Emails Sent Today
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">1,847</div>
            <p className="text-xs text-muted-foreground">2.3% reply rate</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending Approvals
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12</div>
            <p className="text-xs text-muted-foreground">co-pilot mode content</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
