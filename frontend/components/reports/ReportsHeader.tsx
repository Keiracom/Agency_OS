/**
 * ReportsHeader.tsx - Analytics Terminal Header
 * Date tabs + Export buttons (amber theme)
 */

"use client";

import { Download, FileText } from "lucide-react";
import { dateRangeOptions, type DateRange } from "@/lib/mock/reports-data";

interface ReportsHeaderProps {
  selectedRange: DateRange;
  onRangeChange: (range: DateRange) => void;
}

export function ReportsHeader({ selectedRange, onRangeChange }: ReportsHeaderProps) {
  return (
    <header className="bg-bg-base border-b border-default px-8 py-4 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <div>
          <h1 className="text-sm font-semibold text-text-primary">Analytics Terminal</h1>
          <p className="text-xs text-text-muted">Multi-Channel Performance Intelligence</p>
        </div>
        <div className="flex gap-1 bg-bg-void p-1 rounded-lg border border-default">
          {dateRangeOptions.map((opt) => (
            <button
              key={opt.value}
              onClick={() => onRangeChange(opt.value as DateRange)}
              className={`px-4 py-2 text-[13px] font-medium rounded-md transition-all ${
                selectedRange === opt.value
                  ? "bg-[#D4956A] text-text-primary"
                  : "text-text-muted hover:text-text-secondary hover:bg-bg-elevated"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="flex gap-3">
        <button className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-text-secondary bg-transparent border border-default rounded-lg hover:bg-bg-elevated hover:border-[#3A3A50] transition-all">
          <Download className="w-4 h-4" />
          CSV
        </button>
        <button className="flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium text-text-primary bg-[#D4956A] rounded-lg hover:bg-[#E5A67B] transition-all">
          <FileText className="w-4 h-4" />
          Export PDF
        </button>
      </div>
    </header>
  );
}
