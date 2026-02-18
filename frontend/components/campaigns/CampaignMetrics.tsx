'use client';

import { MetricData } from '@/data/mock-campaigns';

interface Props {
  metrics: MetricData[];
}

export function CampaignMetrics({ metrics }: Props) {
  return (
    <div className="grid grid-cols-5 gap-4 p-4 bg-slate-50 rounded-lg mb-5">
      {metrics.map((metric, idx) => (
        <div key={idx} className="text-center">
          <div className="text-2xl font-bold text-slate-800">{metric.value}</div>
          <div className="text-[11px] text-text-muted uppercase tracking-wide">{metric.label}</div>
          <div className={`text-[11px] ${metric.change >= 0 ? 'text-amber' : 'text-amber'}`}>
            {metric.change >= 0 ? '+' : ''}{metric.change}{metric.isPercentage ? '%' : ''} {metric.change >= 0 ? '↑' : '↓'}
          </div>
        </div>
      ))}
    </div>
  );
}
