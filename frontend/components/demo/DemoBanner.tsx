/**
 * FILE: frontend/components/demo/DemoBanner.tsx
 * PURPOSE: Banner shown when in demo mode
 * CEO Directive #028 — Public Demo Dashboard
 */

'use client';

import { useDemo } from '@/lib/demo-context';
import { Sparkles, X } from 'lucide-react';
import { useState } from 'react';

export function DemoBanner() {
  const { isDemo, exitDemoMode } = useDemo();
  const [dismissed, setDismissed] = useState(false);

  if (!isDemo || dismissed) {
    return null;
  }

  // PR4 — palette aligned with the cream/amber theme. Uses the
  // brand-bar (deep ink) so the banner sits visually with the new
  // 232px sidebar instead of the old gradient orange.
  return (
    <div
      className="fixed top-0 left-0 right-0 z-[100] px-4 py-2"
      style={{
        backgroundColor: "var(--brand-bar)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        color: "white",
      }}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles
            className="w-4 h-4 animate-pulse"
            style={{ color: "var(--amber)" }}
          />
          <span className="text-sm font-medium">
            <strong className="font-mono uppercase tracking-[0.12em] text-[11px] mr-2" style={{ color: "var(--amber)" }}>
              Demo Mode
            </strong>
            <span className="text-white/80">
              You&apos;re exploring Agency<em className="not-italic" style={{ color: "var(--amber)", fontStyle: "italic" }}>OS</em> with sample data.
            </span>
          </span>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="https://agency-os.com/signup"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono font-semibold uppercase tracking-[0.08em] px-3 py-1.5 rounded-[4px] transition-colors"
            style={{
              backgroundColor: "var(--amber)",
              color: "var(--on-amber)",
            }}
          >
            Start Free Trial →
          </a>
          <button
            onClick={() => setDismissed(true)}
            className="p-1 rounded transition-colors text-white/60 hover:text-white hover:bg-white/10"
            aria-label="Dismiss banner"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook to get padding for main content when demo banner is visible
 */
export function useDemoBannerPadding() {
  const { isDemo } = useDemo();
  return isDemo ? 'pt-10' : '';
}
