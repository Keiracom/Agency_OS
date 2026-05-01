/**
 * FILE: frontend/components/dashboard/AttentionCards.tsx
 * PURPOSE: "Needs your attention" card list — /demo renderHome lines 1714-1720
 * PHASE: B2.4 — cream/amber rebrand
 *
 * 4 types (meeting-today, positive-reply, overdue-followup, hot-prospect)
 * with per-type colour variants on the cream surface. Real data via
 * useAttentionItems.
 */

"use client";

import Link from "next/link";
import {
  useAttentionItems,
  type AttentionItem,
  type AttentionType,
} from "@/lib/hooks/useAttentionItems";

const TYPE_STYLES: Record<AttentionType, { card: string; icon: string }> = {
  "meeting-today": {
    card: "bg-emerald-50 border-emerald-200 border-l-emerald-500",
    icon: "bg-emerald-600 text-white",
  },
  "positive-reply": {
    card: "bg-emerald-50/60 border-emerald-200 border-l-emerald-400",
    icon: "bg-emerald-600 text-white",
  },
  "overdue-followup": {
    card: "bg-red-50 border-red-200 border-l-red-500",
    icon: "bg-red-600 text-white",
  },
  "hot-prospect": {
    card: "bg-amber-soft border-rule border-l-amber",
    icon: "bg-amber text-white",
  },
};

export interface AttentionCardsProps {
  /** Optional — intercept leads-detail clicks and open a drawer instead. */
  onLeadClick?: (leadId: string) => void;
}

export function AttentionCards({ onLeadClick }: AttentionCardsProps = {}) {
  const { items, isLoading, error } = useAttentionItems();

  if (isLoading) {
    return (
      <div className="space-y-2.5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 rounded-[10px] bg-panel animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || items.length === 0) {
    return (
      <div className="rounded-[10px] border border-rule bg-panel px-4 py-6 text-center text-sm text-ink-2">
        All clear — no items need your attention right now.
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      {items.map((item) => (
        <AttentionRow key={item.id} item={item} onLeadClick={onLeadClick} />
      ))}
    </div>
  );
}

function leadIdFromHref(href: string): string | null {
  const m = /^\/dashboard\/leads\/([^/?#]+)/.exec(href);
  return m ? m[1] : null;
}

function AttentionRow({
  item, onLeadClick,
}: { item: AttentionItem; onLeadClick?: (leadId: string) => void }) {
  const style = TYPE_STYLES[item.type];
  const leadId = leadIdFromHref(item.href);
  const interceptable = !!(onLeadClick && leadId);

  const handleClick: React.MouseEventHandler<HTMLAnchorElement> = (e) => {
    if (interceptable) {
      e.preventDefault();
      onLeadClick!(leadId!);
    }
  };

  return (
    <Link
      href={item.href}
      onClick={handleClick}
      className={`grid grid-cols-[28px_1fr_auto] gap-3 items-center rounded-[10px] border border-l-4 px-4 py-3.5 transition-colors hover:brightness-[1.02] ${style.card}`}
    >
      <div
        className={`w-7 h-7 rounded-md flex items-center justify-center text-base ${style.icon}`}
        aria-hidden
      >
        {item.icon}
      </div>
      <div className="min-w-0 text-sm text-ink truncate">{item.text}</div>
      <span className="text-xs font-mono text-copper tracking-wider whitespace-nowrap uppercase">
        {item.cta}
      </span>
    </Link>
  );
}

export default AttentionCards;
