/**
 * ResponseRates.tsx - Progress Ring/Donut Charts
 * Sprint 4 - Reports Page
 *
 * CSS-based circular progress indicators for response rates.
 */

"use client";

import { Zap } from "lucide-react";
import type { ResponseRate } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface ResponseRatesProps {
  rates: ResponseRate[];
}

// ============================================
// Color Configuration
// ============================================

const strokeColors: Record<ResponseRate["color"], string> = {
  purple: "stroke-accent-primary",
  teal: "stroke-accent-teal",
  success: "stroke-status-success",
};

// ============================================
// Progress Ring Component
// ============================================

interface ProgressRingProps {
  rate: ResponseRate;
}

function ProgressRing({ rate }: ProgressRingProps) {
  // SVG circle calculations
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (rate.value / 100) * circumference;

  return (
    <div className="text-center">
      {/* Ring */}
      <div className="relative w-20 h-20 mx-auto">
        <svg
          className="w-full h-full -rotate-90"
          viewBox="0 0 100 100"
        >
          {/* Background circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            strokeWidth="8"
            className="stroke-bg-base"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r={radius}
            fill="none"
            strokeWidth="8"
            strokeLinecap="round"
            className={`transition-all duration-500 ${strokeColors[rate.color]}`}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        {/* Value */}
        <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-lg font-bold font-mono text-text-primary">
          {rate.value}%
        </span>
      </div>

      {/* Label */}
      <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted mt-2">
        {rate.label}
      </div>
    </div>
  );
}

// ============================================
// Main Component
// ============================================

export function ResponseRates({ rates }: ResponseRatesProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Zap className="w-4 h-4 text-status-warning" />
          Response Rates
        </div>
      </div>

      {/* Progress Rings */}
      <div className="p-5">
        <div className="flex justify-around py-4">
          {rates.map((rate) => (
            <ProgressRing key={rate.label} rate={rate} />
          ))}
        </div>
      </div>
    </div>
  );
}

export default ResponseRates;
