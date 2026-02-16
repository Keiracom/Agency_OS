'use client';

interface Props {
  insight: string;
}

export function InsightBox({ insight }: Props) {
  return (
    <div className="bg-gradient-to-r from-violet-100 to-sky-100 rounded-lg px-4 py-3 flex items-center gap-3">
      <span className="text-lg">🧠</span>
      <p className="text-sm text-text-muted">
        <strong>AI Insight:</strong> {insight}
      </p>
    </div>
  );
}
