/**
 * FILE: frontend/components/dashboard/TodoMockPanel.tsx
 * PURPOSE: Cream/amber placeholder panel that occupies the same slot as
 *          a not-yet-wired feature. Replaces the silent mock-data cards
 *          (Channel Orchestration / Smart Calling / What's Working)
 *          that previously rendered fabricated numbers without a TODO
 *          marker. PR4 dashboard rebuild.
 *
 * Each panel:
 *   - Shows a TODO · MOCK pill so demo viewers + CEO can tell at a
 *     glance that the surface is unwired (hidden when hideBadge=true)
 *   - Names the missing endpoint(s) so a future PR can grep for it
 *   - Carries an optional eyebrow + icon to keep the slot visually
 *     coherent with the rest of the dashboard chrome
 *
 * hideBadge: pass true when IS_DEMO_MODE is active so investor demos
 *   don't surface internal "TODO · MOCK" labels to external viewers.
 */

"use client";

import type { ReactNode } from "react";

interface Props {
  icon?: ReactNode;
  eyebrow: string;          // small mono uppercase eyebrow
  title: string;             // Playfair-style headline
  description: string;       // body copy
  endpointsNeeded: string[]; // bullet list of pending endpoints
  hideBadge?: boolean;       // when true, suppress the TODO · MOCK pill
}

export function TodoMockPanel({
  icon, eyebrow, title, description, endpointsNeeded, hideBadge = false,
}: Props) {
  return (
    <div className="rounded-[10px] border border-dashed border-amber/40 bg-amber-soft px-5 py-5">
      <div className="flex items-center gap-2.5 mb-2">
        {icon && (
          <span className="text-amber" aria-hidden>
            {icon}
          </span>
        )}
        <span className="font-mono text-[10px] tracking-[0.14em] uppercase font-semibold text-copper">
          {eyebrow}
        </span>
        {!hideBadge && (
          <span className="ml-auto font-mono text-[8px] tracking-[0.14em] uppercase text-amber bg-amber-soft border border-amber/40 rounded px-1.5 py-[1px]">
            TODO · MOCK
          </span>
        )}
      </div>

      <div className="font-display font-bold text-[18px] text-ink leading-snug">
        {title}
      </div>
      <p className="text-[13px] text-ink-2 mt-1.5 leading-relaxed">
        {description}
      </p>

      <ul className="mt-3 space-y-1">
        {endpointsNeeded.map(ep => (
          <li
            key={ep}
            className="font-mono text-[11px] text-ink-3 leading-tight"
          >
            <span className="text-copper">→</span> {ep}
          </li>
        ))}
      </ul>
    </div>
  );
}
