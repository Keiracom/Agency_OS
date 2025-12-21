/**
 * FILE: frontend/app/admin/system/rate-limits/page.tsx
 * PURPOSE: Rate limit status for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Rate Limits
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface RateLimit {
  service: string;
  resource: string;
  used: number;
  limit: number;
  resets: string;
  status: "ok" | "warning" | "critical";
}

interface ClientLimit {
  client: string;
  emailUsed: number;
  emailLimit: number;
  smsUsed: number;
  smsLimit: number;
  linkedinUsed: number;
  linkedinLimit: number;
}

// Mock data
const mockRateLimits: RateLimit[] = [
  { service: "Apollo", resource: "API Enrichments", used: 80, limit: 100, resets: "2:00 PM", status: "warning" },
  { service: "HeyReach", resource: "LinkedIn Actions", used: 15, limit: 17, resets: "Midnight", status: "warning" },
  { service: "Resend", resource: "Emails", used: 1847, limit: 10000, resets: "Midnight", status: "ok" },
  { service: "Twilio", resource: "SMS", used: 234, limit: 1000, resets: "Midnight", status: "ok" },
  { service: "Synthflow", resource: "Voice Calls", used: 12, limit: 50, resets: "Midnight", status: "ok" },
  { service: "Lob", resource: "Mail Pieces", used: 5, limit: 100, resets: "Midnight", status: "ok" },
  { service: "Anthropic", resource: "AI Spend ($)", used: 89, limit: 500, resets: "Midnight", status: "ok" },
];

const mockClientLimits: ClientLimit[] = [
  { client: "LeadGen Pro", emailUsed: 45, emailLimit: 50, smsUsed: 78, smsLimit: 100, linkedinUsed: 15, linkedinLimit: 17 },
  { client: "GrowthLab", emailUsed: 32, emailLimit: 50, smsUsed: 45, smsLimit: 100, linkedinUsed: 12, linkedinLimit: 17 },
  { client: "Enterprise Co", emailUsed: 28, emailLimit: 50, smsUsed: 34, smsLimit: 100, linkedinUsed: 8, linkedinLimit: 17 },
  { client: "ScaleUp Co", emailUsed: 18, emailLimit: 50, smsUsed: 23, smsLimit: 100, linkedinUsed: 5, linkedinLimit: 17 },
];

export default function AdminRateLimitsPage() {
  const warningCount = mockRateLimits.filter((r) => r.status === "warning").length;
  const criticalCount = mockRateLimits.filter((r) => r.status === "critical").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Rate Limits</h1>
          <p className="text-muted-foreground">
            Resource usage and API limits across all services
          </p>
        </div>
        <Button variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Alert if near limits */}
      {(warningCount > 0 || criticalCount > 0) && (
        <div className="flex items-center gap-3 rounded-lg border border-yellow-500/20 bg-yellow-500/10 p-4 text-yellow-700">
          <AlertTriangle className="h-5 w-5" />
          <div>
            <p className="font-medium">Rate limits approaching</p>
            <p className="text-sm opacity-80">
              {warningCount} services at 80%+ capacity. Consider adjusting outreach volume.
            </p>
          </div>
        </div>
      )}

      {/* Service Rate Limits */}
      <Card>
        <CardHeader>
          <CardTitle>Service Rate Limits</CardTitle>
          <CardDescription>
            Current usage vs daily limits for each integration
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {mockRateLimits.map((limit) => {
            const percentage = Math.round((limit.used / limit.limit) * 100);
            const progressColor =
              limit.status === "critical"
                ? "bg-red-500"
                : limit.status === "warning"
                ? "bg-yellow-500"
                : "";

            return (
              <div key={limit.service} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{limit.service}</span>
                    <span className="text-sm text-muted-foreground">
                      ({limit.resource})
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm">
                      {limit.used.toLocaleString()} / {limit.limit.toLocaleString()}
                    </span>
                    {limit.status !== "ok" && (
                      <Badge
                        variant="outline"
                        className={
                          limit.status === "critical"
                            ? "bg-red-500/10 text-red-700"
                            : "bg-yellow-500/10 text-yellow-700"
                        }
                      >
                        {percentage}%
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div
                    className={`h-full ${progressColor || "bg-primary"}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Resets: {limit.resets}
                </p>
              </div>
            );
          })}
        </CardContent>
      </Card>

      {/* Per-Client Limits */}
      <Card>
        <CardHeader>
          <CardTitle>Client Usage</CardTitle>
          <CardDescription>
            Per-client rate limit consumption (daily limits per resource)
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Client</TableHead>
                <TableHead>Email (50/day/domain)</TableHead>
                <TableHead>SMS (100/day/number)</TableHead>
                <TableHead>LinkedIn (17/day/seat)</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockClientLimits.map((client) => (
                <TableRow key={client.client}>
                  <TableCell className="font-medium">{client.client}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress
                        value={(client.emailUsed / client.emailLimit) * 100}
                        className="h-2 w-20"
                      />
                      <span className="text-sm text-muted-foreground">
                        {client.emailUsed}/{client.emailLimit}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress
                        value={(client.smsUsed / client.smsLimit) * 100}
                        className="h-2 w-20"
                      />
                      <span className="text-sm text-muted-foreground">
                        {client.smsUsed}/{client.smsLimit}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress
                        value={(client.linkedinUsed / client.linkedinLimit) * 100}
                        className="h-2 w-20"
                      />
                      <span className="text-sm text-muted-foreground">
                        {client.linkedinUsed}/{client.linkedinLimit}
                      </span>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Rate Limit Rules */}
      <Card>
        <CardHeader>
          <CardTitle>Rate Limit Rules (Rule 17)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 border rounded-lg">
              <p className="font-medium">Email</p>
              <p className="text-2xl font-bold">50/day</p>
              <p className="text-sm text-muted-foreground">per domain</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="font-medium">SMS</p>
              <p className="text-2xl font-bold">100/day</p>
              <p className="text-sm text-muted-foreground">per phone number</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="font-medium">LinkedIn</p>
              <p className="text-2xl font-bold">17/day</p>
              <p className="text-sm text-muted-foreground">per seat</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
