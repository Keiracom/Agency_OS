/**
 * FILE: frontend/components/dashboard/HotReplies.tsx
 * PURPOSE: Recent prospect responses with amber heat dots — PR2 rebuild.
 * REFERENCE: dashboard-master-agency-desk.html — `.attention-card.reply`
 *            + warm-reply preview list patterns.
 */

"use client";

import { useDashboardV4, type WarmReply } from "@/hooks/use-dashboard-v4";
import Link from "next/link";

/**
 * Heat tier — drives how many amber dots render on the card. Until the
 * backend exposes a per-reply heat score we infer it from preview length
 * + name presence (longer, more personal previews → hotter).
 *
 * TODO(api): replace `inferHeat` with a real heat score from the warm
 * replies endpoint once `lead_heat_score` is added to the response.
 */
function inferHeat(reply: WarmReply): 1 | 2 | 3 {
  const len = (reply.preview || "").length;
  if (len >= 140) return 3;
  if (len >= 70)  return 2;
  return 1;
}

export function HotReplies() {
  const { data, isLoading } = useDashboardV4();
  const replies = data?.warmReplies ?? [];

  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-ink-3 font-semibold">
          Hot Replies
        </div>
        <Link
          href="/dashboard/replies"
          className="font-mono text-[10px] tracking-[0.08em] uppercase text-copper hover:text-amber transition-colors"
        >
          View all →
        </Link>
      </div>

      {isLoading ? (
        <div className="rounded-[10px] border border-dashed border-rule bg-panel/50 px-5 py-4 text-[13px] text-ink-3">
          Loading replies…
        </div>
      ) : replies.length === 0 ? (
        <div className="rounded-[10px] border border-dashed border-rule bg-panel/50 px-5 py-4 text-[13px] text-ink-3">
          <b className="text-ink">No hot replies yet</b> — new responses will surface here.
        </div>
      ) : (
        <div className="grid gap-2.5">
          {replies.slice(0, 5).map(reply => (
            <HotReplyCard key={reply.id} reply={reply} heat={inferHeat(reply)} />
          ))}
        </div>
      )}
    </section>
  );
}

function HotReplyCard({ reply, heat }: { reply: WarmReply; heat: 1 | 2 | 3 }) {
  return (
    <Link
      href={`/dashboard/leads/${reply.leadId}`}
      className="block rounded-[10px] border border-rule bg-panel hover:border-amber hover:shadow-[0_2px_10px_rgba(212,149,106,0.10)] transition-all px-4 py-3.5"
    >
      <div className="flex items-start gap-3">
        {/* Avatar */}
        <div
          className="w-9 h-9 rounded-full grid place-items-center text-[12px] font-display font-bold shrink-0"
          style={{ backgroundColor: "var(--amber)", color: "var(--on-amber)" }}
        >
          {reply.initials}
        </div>

        {/* Body */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="text-[13px] text-ink font-medium truncate">
              {reply.name}
              {reply.company && (
                <span className="text-ink-3 font-normal"> · {reply.company}</span>
              )}
            </div>

            {/* Heat dots */}
            <HeatDots heat={heat} />
          </div>

          <div className="text-[12.5px] text-ink-2 mt-1 line-clamp-2 leading-snug">
            {reply.preview}
          </div>
        </div>
      </div>
    </Link>
  );
}

function HeatDots({ heat }: { heat: 1 | 2 | 3 }) {
  return (
    <div
      className="flex items-center gap-[3px] shrink-0"
      title={`${heat === 3 ? "Very hot" : heat === 2 ? "Hot" : "Warm"} reply`}
      aria-label={`${heat} of 3 heat dots`}
    >
      {[1, 2, 3].map(i => (
        <span
          key={i}
          className="block w-[7px] h-[7px] rounded-full"
          style={{
            backgroundColor:
              i <= heat ? "var(--amber)" : "rgba(12,10,8,0.10)",
          }}
        />
      ))}
    </div>
  );
}
