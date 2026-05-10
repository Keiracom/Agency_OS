/**
 * FILE: frontend/app/admin/system/errors/page.tsx
 * PURPOSE: Error log for admin (Sentry integration)
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Errors
 */

"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createBrowserClient } from "@/lib/supabase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertTriangle, ExternalLink, RefreshCw } from "lucide-react";

interface ErrorEntry {
  id: string;
  timestamp: Date;
  type: string;
  message: string;
  service: string;
  count: number;
  level: "error" | "warning" | "info";
  resolved: boolean;
}

// Phase 4 admin Tier B wiring (2026-05-10): live `system_errors` table
// from PR #664. Schema: id, source, severity, message, context (jsonb),
// resolved_at, resolved_by, created_at, deleted_at. UI fields mapped:
// - "type": derived from context.type if present, else first token of message
// - "service": source field directly
// - "count": context.count if present, else 1 (system_errors stores per-
//   occurrence rows, not aggregated)
// - "level": severity narrowed to error|warning|info (info if severity is
//   "warning" and not in our enum, default error)
type SystemErrorRow = {
  id: string;
  source: string;
  severity: string;
  message: string;
  context: Record<string, unknown> | null;
  resolved_at: string | null;
  created_at: string;
};

function severityToLevel(s: string): "error" | "warning" | "info" {
  if (s === "warning") return "warning";
  if (s === "info") return "info";
  return "error";
}

async function fetchSystemErrors(): Promise<ErrorEntry[]> {
  const sb = createBrowserClient();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const client = sb as any;
  const { data, error } = await client
    .from("system_errors")
    .select("id, source, severity, message, context, resolved_at, created_at")
    .is("deleted_at", null)
    .order("created_at", { ascending: false })
    .limit(200);
  if (error) throw error;
  return ((data ?? []) as SystemErrorRow[]).map((row) => {
    const ctx = (row.context ?? {}) as Record<string, unknown>;
    const type = (typeof ctx.type === "string" ? ctx.type : null)
      ?? row.message.split(/[\s:]/)[0]
      ?? "Error";
    const count = typeof ctx.count === "number" ? ctx.count : 1;
    return {
      id: row.id,
      timestamp: new Date(row.created_at),
      type,
      message: row.message,
      service: row.source,
      count,
      level: severityToLevel(row.severity),
      resolved: row.resolved_at !== null,
    };
  });
}

const levelColors = {
  error: "bg-amber-glow text-error border-amber/20",
  warning: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  info: "bg-panel/10 text-amber border-default/20",
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export default function AdminErrorsPage() {
  const [levelFilter, setLevelFilter] = useState("all");
  const [resolvedFilter, setResolvedFilter] = useState("all");

  const { data: mockErrors = [] } = useQuery({
    queryKey: ["admin-system-errors"],
    queryFn: fetchSystemErrors,
    staleTime: 30 * 1000,
  });

  const filteredErrors = mockErrors.filter((error) => {
    const matchesLevel = levelFilter === "all" || error.level === levelFilter;
    const matchesResolved =
      resolvedFilter === "all" ||
      (resolvedFilter === "unresolved" && !error.resolved) ||
      (resolvedFilter === "resolved" && error.resolved);
    return matchesLevel && matchesResolved;
  });

  const unresolvedCount = mockErrors.filter((e) => !e.resolved).length;
  const errorCount = mockErrors.filter((e) => e.level === "error").length;
  const warningCount = mockErrors.filter((e) => e.level === "warning").length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Error Log</h1>
          <p className="text-muted-foreground">
            Application errors and warnings from Sentry
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
          <Button variant="outline" asChild>
            <a href="https://sentry.io" target="_blank" rel="noopener noreferrer">
              Open Sentry
              <ExternalLink className="ml-2 h-4 w-4" />
            </a>
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Errors (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockErrors.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Unresolved
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber">{unresolvedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Errors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber">{errorCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Warnings
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{warningCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Select value={levelFilter} onValueChange={setLevelFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Levels</SelectItem>
                <SelectItem value="error">Errors</SelectItem>
                <SelectItem value="warning">Warnings</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
            <Select value={resolvedFilter} onValueChange={setResolvedFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="unresolved">Unresolved</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Error Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Level</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Service</TableHead>
                <TableHead>Count</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredErrors.map((error) => (
                <TableRow key={error.id}>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatTimeAgo(error.timestamp)}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className={levelColors[error.level]}>
                      {error.level}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">{error.type}</TableCell>
                  <TableCell className="max-w-[300px] truncate">
                    {error.message}
                  </TableCell>
                  <TableCell className="font-mono text-sm">{error.service}</TableCell>
                  <TableCell>{error.count}</TableCell>
                  <TableCell>
                    {error.resolved ? (
                      <Badge variant="outline" className="bg-amber/10 text-amber">
                        Resolved
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="bg-amber-glow text-error">
                        Open
                      </Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
