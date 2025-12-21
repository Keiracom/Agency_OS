/**
 * FILE: frontend/app/admin/system/page.tsx
 * PURPOSE: System status dashboard for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - System Status
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
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Database,
  Server,
  Wifi,
  Activity,
} from "lucide-react";

// Mock data
const mockServices = [
  { name: "API", status: "healthy", latency: 45, uptime: "99.9%" },
  { name: "Database", status: "healthy", latency: 12, uptime: "99.99%" },
  { name: "Redis", status: "healthy", latency: 3, uptime: "99.95%" },
  { name: "Prefect", status: "healthy", latency: 156, uptime: "99.8%" },
  { name: "Webhooks", status: "healthy", latency: 23, uptime: "99.9%" },
];

const mockFlows = [
  {
    name: "daily-enrichment",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 10),
    status: "success",
    duration: "12m 34s",
    nextRun: "Tomorrow 2:00 AM",
  },
  {
    name: "hourly-outreach",
    lastRun: new Date(Date.now() - 1000 * 60 * 45),
    status: "success",
    duration: "3m 12s",
    nextRun: "3:00 PM",
  },
  {
    name: "reply-recovery",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 4),
    status: "success",
    duration: "1m 45s",
    nextRun: "6:00 PM",
  },
  {
    name: "billing-sync",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 2),
    status: "success",
    duration: "0m 34s",
    nextRun: "Midnight",
  },
];

const mockErrors = [
  {
    time: new Date(Date.now() - 1000 * 60 * 37),
    error: "ConnectionTimeout",
    service: "apollo.py",
    count: 3,
  },
  {
    time: new Date(Date.now() - 1000 * 60 * 59),
    error: "RateLimitExceeded",
    service: "heyreach.py",
    count: 1,
  },
  {
    time: new Date(Date.now() - 1000 * 60 * 60 * 3),
    error: "ValidationError",
    service: "scout.py",
    count: 2,
  },
];

const mockDbStats = {
  connections: { active: 5, max: 10 },
  latency: { p50: 12, p95: 45, p99: 120 },
  tables: [
    { name: "leads", rows: "2.4M", size: "1.2GB" },
    { name: "activities", rows: "12.8M", size: "4.5GB" },
    { name: "campaigns", rows: "156", size: "2MB" },
    { name: "clients", rows: "19", size: "128KB" },
  ],
};

const mockRateLimits = [
  { service: "Apollo", used: 80, limit: 100, resets: "2:00 PM" },
  { service: "HeyReach", used: 45, limit: 100, resets: "Midnight" },
  { service: "Resend", used: 1847, limit: 10000, resets: "Midnight" },
  { service: "Twilio", used: 234, limit: 1000, resets: "Midnight" },
];

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminSystemPage() {
  const allHealthy = mockServices.every((s) => s.status === "healthy");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Status</h1>
          <p className="text-muted-foreground">
            Infrastructure health and monitoring
          </p>
        </div>
        <Badge
          className={
            allHealthy
              ? "bg-green-500/10 text-green-700"
              : "bg-yellow-500/10 text-yellow-700"
          }
        >
          {allHealthy ? "All Systems Operational" : "Degraded Performance"}
        </Badge>
      </div>

      {/* Services Grid */}
      <div className="grid gap-4 md:grid-cols-5">
        {mockServices.map((service) => (
          <Card key={service.name}>
            <CardContent className="pt-6">
              <div className="flex flex-col items-center text-center gap-2">
                <div
                  className={`h-3 w-3 rounded-full ${
                    service.status === "healthy"
                      ? "bg-green-500 animate-pulse"
                      : service.status === "degraded"
                      ? "bg-yellow-500"
                      : "bg-red-500"
                  }`}
                />
                <span className="font-medium">{service.name}</span>
                <span className="text-sm text-muted-foreground">
                  {service.status === "healthy" ? "Healthy" : service.status}
                </span>
                <span className="text-xs text-muted-foreground">
                  {service.latency}ms avg
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Prefect Flows */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Prefect Flows
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Flow</TableHead>
                <TableHead>Last Run</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Next Run</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockFlows.map((flow) => (
                <TableRow key={flow.name}>
                  <TableCell className="font-mono">{flow.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatTimeAgo(flow.lastRun)}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {flow.status === "success" ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : flow.status === "failed" ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                      ) : (
                        <Clock className="h-4 w-4 text-yellow-500" />
                      )}
                      <span className="capitalize">{flow.status}</span>
                    </div>
                  </TableCell>
                  <TableCell>{flow.duration}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {flow.nextRun}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Recent Errors */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-yellow-500" />
            Recent Errors
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Error</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Count</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockErrors.map((error, i) => (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">
                    {formatTimeAgo(error.time)}
                  </TableCell>
                  <TableCell className="font-mono text-red-600">
                    {error.error}
                  </TableCell>
                  <TableCell className="font-mono">{error.service}</TableCell>
                  <TableCell>{error.count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Database Stats */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Database Stats
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex justify-between items-center p-3 border rounded-lg">
              <span className="text-muted-foreground">Connection Pool</span>
              <span className="font-medium">
                {mockDbStats.connections.active}/{mockDbStats.connections.max}{" "}
                active
              </span>
            </div>
            <div className="flex justify-between items-center p-3 border rounded-lg">
              <span className="text-muted-foreground">Query Latency</span>
              <span className="font-medium">
                p50: {mockDbStats.latency.p50}ms | p95:{" "}
                {mockDbStats.latency.p95}ms | p99: {mockDbStats.latency.p99}ms
              </span>
            </div>
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Table</TableHead>
                    <TableHead>Rows</TableHead>
                    <TableHead>Size</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {mockDbStats.tables.map((table) => (
                    <TableRow key={table.name}>
                      <TableCell className="font-mono">{table.name}</TableCell>
                      <TableCell>{table.rows}</TableCell>
                      <TableCell>{table.size}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* Rate Limits */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Wifi className="h-5 w-5" />
              Rate Limits
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {mockRateLimits.map((limit) => {
              const percent = Math.round((limit.used / limit.limit) * 100);
              const isHigh = percent >= 80;
              return (
                <div key={limit.service} className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="font-medium">{limit.service}</span>
                    <span
                      className={`text-sm ${
                        isHigh ? "text-yellow-600" : "text-muted-foreground"
                      }`}
                    >
                      {limit.used.toLocaleString()} /{" "}
                      {limit.limit.toLocaleString()} ({percent}%)
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        isHigh ? "bg-yellow-500" : "bg-primary"
                      }`}
                      style={{ width: `${percent}%` }}
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
      </div>
    </div>
  );
}
