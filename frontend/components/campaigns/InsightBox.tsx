'use client';

import { Brain } from 'lucide-react';

interface Props {
  insight: string;
}

export function InsightBox({ insight }: Props) {
  return (
    <div className="bg-gradient-to-r from-violet-100 to-sky-100 rounded-lg px-4 py-3 flex items-center gap-3">
      <Brain className="w-5 h-5 text-violet-600" />
      <p className="text-sm text-ink-3">
        <strong>AI Insight:</strong> {insight}
      </p>
    </div>
  );
}
