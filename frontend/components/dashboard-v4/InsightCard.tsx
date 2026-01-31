/**
 * FILE: frontend/components/dashboard-v4/InsightCard.tsx
 * PURPOSE: Single insight card showing what's working
 * PHASE: Dashboard V4 Implementation
 */

"use client";

import { Card } from "@/components/ui/card";
import type { InsightData } from "./types";

interface InsightCardProps {
  insight: InsightData;
}

export function InsightCard({ insight }: InsightCardProps) {
  // Parse the detail to highlight text if needed
  const renderDetail = () => {
    if (!insight.highlightText) {
      return <p className="text-sm text-muted-foreground leading-relaxed">{insight.detail}</p>;
    }

    const parts = insight.detail.split(insight.highlightText);
    return (
      <p className="text-sm text-muted-foreground leading-relaxed">
        {parts[0]}
        <strong className="text-foreground">{insight.highlightText}</strong>
        {parts[1]}
      </p>
    );
  };

  return (
    <Card className="p-6 bg-gradient-to-br from-blue-50 to-violet-50 dark:from-blue-950/30 dark:to-violet-950/30 border-blue-100 dark:border-blue-900">
      <div className="text-4xl mb-4">{insight.icon}</div>
      <h3 className="text-xl font-bold text-foreground mb-2">{insight.headline}</h3>
      {renderDetail()}
    </Card>
  );
}
