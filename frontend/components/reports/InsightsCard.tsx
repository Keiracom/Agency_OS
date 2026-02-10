/**
 * InsightsCard.tsx - "What's Working" Insights Card
 * Sprint 4 - Reports Page
 *
 * Displays insights grid with discovery banner.
 */

"use client";

import { Lightbulb, Flame } from "lucide-react";
import type { InsightBox } from "@/data/mock-reports";

// ============================================
// Types
// ============================================

interface InsightsCardProps {
  insights: InsightBox[];
  discovery: {
    label: string;
    text: string;
  };
}

// ============================================
// Component
// ============================================

export function InsightsCard({ insights, discovery }: InsightsCardProps) {
  return (
    <div className="bg-bg-surface border border-border-subtle rounded-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border-subtle">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Lightbulb className="w-4 h-4 text-accent-primary" />
          What&apos;s Working
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        {/* Insights Grid */}
        <div className="grid grid-cols-2 gap-3 mb-3">
          {insights.map((box) => (
            <div key={box.title} className="bg-bg-base rounded-lg p-3.5">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2.5">
                {box.title}
              </div>
              {box.items.map((item) => (
                <div
                  key={item.label}
                  className="flex justify-between items-center py-1.5"
                >
                  <span className="text-xs text-text-secondary">{item.label}</span>
                  <span className="text-xs font-semibold font-mono text-status-success">
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Discovery Banner */}
        <div
          className="p-3.5 rounded-lg border
            bg-gradient-to-br from-accent-primary/10 to-accent-blue/10
            border-accent-primary/30"
        >
          <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-accent-primary mb-1.5">
            <Flame className="w-3.5 h-3.5" />
            {discovery.label}
          </div>
          <div className="text-sm text-text-primary leading-relaxed">
            {discovery.text}
          </div>
        </div>
      </div>
    </div>
  );
}

export default InsightsCard;
