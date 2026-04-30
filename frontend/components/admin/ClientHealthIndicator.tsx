/**
 * FILE: frontend/components/admin/ClientHealthIndicator.tsx
 * PURPOSE: Client health score indicator for admin dashboard
 * PHASE: Admin Dashboard
 * TASK: Admin Dashboard Components
 */

"use client";

import { cn } from "@/lib/utils";

interface ClientHealthIndicatorProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

export function ClientHealthIndicator({
  score,
  size = "md",
  showLabel = true,
  className,
}: ClientHealthIndicatorProps) {
  const getHealthColor = () => {
    if (score >= 70) return "text-amber bg-amber";
    if (score >= 40) return "text-yellow-600 bg-yellow-500";
    return "text-amber bg-amber";
  };

  const getHealthLabel = () => {
    if (score >= 70) return "Healthy";
    if (score >= 40) return "At Risk";
    return "Critical";
  };

  const getSizeClasses = () => {
    switch (size) {
      case "sm":
        return "h-6 w-6 text-xs";
      case "lg":
        return "h-12 w-12 text-lg";
      default:
        return "h-8 w-8 text-sm";
    }
  };

  const colorClass = getHealthColor();
  const sizeClass = getSizeClasses();

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div
        className={cn(
          "rounded-full flex items-center justify-center font-bold text-ink",
          sizeClass,
          colorClass.split(" ")[1]
        )}
      >
        {score}
      </div>
      {showLabel && (
        <span className={cn("text-sm", colorClass.split(" ")[0])}>
          {getHealthLabel()}
        </span>
      )}
    </div>
  );
}

interface ClientHealthBadgeProps {
  score: number;
  className?: string;
}

export function ClientHealthBadge({ score, className }: ClientHealthBadgeProps) {
  const getHealthColor = () => {
    if (score >= 70) return "bg-amber/10 text-amber border-amber/20";
    if (score >= 40) return "bg-yellow-500/10 text-yellow-700 border-yellow-500/20";
    return "bg-amber-glow text-error border-amber/20";
  };

  const getHealthLabel = () => {
    if (score >= 70) return "Healthy";
    if (score >= 40) return "At Risk";
    return "Critical";
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        getHealthColor(),
        className
      )}
    >
      <span className="font-bold">{score}</span>
      <span>{getHealthLabel()}</span>
    </span>
  );
}
