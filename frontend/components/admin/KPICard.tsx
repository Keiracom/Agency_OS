/**
 * FILE: frontend/components/admin/KPICard.tsx
 * PURPOSE: KPI metric card for admin dashboard
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Components
 */

"use client";

import { cn } from "@/lib/utils";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface KPICardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  className?: string;
}

export function KPICard({
  title,
  value,
  change,
  changeLabel = "vs last period",
  icon,
  loading = false,
  className,
}: KPICardProps) {
  if (loading) {
    return (
      <Card className={className}>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-4" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-3 w-20" />
        </CardContent>
      </Card>
    );
  }

  const getChangeIcon = () => {
    if (!change || change === 0) return <Minus className="h-3 w-3" />;
    return change > 0 ? (
      <ArrowUp className="h-3 w-3" />
    ) : (
      <ArrowDown className="h-3 w-3" />
    );
  };

  const getChangeColor = () => {
    if (!change || change === 0) return "text-muted-foreground";
    return change > 0 ? "text-green-600" : "text-red-600";
  };

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {icon && (
          <div className="h-4 w-4 text-muted-foreground">
            {icon}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change !== undefined && (
          <p className={cn("text-xs flex items-center gap-1 mt-1", getChangeColor())}>
            {getChangeIcon()}
            <span>{Math.abs(change)}%</span>
            <span className="text-muted-foreground">{changeLabel}</span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
