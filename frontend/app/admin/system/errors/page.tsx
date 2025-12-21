/**
 * FILE: frontend/app/admin/system/errors/page.tsx
 * PURPOSE: Error log for admin (Sentry integration)
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard - Errors
 */

"use client";

import { useState } from "react";
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

// Mock data
const mockErrors: ErrorEntry[] = [
  {
    id: "1",
    timestamp: new Date(Date.now() - 1000 * 60 * 23),
    type: "ConnectionTimeout",
    message: "Connection to Apollo API timed out after 30s",
    service: "apollo.py",
    count: 3,
    level: "error",
    resolved: false,
  },
  {
    id: "2",
    timestamp: new Date(Date.now() - 1000 * 60 * 59),
    type: "RateLimitExceeded",
    message: "HeyReach rate limit exceeded for seat_123",
    service: "heyreach.py",
    count: 1,
    level: "warning",
    resolved: false,
  },
  {
    id: "3",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 2),
    type: "ValidationError",
    message: "Invalid email format: user@.com",
    service: "scout.py",
    count: 2,
    level: "warning",
    resolved: true,
  },
  {
    id: "4",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 4),
    type: "AuthenticationError",
    message: "Twilio authentication failed - invalid API key",
    service: "twilio.py",
    count: 5,
    level: "error",
    resolved: true,
  },
  {
    id: "5",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 6),
    type: "DatabaseError",
    message: "Connection pool exhausted",
    service: "supabase.py",
    count: 1,
    level: "error",
    resolved: true,
  },
  {
    id: "6",
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 8),
    type: "AISpendLimitError",
    message: "Daily AI spend limit reached: $500/$500",
    service: "anthropic.py",
    count: 1,
    level: "error",
    resolved: true,
  },
];

const levelColors = {
  error: "bg-red-500/10 text-red-700 border-red-500/20",
  warning: "bg-yellow-500/10 text-yellow-700 border-yellow-500/20",
  info: "bg-blue-500/10 text-blue-700 border-blue-500/20",
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
            <div className="text-2xl font-bold text-red-600">{unresolvedCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Errors
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{errorCount}</div>
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
                      <Badge variant="outline" className="bg-green-500/10 text-green-700">
                        Resolved
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="bg-red-500/10 text-red-700">
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
