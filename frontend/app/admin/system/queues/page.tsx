/**
 * FILE: frontend/app/admin/system/queues/page.tsx
 * PURPOSE: Prefect queue/flow monitor for admin
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Queues
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  CheckCircle,
  XCircle,
  Clock,
  Play,
  Pause,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

interface Flow {
  id: string;
  name: string;
  lastRun: Date;
  status: "success" | "failed" | "running" | "pending";
  duration: string;
  nextRun: string;
  schedule: string;
}

interface QueueStats {
  active: number;
  pending: number;
  completed: number;
  failed: number;
}

// Mock data
const mockFlows: Flow[] = [
  {
    id: "1",
    name: "daily-enrichment",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 10),
    status: "success",
    duration: "12m 34s",
    nextRun: "Tomorrow 2:00 AM",
    schedule: "0 2 * * *",
  },
  {
    id: "2",
    name: "hourly-outreach",
    lastRun: new Date(Date.now() - 1000 * 60 * 45),
    status: "success",
    duration: "3m 12s",
    nextRun: "3:00 PM",
    schedule: "0 8-18 * * 1-5",
  },
  {
    id: "3",
    name: "reply-recovery",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 4),
    status: "success",
    duration: "1m 45s",
    nextRun: "6:00 PM",
    schedule: "0 */6 * * *",
  },
  {
    id: "4",
    name: "billing-sync",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 2),
    status: "success",
    duration: "0m 34s",
    nextRun: "Midnight",
    schedule: "0 0 * * *",
  },
  {
    id: "5",
    name: "daily-metrics",
    lastRun: new Date(Date.now() - 1000 * 60 * 60 * 24),
    status: "success",
    duration: "2m 15s",
    nextRun: "Midnight",
    schedule: "0 0 * * *",
  },
];

const mockQueueStats: QueueStats = {
  active: 2,
  pending: 5,
  completed: 1247,
  failed: 3,
};

const statusIcons = {
  success: CheckCircle,
  failed: XCircle,
  running: Play,
  pending: Clock,
};

const statusColors = {
  success: "text-green-500",
  failed: "text-red-500",
  running: "text-blue-500",
  pending: "text-yellow-500",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminQueuesPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Prefect Queues</h1>
          <p className="text-muted-foreground">
            Flow status and task queue monitoring
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" asChild>
            <a href="https://prefect.io" target="_blank" rel="noopener noreferrer">
              Open Prefect
              <ExternalLink className="ml-2 h-4 w-4" />
            </a>
          </Button>
        </div>
      </div>

      {/* Queue Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{mockQueueStats.active}</div>
            <p className="text-xs text-muted-foreground">Currently running</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{mockQueueStats.pending}</div>
            <p className="text-xs text-muted-foreground">Waiting to start</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Completed (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{mockQueueStats.completed}</div>
            <p className="text-xs text-muted-foreground">Successfully finished</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Failed (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockQueueStats.failed}</div>
            <p className="text-xs text-muted-foreground">Need attention</p>
          </CardContent>
        </Card>
      </div>

      {/* Flows Table */}
      <Card>
        <CardHeader>
          <CardTitle>Scheduled Flows</CardTitle>
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
                <TableHead>Schedule</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockFlows.map((flow) => {
                const StatusIcon = statusIcons[flow.status];
                return (
                  <TableRow key={flow.id}>
                    <TableCell className="font-mono">{flow.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatTimeAgo(flow.lastRun)}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <StatusIcon className={`h-4 w-4 ${statusColors[flow.status]}`} />
                        <span className="capitalize">{flow.status}</span>
                      </div>
                    </TableCell>
                    <TableCell>{flow.duration}</TableCell>
                    <TableCell className="text-muted-foreground">{flow.nextRun}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {flow.schedule}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Pause className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Work Pool Info */}
      <Card>
        <CardHeader>
          <CardTitle>Work Pool</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Pool Name</p>
              <p className="font-mono font-medium">agency-os-pool</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Queue</p>
              <p className="font-mono font-medium">agency-os-queue</p>
            </div>
            <div className="p-4 border rounded-lg">
              <p className="text-sm text-muted-foreground">Workers</p>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />
                <span className="font-medium">2 active</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
