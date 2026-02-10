/**
 * ExecSummaryCard.tsx - Executive Summary Metric Card
 * Sprint 4 - Reports Page
 *
 * Single metric card with colored top border, value, label, and change indicator.
 */

"use client";

import { ArrowUp, ArrowDown } from "lucide-react";
import type { ExecMetric } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface ExecSummaryCardProps {
  metric: ExecMetric;
}

// ============================================
// Color Configuration
// ============================================

const colorBorder: Record<ExecMetric["color"], string> = {
  purple: "before:bg-accent-primary",
  teal: "before:bg-accent-teal",
  blue: "before:bg-accent-blue",
  success: "before:bg-status-success",
};

// ============================================
// Component
// ============================================

export function ExecSummaryCard({ metric }: ExecSummaryCardProps) {
  const isPositive = metric.change >= 0;

  // Format value with prefix/suffix
  const formattedValue = () => {
    const val = metric.value;
    return (
      <>
        {metric.prefix && (
          <span className="text-lg text-text-muted">{metric.prefix}</span>
        )}
        {val}
        {metric.suffix && (
          <span className="text-lg text-text-muted">{metric.suffix}</span>
        )}
      </>
    );
  };

  return (
    <div
      className={`
        relative bg-bg-surface border border-border-subtle rounded-xl p-5 overflow-hidden
        before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:h-0.5
        ${colorBorder[metric.color]}
      `}
    >
      {/* Label */}
      <div className="text-[11px] font-semibold uppercase tracking-wider text-text-muted mb-2">
        {metric.label}
      </div>

      {/* Value */}
      <div className="text-4xl font-extrabold font-mono text-text-primary leading-none">
        {formattedValue()}
      </div>

      {/* Change Indicator */}
      <div className="flex items-center gap-2 mt-3 text-xs">
        <span
          className={`flex items-center gap-1 font-semibold ${
            isPositive ? "text-status-success" : "text-status-error"
          }`}
        >
          {isPositive ? (
            <ArrowUp className="w-3 h-3" />
          ) : (
            <ArrowDown className="w-3 h-3" />
          )}
          {Math.abs(metric.change)}
          {metric.id === "roi" ? "x" : "%"}
        </span>
        <span className="text-text-muted">{metric.changeLabel}</span>
      </div>
    </div>
  );
}

export default ExecSummaryCard;
