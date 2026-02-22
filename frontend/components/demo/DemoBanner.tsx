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

  return (
    <div 
      className="fixed top-0 left-0 right-0 z-[100] bg-gradient-to-r from-amber-600 to-orange-500 text-white px-4 py-2"
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Sparkles className="w-4 h-4 animate-pulse" />
          <span className="text-sm font-medium">
            <strong>Demo Mode</strong> — You&apos;re exploring Horizon Digital&apos;s Agency OS dashboard with sample data.
          </span>
        </div>
        <div className="flex items-center gap-3">
          <a 
            href="https://agency-os.com/signup" 
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-semibold bg-white/20 hover:bg-white/30 px-3 py-1.5 rounded-full transition-colors"
          >
            Start Free Trial →
          </a>
          <button 
            onClick={() => setDismissed(true)}
            className="p-1 hover:bg-white/20 rounded transition-colors"
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
