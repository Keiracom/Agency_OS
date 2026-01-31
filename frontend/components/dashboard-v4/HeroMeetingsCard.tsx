/**
 * FILE: frontend/components/dashboard-v4/HeroMeetingsCard.tsx
 * PURPOSE: Hero metric card showing meetings vs goal with gauge
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { MeetingsGoalData, MomentumData } from "./types";

interface HeroMeetingsCardProps {
  meetingsGoal: MeetingsGoalData;
  momentum: MomentumData;
}

function MeetingsGauge({ percent }: { percent: number }) {
  // Clamp percent between 0 and 100
  const clampedPercent = Math.min(100, Math.max(0, percent));
  // Calculate stroke dash offset (arc length is 251.2 for our path)
  const arcLength = 251.2;
  const strokeDashoffset = arcLength * (1 - clampedPercent / 100);
  
  const statusText = clampedPercent >= 100 
    ? "Target Hit" 
    : `${clampedPercent}% of goal`;

  const statusColor = clampedPercent >= 100 
    ? "text-emerald-500" 
    : clampedPercent >= 70 
      ? "text-blue-500" 
      : "text-amber-500";

  return (
    <div className="w-[200px]">
      <svg viewBox="0 0 200 120" width="200" height="120">
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#10B981" />
            <stop offset="100%" stopColor="#3B82F6" />
          </linearGradient>
        </defs>
        {/* Background arc */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="currentColor"
          strokeWidth="20"
          strokeLinecap="round"
          className="text-muted"
        />
        {/* Filled arc */}
        <path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="20"
          strokeLinecap="round"
          strokeDasharray={arcLength}
          strokeDashoffset={strokeDashoffset}
          style={{ transition: "stroke-dashoffset 0.5s ease-out" }}
        />
      </svg>
      <div className="text-center mt-3">
        <p className={`text-base font-bold ${statusColor}`}>
          {clampedPercent}% — {statusText}
        </p>
      </div>
    </div>
  );
}

export function HeroMeetingsCard({ meetingsGoal, momentum }: HeroMeetingsCardProps) {
  const MomentumIcon = momentum.direction === "up" 
    ? TrendingUp 
    : momentum.direction === "down" 
      ? TrendingDown 
      : Minus;

  const momentumColor = momentum.direction === "up" 
    ? "text-emerald-500" 
    : momentum.direction === "down" 
      ? "text-red-500" 
      : "text-muted-foreground";

  return (
    <Card className="p-8 shadow-sm">
      <div className="flex items-center gap-12">
        {/* Main metric */}
        <div className="flex-1">
          <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Meetings This Month
          </p>
          <p className="text-7xl font-extrabold text-foreground leading-none">
            {meetingsGoal.current}
          </p>
          <p className="text-lg text-muted-foreground mt-2">
            Goal: {meetingsGoal.target} •{" "}
            <span className={meetingsGoal.targetHit ? "text-emerald-500 font-semibold" : ""}>
              {meetingsGoal.targetHit 
                ? `Target hit${meetingsGoal.daysEarly ? ` ${meetingsGoal.daysEarly} days early` : ""} ✓` 
                : `${meetingsGoal.target - meetingsGoal.current} to go`}
            </span>
          </p>
          
          {/* Momentum indicator */}
          <div className="flex items-center gap-3 mt-5 pt-5 border-t">
            <MomentumIcon className={`h-6 w-6 ${momentumColor}`} />
            <p className="text-sm text-muted-foreground">
              <span className={`font-semibold ${momentumColor}`}>
                {momentum.direction === "up" ? "↑" : momentum.direction === "down" ? "↓" : "→"}{" "}
                {Math.abs(momentum.percentChange)}% vs last month
              </span>
              {" "}• {momentum.label}
            </p>
          </div>
        </div>

        {/* Gauge */}
        <MeetingsGauge percent={meetingsGoal.percentComplete} />
      </div>
    </Card>
  );
}
