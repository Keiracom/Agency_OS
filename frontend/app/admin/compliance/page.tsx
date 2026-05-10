/**
 * FILE: frontend/app/admin/compliance/page.tsx
 * PURPOSE: Compliance overview for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Compliance Overview
 */

"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { createBrowserClient } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Shield,
  AlertTriangle,
  XCircle,
  PhoneOff,
  ArrowRight,
  CheckCircle,
} from "lucide-react";

// Phase 4 admin Tier B wiring (2026-05-10): aggregates from
// `email_suppression` + `email_events` (last 30d). bounceRate needs a
// sent-count denominator from activities — deferred (pre-revenue 0
// sent). dncrBlocks = 0 (voice channel; 0 calls fired). lastAudit
// defaults to epoch (UI shows "—").
type ComplianceData = {
  suppressionCount: number;
  bounceRate: number;
  spamComplaints: number;
  dncrBlocks: number;
  lastAudit: Date;
  status: "healthy" | "issues";
  recentIssues: Array<{ type: string; count: number; client: string }>;
};

async function fetchCompliance(): Promise<ComplianceData> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const [{ count: suppressionCount }, { data: events }] = await Promise.all([
    client.from("email_suppression").select("*", { count: "exact", head: true }).is("deleted_at", null),
    client
      .from("email_events")
      .select("event_type, clients(name)")
      .in("event_type", ["bounce", "hard_bounce", "soft_bounce", "spam", "complaint"])
      .gte("event_at", new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString()),
  ]);
  const eventRows = (events ?? []) as Array<{ event_type: string; clients: { name: string | null } | null }>;
  const totalBounceish = eventRows.length;
  const spamComplaints = eventRows.filter((r) => r.event_type === "spam" || r.event_type === "complaint").length;
  const grouped = new Map<string, number>();
  for (const r of eventRows) {
    const bucket = r.event_type === "spam" || r.event_type === "complaint" ? "spam" : "bounce";
    const c = r.clients?.name ?? "Unknown";
    const key = `${bucket}::${c}`;
    grouped.set(key, (grouped.get(key) ?? 0) + 1);
  }
  const recentIssues = Array.from(grouped.entries())
    .map(([key, count]) => {
      const [type, c] = key.split("::");
      return { type, count, client: c };
    })
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);
  return {
    suppressionCount: suppressionCount ?? 0,
    bounceRate: 0,
    spamComplaints,
    dncrBlocks: 0,
    lastAudit: new Date(0),
    status: totalBounceish > 50 ? "issues" : "healthy",
    recentIssues,
  };
}

const EMPTY_COMPLIANCE: ComplianceData = {
  suppressionCount: 0,
  bounceRate: 0,
  spamComplaints: 0,
  dncrBlocks: 0,
  lastAudit: new Date(0),
  status: "healthy",
  recentIssues: [],
};

export default function AdminCompliancePage() {
  const { data: mockCompliance = EMPTY_COMPLIANCE } = useQuery({
    queryKey: ["admin-compliance"],
    queryFn: fetchCompliance,
    staleTime: 30 * 1000,
  });
  const bounceStatus = mockCompliance.bounceRate < 2 ? "good" : mockCompliance.bounceRate < 5 ? "warning" : "critical";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Compliance</h1>
          <p className="text-muted-foreground">
            Email deliverability and regulatory compliance
          </p>
        </div>
        <Badge
          variant="outline"
          className={
            mockCompliance.status === "healthy"
              ? "bg-amber/10 text-amber"
              : "bg-yellow-500/10 text-yellow-700"
          }
        >
          <CheckCircle className="mr-1 h-3 w-3" />
          {mockCompliance.status === "healthy" ? "All Systems Compliant" : "Issues Detected"}
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Suppression List
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockCompliance.suppressionCount.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">emails blocked</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Bounce Rate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              bounceStatus === "good" ? "text-amber" :
              bounceStatus === "warning" ? "text-yellow-600" : "text-amber"
            }`}>
              {mockCompliance.bounceRate}%
            </div>
            <p className="text-xs text-muted-foreground">
              {bounceStatus === "good" ? "Healthy" : bounceStatus === "warning" ? "Monitor" : "Action needed"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <XCircle className="h-4 w-4" />
              Spam Complaints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${mockCompliance.spamComplaints > 10 ? "text-amber" : ""}`}>
              {mockCompliance.spamComplaints}
            </div>
            <p className="text-xs text-muted-foreground">this month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <PhoneOff className="h-4 w-4" />
              DNCR Blocks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockCompliance.dncrBlocks}</div>
            <p className="text-xs text-muted-foreground">Australian registry</p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Links */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Suppression List
                </CardTitle>
                <CardDescription>Manage blocked emails</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/compliance/suppression">
                  Manage
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Spam complaints</span>
                <span>{mockCompliance.suppressionCount * 0.15 | 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Unsubscribes</span>
                <span>{mockCompliance.suppressionCount * 0.45 | 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Bounces</span>
                <span>{mockCompliance.suppressionCount * 0.30 | 0}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Manual blocks</span>
                <span>{mockCompliance.suppressionCount * 0.10 | 0}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5" />
                  Bounce Tracker
                </CardTitle>
                <CardDescription>Monitor email deliverability</CardDescription>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/admin/compliance/bounces">
                  View All
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockCompliance.recentIssues.map((issue, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      className={
                        issue.type === "spam"
                          ? "bg-amber-glow text-error"
                          : issue.type === "bounce"
                          ? "bg-yellow-500/10 text-yellow-700"
                          : "bg-bg-surface0/10 text-ink-3"
                      }
                    >
                      {issue.type}
                    </Badge>
                    <span className="text-muted-foreground">{issue.client}</span>
                  </div>
                  <span className="font-medium">{issue.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Compliance Guidelines */}
      <Card>
        <CardHeader>
          <CardTitle>Compliance Thresholds</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Bounce Rate</p>
              <p className="text-lg font-medium">&lt; 2%</p>
              <Badge variant="outline" className="mt-2 bg-amber/10 text-amber">
                Target
              </Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Bounce Rate</p>
              <p className="text-lg font-medium">2-5%</p>
              <Badge variant="outline" className="mt-2 bg-yellow-500/10 text-yellow-700">
                Warning
              </Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Bounce Rate</p>
              <p className="text-lg font-medium">&gt; 5%</p>
              <Badge variant="outline" className="mt-2 bg-amber-glow text-error">
                Critical
              </Badge>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Spam Complaints</p>
              <p className="text-lg font-medium">&lt; 0.1%</p>
              <Badge variant="outline" className="mt-2 bg-amber/10 text-amber">
                Industry Standard
              </Badge>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
