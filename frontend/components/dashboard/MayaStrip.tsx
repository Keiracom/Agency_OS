/**
 * FILE: frontend/components/dashboard/MayaStrip.tsx
 * PURPOSE: Maya background-status collapsible strip
 * PHASE: B2.4 — port of /demo renderHome lines 1688-1701 (.maya-strip)
 *
 * One-row strip showing what Maya is doing in the background. Click to
 * expand to a 3-row breakdown of in-flight work. Reads counts from
 * useDashboardStats — placeholder zero until backend exposes Maya queue
 * telemetry.
 */

"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { useDashboardStats } from "@/lib/hooks/useDashboardStats";

interface MayaCounts {
  drafts: number;
  critic: number;
  enriching: number;
}

function readMayaCounts(): MayaCounts {
  return { drafts: 0, critic: 0, enriching: 0 };
}

export function MayaStrip({ personaName = "Maya" }: { personaName?: string }) {
  const [open, setOpen] = useState(false);
  const stats = useDashboardStats();
  const counts = readMayaCounts();
  const total = counts.drafts + counts.critic + counts.enriching;

  return (
    <section
      onClick={() => setOpen((v) => !v)}
      className="rounded-[12px] border border-rule bg-panel cursor-pointer transition-colors hover:border-amber/60"
      role="button"
      aria-expanded={open}
    >
      <div className="flex items-center justify-between px-5 py-4">
        <div className="text-[13px] text-ink leading-snug">
          <b className="font-semibold">{personaName} is working in the background</b>
          {total === 0 ? (
            <span className="text-ink-2">
              {" "}
              · awaiting first cycle of telemetry · cycle day {stats.cycleDay}/{stats.cycleLength}
            </span>
          ) : (
            <span className="text-ink-2">
              {" "}
              · generating drafts for {counts.drafts} prospects · critic loop
              on {counts.critic} · enriching {counts.enriching}
            </span>
          )}
        </div>
        <div className="font-mono text-[10px] tracking-[0.16em] text-ink-3 uppercase flex items-center gap-1 shrink-0">
          {open ? "Collapse" : "Expand"}
          <ChevronDown
            className={`w-3.5 h-3.5 transition-transform ${open ? "rotate-180" : ""}`}
            strokeWidth={2}
          />
        </div>
      </div>

      {open && (
        <div className="px-5 pb-5 border-t border-rule pt-4 space-y-3">
          <MayaActionRow
            count={counts.drafts}
            label="drafts in flight (Email · LinkedIn · SMS · Voice)"
          />
          <MayaActionRow
            count={counts.critic}
            label="drafts in critic loop (rewriting based on score)"
          />
          <MayaActionRow
            count={counts.enriching}
            label="prospects in Stage 9 enrichment (vulnerability scan)"
          />
          <div className="font-mono text-[11px] text-ink-3 pt-2">
            Recent today: telemetry feed pending — backend endpoint to come.
          </div>
        </div>
      )}
    </section>
  );
}

function MayaActionRow({ count, label }: { count: number; label: string }) {
  return (
    <div className="grid grid-cols-[44px_1fr] gap-3 items-center">
      <div className="font-display font-bold text-[22px] text-amber leading-none text-right tabular-nums">
        {count}
      </div>
      <div className="text-[12.5px] text-ink-2">{label}</div>
    </div>
  );
}

export default MayaStrip;
