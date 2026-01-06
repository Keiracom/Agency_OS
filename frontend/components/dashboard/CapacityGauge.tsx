"use client";

/**
 * CapacityGauge.tsx - Monthly Capacity Fuel Gauge
 * Phase 21: Deep Research & UI
 *
 * Visual "fuel gauge" showing:
 * - Active leads vs monthly limit
 * - Email send capacity
 * - Percentage used with color coding
 */

import { useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Fuel, AlertTriangle, CheckCircle2 } from "lucide-react";

interface CapacityGaugeProps {
  current: number;
  limit: number;
  label?: string;
  showPercentage?: boolean;
  variant?: "gauge" | "bar" | "circle";
  warningThreshold?: number;
  criticalThreshold?: number;
}

export function CapacityGauge({
  current,
  limit,
  label = "Monthly Capacity",
  showPercentage = true,
  variant = "gauge",
  warningThreshold = 75,
  criticalThreshold = 90,
}: CapacityGaugeProps) {
  const percentage = useMemo(() => {
    return Math.min(Math.round((current / limit) * 100), 100);
  }, [current, limit]);

  const status = useMemo(() => {
    if (percentage >= criticalThreshold) return "critical";
    if (percentage >= warningThreshold) return "warning";
    return "healthy";
  }, [percentage, warningThreshold, criticalThreshold]);

  const statusConfig = {
    healthy: {
      color: "from-green-500 to-emerald-400",
      bgColor: "bg-green-500/20",
      textColor: "text-green-400",
      icon: CheckCircle2,
      message: "Capacity available",
    },
    warning: {
      color: "from-yellow-500 to-orange-400",
      bgColor: "bg-yellow-500/20",
      textColor: "text-yellow-400",
      icon: AlertTriangle,
      message: "Running low",
    },
    critical: {
      color: "from-red-500 to-orange-500",
      bgColor: "bg-red-500/20",
      textColor: "text-red-400",
      icon: AlertTriangle,
      message: "Near capacity",
    },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;

  // Fuel gauge variant (semicircle)
  if (variant === "gauge") {
    const angle = (percentage / 100) * 180;
    const radius = 70;
    const strokeWidth = 12;

    return (
      <Card className="bg-[#1a1a1f] border-white/10">
        <CardHeader className="pb-2">
          <CardTitle className="text-white text-sm flex items-center gap-2">
            <Fuel className="h-4 w-4 text-blue-400" />
            {label}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col items-center pt-2">
          {/* SVG Gauge */}
          <svg
            viewBox="0 0 160 100"
            className="w-full max-w-[200px]"
          >
            {/* Background arc */}
            <path
              d={`M ${80 - radius} 85 A ${radius} ${radius} 0 0 1 ${80 + radius} 85`}
              fill="none"
              stroke="rgba(255,255,255,0.1)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
            />

            {/* Gradient definition */}
            <defs>
              <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop
                  offset="0%"
                  className={status === "critical" ? "text-red-500" : status === "warning" ? "text-yellow-500" : "text-green-500"}
                  stopColor="currentColor"
                />
                <stop
                  offset="100%"
                  className={status === "critical" ? "text-orange-500" : status === "warning" ? "text-orange-400" : "text-emerald-400"}
                  stopColor="currentColor"
                />
              </linearGradient>
            </defs>

            {/* Filled arc */}
            <path
              d={`M ${80 - radius} 85 A ${radius} ${radius} 0 0 1 ${80 + radius} 85`}
              fill="none"
              stroke="url(#gaugeGradient)"
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              strokeDasharray={`${(angle / 180) * Math.PI * radius} ${Math.PI * radius}`}
            />

            {/* Needle */}
            <g transform={`rotate(${angle - 180}, 80, 85)`}>
              <line
                x1="80"
                y1="85"
                x2="80"
                y2="30"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle cx="80" cy="85" r="6" fill="white" />
              <circle cx="80" cy="85" r="3" fill="#1a1a1f" />
            </g>

            {/* Percentage text */}
            <text
              x="80"
              y="70"
              textAnchor="middle"
              className="fill-white text-2xl font-bold"
              style={{ fontSize: "24px" }}
            >
              {percentage}%
            </text>
          </svg>

          {/* Stats below gauge */}
          <div className="flex items-center justify-between w-full mt-4 px-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-white">
                {current.toLocaleString()}
              </p>
              <p className="text-xs text-gray-500">Used</p>
            </div>
            <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full ${config.bgColor}`}>
              <StatusIcon className={`h-3.5 w-3.5 ${config.textColor}`} />
              <span className={`text-xs font-medium ${config.textColor}`}>
                {config.message}
              </span>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-white">
                {limit.toLocaleString()}
              </p>
              <p className="text-xs text-gray-500">Limit</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Bar variant (horizontal)
  if (variant === "bar") {
    return (
      <Card className="bg-[#1a1a1f] border-white/10">
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Fuel className="h-4 w-4 text-blue-400" />
              {label}
            </CardTitle>
            {showPercentage && (
              <span className={`text-sm font-medium ${config.textColor}`}>
                {percentage}%
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Progress bar */}
          <div className="h-4 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${config.color} rounded-full transition-all duration-500`}
              style={{ width: `${percentage}%` }}
            />
          </div>

          {/* Labels */}
          <div className="flex items-center justify-between text-sm">
            <span className="text-white font-medium">
              {current.toLocaleString()} / {limit.toLocaleString()}
            </span>
            <div className={`flex items-center gap-1.5 ${config.textColor}`}>
              <StatusIcon className="h-3.5 w-3.5" />
              <span className="text-xs">{config.message}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Circle variant
  const circleRadius = 40;
  const circumference = 2 * Math.PI * circleRadius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  return (
    <Card className="bg-[#1a1a1f] border-white/10">
      <CardHeader className="pb-2">
        <CardTitle className="text-white text-sm flex items-center gap-2">
          <Fuel className="h-4 w-4 text-blue-400" />
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-center pt-2">
        <div className="relative">
          <svg width="100" height="100" className="transform -rotate-90">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r={circleRadius}
              fill="none"
              stroke="rgba(255,255,255,0.1)"
              strokeWidth="8"
            />
            {/* Progress circle */}
            <circle
              cx="50"
              cy="50"
              r={circleRadius}
              fill="none"
              stroke={`url(#circleGradient-${status})`}
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-500"
            />
            <defs>
              <linearGradient id={`circleGradient-${status}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={status === "critical" ? "#ef4444" : status === "warning" ? "#eab308" : "#22c55e"} />
                <stop offset="100%" stopColor={status === "critical" ? "#f97316" : status === "warning" ? "#f97316" : "#10b981"} />
              </linearGradient>
            </defs>
          </svg>
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-2xl font-bold text-white">{percentage}%</span>
          </div>
        </div>

        {/* Stats below */}
        <div className="flex items-center justify-between w-full mt-4">
          <div className="text-center flex-1">
            <p className="text-lg font-bold text-white">{current.toLocaleString()}</p>
            <p className="text-xs text-gray-500">Used</p>
          </div>
          <div className="text-center flex-1">
            <p className="text-lg font-bold text-white">{(limit - current).toLocaleString()}</p>
            <p className="text-xs text-gray-500">Remaining</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default CapacityGauge;
