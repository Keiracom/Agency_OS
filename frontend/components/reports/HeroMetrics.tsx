/**
 * HeroMetrics.tsx - Executive Summary Cards
 * 4-column hero metrics with accent borders
 */

"use client";

import { heroMetrics } from "@/lib/mock/reports-data";
import { TrendingUp } from "lucide-react";

const accentColors: Record<string, string> = {
  amber: "#D4956A",
  teal: "#14B8A6",
  blue: "#3B82F6",
  green: "#22C55E",
};

export function HeroMetrics() {
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {heroMetrics.map((metric) => (
        <div
          key={metric.id}
          className="bg-bg-surface border border-default rounded-xl p-5 relative overflow-hidden"
        >
          <div
            className="absolute top-0 left-0 right-0 h-0.5"
            style={{ backgroundColor: accentColors[metric.accentColor] }}
          />
          <p className="text-[11px] font-semibold uppercase tracking-wider text-ink-3 mb-2">
            {metric.label}
          </p>
          <p className="text-4xl font-extrabold font-mono text-ink leading-none">
            {metric.prefix}
            {metric.value}
            {metric.suffix && <span className="text-lg text-ink-3">{metric.suffix}</span>}
          </p>
          <div className="flex items-center gap-2 mt-3 text-xs">
            <span className="flex items-center gap-1 font-semibold text-[#22C55E]">
              <TrendingUp className="w-3 h-3" />↑ {metric.change}%
            </span>
            <span className="text-ink-3">{metric.changeLabel}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
