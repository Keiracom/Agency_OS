/**
 * FILE: frontend/components/elliot/task-monitor.tsx
 * PURPOSE: Task Monitor component for spawned agents
 * PHASE: Elliot Dashboard
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useTasks, useTaskStats, type TaskStatus, type ElliotTask } from "@/hooks/use-elliot";
import {
  Bot,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Clock,
  Play,
  AlertTriangle,
} from "lucide-react";

const statusConfig: Record<TaskStatus, { icon: typeof Bot; color: string; label: string }> = {
  running: { icon: Play, color: "bg-blue-500", label: "Running" },
  completed: { icon: CheckCircle2, color: "bg-green-500", label: "Completed" },
  failed: { icon: XCircle, color: "bg-red-500", label: "Failed" },
  retry: { icon: RefreshCw, color: "bg-yellow-500", label: "Retry" },
};

function formatDuration(startDate: string, endDate?: string | null): string {
  const start = new Date(startDate);
  const end = endDate ? new Date(endDate) : new Date();
  const diffMs = end.getTime() - start.getTime();
  
  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `${days}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`;
  return `${seconds}s`;
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function TaskCard({ task }: { task: ElliotTask }) {
  const config = statusConfig[task.status];
  const StatusIcon = config.icon;

  return (
    <div className="flex items-start gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50">
      <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${config.color} bg-opacity-20`}>
        <StatusIcon className={`h-5 w-5 ${config.color.replace('bg-', 'text-')}`} />
      </div>
      <div className="flex-1 space-y-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium truncate">{task.label}</span>
          <Badge variant={task.status === "running" ? "default" : task.status === "completed" ? "secondary" : "destructive"}>
            {config.label}
          </Badge>
          {task.retry_count > 0 && (
            <Badge variant="outline" className="text-xs">
              Retry {task.retry_count}/{task.max_retries}
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2">
          {task.task_description}
        </p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDuration(task.created_at, task.completed_at)}
          </span>
          <span>{formatTimeAgo(task.created_at)}</span>
          <span className="font-mono text-[10px] opacity-50 truncate max-w-32">
            {task.session_key.slice(0, 20)}...
          </span>
        </div>
        {task.output_summary && (
          <p className="text-xs text-muted-foreground bg-muted/50 rounded p-2 mt-2 line-clamp-2">
            {task.output_summary}
          </p>
        )}
      </div>
    </div>
  );
}

function StatsCards({ stats }: { stats: { running: number; completed: number; failed: number; retry: number; total: number } }) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Running</CardTitle>
          <Play className="h-4 w-4 text-blue-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.running}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Completed</CardTitle>
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.completed}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Failed</CardTitle>
          <XCircle className="h-4 w-4 text-red-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.failed}</div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Retry</CardTitle>
          <RefreshCw className="h-4 w-4 text-yellow-500" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{stats.retry}</div>
        </CardContent>
      </Card>
    </div>
  );
}

export function TaskMonitor() {
  const [filter, setFilter] = useState<TaskStatus | "all">("all");
  const { data: tasks, isLoading, error, refetch } = useTasks(filter);
  const { data: stats, isLoading: statsLoading } = useTaskStats();

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      {statsLoading ? (
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-20" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-12" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : stats ? (
        <StatsCards stats={stats} />
      ) : null}

      {/* Task List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Spawned Agents</CardTitle>
              <CardDescription>Track and monitor all spawned agent tasks</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={filter} onValueChange={(v) => setFilter(v as TaskStatus | "all")}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="retry">Retry</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-4 rounded-lg border p-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <AlertTriangle className="mr-2 h-5 w-5" />
              Failed to load tasks
            </div>
          ) : !tasks || tasks.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Bot className="h-12 w-12 mb-2 opacity-50" />
              <p>No tasks found</p>
              <p className="text-sm">Spawned agent tasks will appear here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {tasks.map((task) => (
                <TaskCard key={task.id} task={task} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
