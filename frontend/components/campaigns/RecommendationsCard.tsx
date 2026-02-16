'use client';

import { Recommendation } from '@/data/mock-campaigns';

interface Props {
  recommendations: Recommendation[];
}

export function RecommendationsCard({ recommendations }: Props) {
  return (
    <div className="bg-bg-surface rounded-2xl p-6 border border-slate-200">
      <div className="text-[13px] text-text-muted uppercase tracking-wide font-semibold mb-4">
        AI Recommendations
      </div>
      <div className="space-y-2.5">
        {recommendations.map((rec) => (
          <div
            key={rec.id}
            className="flex gap-2.5 items-start px-4 py-3 bg-amber-50 rounded-lg text-sm text-amber-800"
          >
            <span className="text-base">💡</span>
            <span>{rec.text}</span>
          </div>
        ))}
      </div>
      <button className="mt-4 px-4 py-2 bg-amber text-text-primary rounded-md text-xs font-semibold hover:bg-violet-700 transition-colors">
        Apply Recommendations
      </button>
    </div>
  );
}
