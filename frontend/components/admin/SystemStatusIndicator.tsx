/**
 * FILE: frontend/components/admin/SystemStatusIndicator.tsx
 * PURPOSE: System status grid for admin dashboard
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Components
 */

"use client";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export interface ServiceStatus {
  name: string;
  status: "healthy" | "degraded" | "down";
  latency?: number;
  message?: string;
}

interface SystemStatusIndicatorProps {
  services: ServiceStatus[];
  loading?: boolean;
  className?: string;
}

export function SystemStatusIndicator({
  services,
  loading = false,
  className,
}: SystemStatusIndicatorProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-16 w-32" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusColor = (status: ServiceStatus["status"]) => {
    switch (status) {
      case "healthy":
        return "bg-green-500";
      case "degraded":
        return "bg-yellow-500";
      case "down":
        return "bg-red-500";
    }
  };

  const getStatusLabel = (status: ServiceStatus["status"]) => {
    switch (status) {
      case "healthy":
        return "Healthy";
      case "degraded":
        return "Degraded";
      case "down":
        return "Down";
    }
  };

  const allHealthy = services.every((s) => s.status === "healthy");
  const hasCritical = services.some((s) => s.status === "down");

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">System Status</CardTitle>
          <div className="flex items-center gap-2">
            <div
              className={cn(
                "h-2 w-2 rounded-full",
                allHealthy ? "bg-green-500" : hasCritical ? "bg-red-500" : "bg-yellow-500"
              )}
            />
            <span className="text-xs text-muted-foreground">
              {allHealthy ? "All Systems Operational" : hasCritical ? "System Issues" : "Degraded Performance"}
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4">
          {services.map((service) => (
            <div
              key={service.name}
              className="flex flex-col items-center gap-1 rounded-lg border p-3 min-w-[100px]"
            >
              <div className="flex items-center gap-2">
                <div
                  className={cn(
                    "h-2.5 w-2.5 rounded-full animate-pulse",
                    getStatusColor(service.status)
                  )}
                />
                <span className="text-sm font-medium">{service.name}</span>
              </div>
              <span className="text-xs text-muted-foreground">
                {getStatusLabel(service.status)}
              </span>
              {service.latency !== undefined && (
                <span className="text-xs text-muted-foreground">
                  {service.latency}ms
                </span>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
