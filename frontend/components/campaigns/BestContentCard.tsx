'use client';

import { BestContent, channelEmoji } from '@/data/mock-campaigns';

interface Props {
  content: BestContent[];
}

export function BestContentCard({ content }: Props) {
  return (
    <div className="bg-bg-surface rounded-2xl p-6 border border-slate-200 mb-5">
      <div className="text-[13px] text-text-muted uppercase tracking-wide font-semibold mb-4">
        Best Performing Content
      </div>
      <div className="space-y-2">
        {content.map((item, idx) => (
          <div
            key={idx}
            className="flex justify-between items-center px-4 py-3 bg-slate-50 rounded-lg"
          >
            <span className="text-sm text-text-muted">
              {channelEmoji[item.channel]} {item.text}
            </span>
            <span className="text-xs text-amber font-semibold">
              {item.result}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
