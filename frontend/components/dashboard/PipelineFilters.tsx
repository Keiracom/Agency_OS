/**
 * FILE: frontend/components/dashboard/PipelineFilters.tsx
 * PURPOSE: Filter chip row — Top 10 / Top 50 / Struggling / Trying /
 *          Dabbling. PR3 dashboard rebuild.
 * REFERENCE: dashboard-master-agency-desk.html — `.chip` /
 *            `.chip.active` / `.chip-count` styling.
 */

"use client";

export type PipelineFilterKey =
  | "all"
  | "top10"
  | "top50"
  | "struggling"
  | "trying"
  | "dabbling";

export interface PipelineFilterOption {
  key: PipelineFilterKey;
  label: string;
  count: number;
}

interface Props {
  options: PipelineFilterOption[];
  active: PipelineFilterKey;
  onChange: (key: PipelineFilterKey) => void;
}

export function PipelineFilters({ options, active, onChange }: Props) {
  return (
    <div className="flex gap-2 flex-wrap">
      {options.map(opt => {
        const isActive = opt.key === active;
        return (
          <button
            key={opt.key}
            type="button"
            onClick={() => onChange(opt.key)}
            className={[
              "px-3.5 py-1.5 rounded-full font-mono text-[11px] tracking-[0.06em] border transition-colors",
              isActive
                ? "bg-amber border-amber font-semibold"
                : "bg-panel border-rule text-ink-3 hover:text-copper hover:border-amber",
            ].join(" ")}
            style={isActive ? { color: "var(--on-amber)" } : undefined}
          >
            {opt.label}
            <span
              className={[
                "ml-1.5 font-bold",
                isActive ? "" : "text-copper",
              ].join(" ")}
              style={isActive ? { color: "var(--on-amber)" } : undefined}
            >
              {opt.count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
