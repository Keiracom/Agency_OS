/**
 * FILE: frontend/components/dashboard/PipelineStateTabs.tsx
 * PURPOSE: Pipeline state-machine tab row — Review / Outreach /
 *          Complete modes with mode-specific summaries (review counter,
 *          outreach breakdown, completion countdown). PR3 dashboard rebuild.
 *
 * The three modes mirror the prototype's three pipeline phases:
 *   Review  — operator gates which prospects to release
 *   Outreach — Maya is actively running sequences
 *   Complete — cycle finished, results posted, next cycle countdown
 */

"use client";

import { useMemo } from "react";

export type PipelineMode = "review" | "outreach" | "complete";

interface ReviewProps {
  mode: "review";
  total: number;
  reviewed: number;
  onReleaseAll?: () => void;
  releasing?: boolean;
}

interface OutreachProps {
  mode: "outreach";
  contacted: number;
  replied: number;
  meetingsBooked: number;
}

interface CompleteProps {
  mode: "complete";
  cycleNumber: number;
  contacted: number;
  replied: number;
  meetingsBooked: number;
  /** ISO timestamp at which the next cycle begins. */
  nextCycleAt?: string | null;
}

type Props = ReviewProps | OutreachProps | CompleteProps;

interface TabsProps {
  mode: PipelineMode;
  onChange: (mode: PipelineMode) => void;
}

/** Tab-row + content. Caller picks the visible mode and supplies data. */
export function PipelineStateTabs(props: Props & TabsProps) {
  return (
    <section>
      <TabRow active={props.mode} onChange={props.onChange} />

      <div className="mt-4 rounded-[10px] border border-rule bg-panel p-5">
        {props.mode === "review" && <ReviewBody {...props} />}
        {props.mode === "outreach" && <OutreachBody {...props} />}
        {props.mode === "complete" && <CompleteBody {...props} />}
      </div>
    </section>
  );
}

function TabRow({
  active, onChange,
}: { active: PipelineMode; onChange: (m: PipelineMode) => void }) {
  const tabs: Array<{ key: PipelineMode; label: string }> = [
    { key: "review",   label: "Review" },
    { key: "outreach", label: "Outreach" },
    { key: "complete", label: "Complete" },
  ];
  return (
    <div className="inline-flex p-[2px] rounded-md bg-surface">
      {tabs.map(t => {
        const isActive = t.key === active;
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => onChange(t.key)}
            className={[
              "px-3.5 py-1.5 font-mono text-[11px] tracking-[0.06em] rounded-[4px] uppercase transition-colors",
              isActive
                ? "bg-ink text-white font-semibold"
                : "text-ink-3 hover:text-ink",
            ].join(" ")}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

// ─── Review mode ──────────────────────────────────────────────────────────

function ReviewBody({ total, reviewed, onReleaseAll, releasing }: ReviewProps) {
  const pct = total > 0 ? Math.round((reviewed / total) * 100) : 0;
  const remaining = Math.max(0, total - reviewed);

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-display font-bold text-[22px] text-ink leading-tight">
          You have reviewed{" "}
          <em className="text-amber" style={{ fontStyle: "italic" }}>
            {reviewed}
          </em>{" "}
          <span className="text-ink-3">of {total}</span>
        </h3>
        <button
          type="button"
          onClick={onReleaseAll}
          disabled={releasing || remaining === 0}
          className="px-4 py-2 rounded-[6px] font-mono text-[11px] tracking-[0.08em] uppercase font-semibold transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ backgroundColor: "var(--ink)", color: "white" }}
        >
          {releasing ? "Releasing…" : `Release All (${remaining})`}
        </button>
      </div>

      <div
        className="mt-3 h-1.5 w-full rounded-full overflow-hidden"
        style={{ backgroundColor: "rgba(12,10,8,0.06)" }}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={reviewed}
      >
        <div
          className="h-full transition-[width] duration-300"
          style={{
            width: `${pct}%`,
            backgroundColor: "var(--amber)",
          }}
        />
      </div>

      <p className="mt-3 text-[13px] text-ink-2 leading-relaxed">
        Each prospect waits in review until you release it — then Maya begins
        outreach. No content sent yet.
      </p>
    </div>
  );
}

// ─── Outreach mode ────────────────────────────────────────────────────────

function OutreachBody({ contacted, replied, meetingsBooked }: OutreachProps) {
  return (
    <div>
      <h3 className="font-display font-bold text-[22px] text-ink leading-tight">
        Maya is <em className="text-amber" style={{ fontStyle: "italic" }}>working</em>
      </h3>
      <p className="text-[13px] text-ink-3 mt-1">
        Sequences in flight. Numbers refresh every 5 minutes.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mt-4 pt-4 border-t border-rule">
        <Metric label="Contacted" value={contacted} />
        <Metric label="Replied" value={replied} />
        <Metric label="Booked" value={meetingsBooked} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="font-display font-bold text-[24px] text-ink leading-none">
        {value.toLocaleString()}
      </div>
      <div className="font-mono text-[10px] tracking-[0.12em] uppercase text-ink-3 mt-1.5">
        {label}
      </div>
    </div>
  );
}

// ─── Complete mode ────────────────────────────────────────────────────────

function CompleteBody({
  cycleNumber, contacted, replied, meetingsBooked, nextCycleAt,
}: CompleteProps) {
  const countdown = useNextCycleCountdown(nextCycleAt);

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <h3 className="font-display font-bold text-[22px] text-ink leading-tight">
          Cycle <em className="text-amber" style={{ fontStyle: "italic" }}>{cycleNumber}</em>{" "}
          <span className="text-ink-3">complete</span>
        </h3>

        {countdown && (
          <div className="font-mono text-[11px] text-ink-3 tracking-[0.06em]">
            Next cycle in <span className="text-copper font-semibold">{countdown}</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mt-4 pt-4 border-t border-rule">
        <Metric label="Contacted" value={contacted} />
        <Metric label="Replied" value={replied} />
        <Metric label="Booked" value={meetingsBooked} />
      </div>
    </div>
  );
}

function useNextCycleCountdown(nextCycleAt: string | null | undefined): string | null {
  return useMemo(() => {
    if (!nextCycleAt) return null;
    const ts = Date.parse(nextCycleAt);
    if (Number.isNaN(ts)) return null;
    const diffMs = ts - Date.now();
    if (diffMs <= 0) return "now";
    const days = Math.floor(diffMs / (24 * 3600 * 1000));
    const hours = Math.floor((diffMs % (24 * 3600 * 1000)) / (3600 * 1000));
    if (days > 0) return `${days}d ${hours}h`;
    const mins = Math.floor((diffMs % (3600 * 1000)) / 60000);
    return `${hours}h ${mins}m`;
  }, [nextCycleAt]);
}
