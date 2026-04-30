/**
 * FILE: frontend/components/dashboard/TodoMockPanel.tsx
 * PURPOSE: Honest "Coming soon" empty state. Replaces the previous
 *          TODO · MOCK panel which surfaced fabricated numbers behind
 *          a dev-only badge. Per A3 dispatch (2026-04-30) the dashboard
 *          shows real data or honest empty states — never invented
 *          numbers, never internal TODO labels visible to investors.
 *
 * Component name kept for backwards-compat with existing import
 * statements; semantics are now an honest empty-state card.
 */

"use client";

import type { ReactNode } from "react";

interface Props {
  /** Optional eyebrow text — short label for the slot (e.g. "Voice"). */
  eyebrow?: string;
  /** Headline shown to the user. */
  title: string;
  /** Single-paragraph explanation of why no data is shown yet. */
  description?: string;
  /** Optional small icon — rendered before the eyebrow. */
  icon?: ReactNode;
}

export function TodoMockPanel({ icon, eyebrow, title, description }: Props) {
  return (
    <div className="rounded-[10px] border border-rule bg-panel px-5 py-5">
      {(icon || eyebrow) && (
        <div className="flex items-center gap-2.5 mb-2">
          {icon && (
            <span className="text-ink-3" aria-hidden>
              {icon}
            </span>
          )}
          {eyebrow && (
            <span className="font-mono text-[10px] tracking-[0.14em] uppercase font-semibold text-ink-3">
              {eyebrow}
            </span>
          )}
        </div>
      )}

      <div className="font-display font-bold text-[18px] text-ink leading-snug">
        {title}
      </div>

      {description && (
        <p className="text-[13px] text-ink-3 mt-1.5 leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
}
