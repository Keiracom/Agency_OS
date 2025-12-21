/**
 * FILE: frontend/components/admin/AlertBanner.tsx
 * PURPOSE: System alerts banner for admin dashboard
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Components
 */

"use client";

import { cn } from "@/lib/utils";
import { AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export interface Alert {
  id: string;
  severity: "critical" | "warning" | "info";
  message: string;
  timestamp: Date;
  link?: string;
  dismissible?: boolean;
}

interface AlertBannerProps {
  alerts: Alert[];
  onDismiss?: (id: string) => void;
  className?: string;
}

export function AlertBanner({ alerts, onDismiss, className }: AlertBannerProps) {
  if (alerts.length === 0) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Alerts</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No active alerts</p>
        </CardContent>
      </Card>
    );
  }

  const getSeverityIcon = (severity: Alert["severity"]) => {
    switch (severity) {
      case "critical":
        return <AlertCircle className="h-4 w-4" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4" />;
      case "info":
        return <Info className="h-4 w-4" />;
    }
  };

  const getSeverityColor = (severity: Alert["severity"]) => {
    switch (severity) {
      case "critical":
        return "bg-red-500/10 border-red-500/20 text-red-700 dark:text-red-400";
      case "warning":
        return "bg-yellow-500/10 border-yellow-500/20 text-yellow-700 dark:text-yellow-400";
      case "info":
        return "bg-blue-500/10 border-blue-500/20 text-blue-700 dark:text-blue-400";
    }
  };

  const getSeverityDot = (severity: Alert["severity"]) => {
    switch (severity) {
      case "critical":
        return "bg-red-500";
      case "warning":
        return "bg-yellow-500";
      case "info":
        return "bg-blue-500";
    }
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          Alerts
          <span className="inline-flex items-center justify-center rounded-full bg-red-500 px-2 py-0.5 text-xs text-white">
            {alerts.length}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {alerts.map((alert) => (
          <div
            key={alert.id}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-3",
              getSeverityColor(alert.severity)
            )}
          >
            <div className={cn("mt-0.5 h-2 w-2 rounded-full shrink-0", getSeverityDot(alert.severity))} />
            <div className="flex-1 min-w-0">
              {alert.link ? (
                <Link href={alert.link} className="text-sm hover:underline">
                  {alert.message}
                </Link>
              ) : (
                <p className="text-sm">{alert.message}</p>
              )}
              <p className="text-xs opacity-70 mt-1">
                {formatTimeAgo(alert.timestamp)}
              </p>
            </div>
            {alert.dismissible && onDismiss && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 shrink-0"
                onClick={() => onDismiss(alert.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "Just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
