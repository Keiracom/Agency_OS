/**
 * FILE: frontend/components/BUReadinessWidget.tsx
 * PURPOSE: M10 — surface BU sellable thresholds (Coverage / Verified /
 *          Outcomes / Trajectory) on the dashboard.
 * PHASE:   M10 — BU readiness threshold instrumentation
 *
 * Polls /api/v1/bu/readiness on mount + every 60s. Each metric is shown
 * with a progress bar against its threshold and a pass/fail badge:
 *   - emerald: threshold met
 *   - amber:   between 50% and 100% of threshold
 *   - red:     below 50% of threshold
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import api from "@/lib/api";

interface ReadinessMetric {
  name: string;
  value: number;
  unit: "pct" | "count";
  threshold: number;
  pass: boolean;
  detail: string;
}

interface ReadinessResponse {
  metrics: ReadinessMetric[];
  overall_pass: boolean;
}

const LABELS: Record<string, string> = {
  coverage:   "Coverage",
  verified:   "Verified contacts",
  outcomes:   "Outcomes",
  trajectory: "Trajectory",
};

function fmt(metric: ReadinessMetric): string {
  if (metric.unit === "pct") return `${metric.value.toFixed(1)}%`;
  return metric.value.toLocaleString();
}

function fmtThreshold(metric: ReadinessMetric): string {
  if (metric.unit === "pct") return `≥ ${metric.threshold.toFixed(0)}%`;
  return `≥ ${metric.threshold.toLocaleString()}`;
}

function ratio(metric: ReadinessMetric): number {
  if (metric.threshold <= 0) return 0;
  return Math.min(1, metric.value / metric.threshold);
}

function colorBand(metric: ReadinessMetric): {
  bar: string; badge: string; text: string; icon: JSX.Element;
} {
  const r = ratio(metric);
  if (metric.pass) {
    return {
      bar:   "bg-emerald-500",
      badge: "bg-emerald-500/15 border-emerald-500/40 text-emerald-300",
      text:  "text-emerald-300",
      icon:  <CheckCircle2 className="w-3.5 h-3.5" />,
    };
  }
  if (r >= 0.5) {
    return {
      bar:   "bg-amber-500",
      badge: "bg-amber-500/15 border-amber-500/40 text-amber-300",
      text:  "text-amber-300",
      icon:  <AlertTriangle className="w-3.5 h-3.5" />,
    };
  }
  return {
    bar:   "bg-red-500",
    badge: "bg-red-500/15 border-red-500/40 text-red-300",
    text:  "text-red-300",
    icon:  <XCircle className="w-3.5 h-3.5" />,
  };
}

async function fetchReadiness(): Promise<ReadinessResponse | null> {
  try {
    return await api.get<ReadinessResponse>("/api/v1/bu/readiness");
  } catch {
    return null;
  }
}

export function BUReadinessWidget() {
  const { data, isLoading } = useQuery({
    queryKey: ["bu-readiness"],
    queryFn: fetchReadiness,
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
  });

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
      <header className="flex items-center justify-between mb-3">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-gray-400">
          BU readiness
        </h3>
        {data && (
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-mono uppercase tracking-widest rounded border ${
              data.overall_pass
                ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-300"
                : "bg-red-500/15 border-red-500/40 text-red-300"
            }`}
          >
            {data.overall_pass ? (
              <CheckCircle2 className="w-3 h-3" />
            ) : (
              <XCircle className="w-3 h-3" />
            )}
            {data.overall_pass ? "Sellable" : "Not yet"}
          </span>
        )}
      </header>

      {isLoading ? (
        <div className="text-xs text-gray-500 italic py-3">Loading…</div>
      ) : !data ? (
        <div className="text-xs text-gray-500 italic py-3">
          BU readiness endpoint unavailable.
        </div>
      ) : (
        <ul className="space-y-3">
          {data.metrics.map((m) => {
            const { bar, badge, text, icon } = colorBand(m);
            const pct = ratio(m) * 100;
            return (
              <li key={m.name}>
                <div className="flex items-baseline justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-widest text-gray-400">
                      {LABELS[m.name] ?? m.name}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-widest rounded border ${badge}`}
                    >
                      {icon}
                      {m.pass ? "PASS" : "FAIL"}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono">
                    <span className={text}>{fmt(m)}</span>
                    <span className="text-gray-500 ml-1.5">
                      {fmtThreshold(m)}
                    </span>
                  </div>
                </div>
                <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${bar} transition-all`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">{m.detail}</div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
