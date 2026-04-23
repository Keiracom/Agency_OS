/**
 * AttentionCards — items needing operator attention.
 *
 * Port of Master v10 .attention-card (dashboard-master-agency-desk.html:221-231, 1714-1720).
 * 4 types (meeting-today, positive-reply, overdue-followup, hot-prospect) with
 * per-type colour variants. Real data from useAttentionItems hook.
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
    card: "bg-emerald-900/20 border-emerald-600 border-l-emerald-500",
    icon: "bg-emerald-600 text-white",
  },
  "positive-reply": {
    card: "bg-emerald-900/10 border-emerald-700 border-l-emerald-600",
    icon: "bg-emerald-600 text-white",
  },
  "overdue-followup": {
    card: "bg-red-900/15 border-red-700 border-l-red-500",
    icon: "bg-red-600 text-white",
  },
  "hot-prospect": {
    card: "bg-amber-900/20 border-amber-700 border-l-amber-500",
    icon: "bg-amber-600 text-white",
  },
};

export interface AttentionCardsProps {
  /** Optional — intercept leads-detail clicks and open a drawer instead of navigating. */
  onLeadClick?: (leadId: string) => void;
}

export function AttentionCards({ onLeadClick }: AttentionCardsProps = {}) {
  const { items, isLoading, error } = useAttentionItems();

  if (isLoading) {
    return (
      <div className="space-y-2.5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-14 rounded-lg bg-gray-800 animate-pulse" />
        ))}
      </div>
    );
  }

  if (error || items.length === 0) {
    return (
      <div className="rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-6 text-center text-sm text-gray-400">
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
      className={`grid grid-cols-[28px_1fr_auto] gap-3 items-center rounded-lg border border-l-4 px-4 py-3.5 transition-colors hover:brightness-110 ${style.card}`}
    >
      <div
        className={`w-7 h-7 rounded-md flex items-center justify-center text-base ${style.icon}`}
        aria-hidden
      >
        {item.icon}
      </div>
      <div className="min-w-0 text-sm text-gray-100 truncate">{item.text}</div>
      <span className="text-xs font-mono text-amber-400 tracking-wider whitespace-nowrap">
        {item.cta}
      </span>
    </Link>
  );
}

export default AttentionCards;
