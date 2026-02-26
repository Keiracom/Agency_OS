/**
 * MeetingsChart.tsx - Meetings Over Time Bar Chart
 * CSS-only bar chart with amber accent
 * Uses real data from meetings API
 */

"use client";

import { TrendingUp, AlertCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface WeeklyMeetingData {
  week: string;
  weekStart: string;
  value: number;
}

interface MeetingsReportResponse {
  success: boolean;
  data: WeeklyMeetingData[];
}

async function fetchMeetingsReport(): Promise<WeeklyMeetingData[]> {
  const res = await fetch("/api/reports/meetings");
  if (!res.ok) {
    throw new Error("Failed to fetch meetings report");
  }
  const json: MeetingsReportResponse = await res.json();
  if (!json.success) {
    throw new Error("Failed to fetch meetings report");
  }
  return json.data;
}

function ChartSkeleton() {
  return (
    <div className="h-48 flex items-end gap-2 animate-pulse">
      {Array.from({ length: 12 }).map((_, i) => (
        <div key={i} className="flex-1 flex flex-col items-center h-full">
          <div className="flex-1 w-full flex items-end justify-center">
            <div
              className="w-[70%] rounded-t bg-muted"
              style={{ height: `${20 + Math.random() * 60}%` }}
            />
          </div>
          <div className="w-8 h-3 bg-muted rounded mt-2" />
          <div className="w-4 h-3 bg-muted rounded mt-1" />
        </div>
      ))}
    </div>
  );
}

export function MeetingsChart() {
  const { data: meetingsData, isLoading, error } = useQuery({
    queryKey: ["reports", "meetings"],
    queryFn: fetchMeetingsReport,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // 10 minutes
  });

  const maxVal = meetingsData ? Math.max(...meetingsData.map((d) => d.value), 1) : 1;

  return (
    <div className="bg-bg-base border border-default rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-default flex items-center gap-2">
        <TrendingUp className="w-4 h-4 text-[#D4956A]" />
        <h3 className="text-sm font-semibold text-text-primary">Meetings Over Time</h3>
        <span className="text-xs text-text-muted ml-auto">Last 12 weeks</span>
      </div>
      <div className="p-5">
        {isLoading ? (
          <ChartSkeleton />
        ) : error ? (
          <div className="h-48 flex flex-col items-center justify-center text-text-muted">
            <AlertCircle className="w-8 h-8 mb-2" />
            <p className="text-sm">Unable to load meetings data</p>
          </div>
        ) : !meetingsData || meetingsData.length === 0 ? (
          <div className="h-48 flex flex-col items-center justify-center text-text-muted">
            <TrendingUp className="w-8 h-8 mb-2 opacity-50" />
            <p className="text-sm">No meetings data yet</p>
            <p className="text-xs mt-1">Meetings will appear here once booked</p>
          </div>
        ) : (
          <div className="h-48 flex items-end gap-2">
            {meetingsData.map((d) => {
              const height = maxVal > 0 ? (d.value / maxVal) * 100 : 0;
              return (
                <div key={d.weekStart} className="flex-1 flex flex-col items-center h-full">
                  <div className="flex-1 w-full flex items-end justify-center">
                    <div
                      className="w-[70%] rounded-t bg-gradient-to-t from-[#D4956A]/50 to-[#D4956A] hover:brightness-110 transition-all relative group"
                      style={{ height: `${Math.max(height, 2)}%` }}
                    >
                      <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-xs font-mono font-semibold text-text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                        {d.value}
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-text-muted mt-2 font-medium truncate max-w-full">{d.week}</p>
                  <p className="text-xs font-mono font-semibold text-text-secondary">{d.value}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
