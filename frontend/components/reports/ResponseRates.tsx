/**
 * ResponseRates.tsx - Response Rate Donut Gauges
 * Three circular progress indicators
 */

"use client";

import { Zap } from "lucide-react";
import { responseRates } from "@/lib/mock/reports-data";

const colorMap: Record<string, string> = {
  amber: "#D4956A",
  teal: "#14B8A6",
  green: "#22C55E",
};

export function ResponseRates() {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="bg-[#12121D] border border-[#1E1E2E] rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-[#1E1E2E] flex items-center gap-2">
        <Zap className="w-4 h-4 text-amber-500" />
        <h3 className="text-sm font-semibold text-[#F8F8FC]">Response Rates</h3>
      </div>
      <div className="p-5 flex justify-around">
        {responseRates.map((rate) => {
          const offset = circumference - (rate.value / 100) * circumference;
          const color = colorMap[rate.color];
          return (
            <div key={rate.label} className="text-center">
              <div className="w-20 h-20 relative">
                <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r={radius} fill="none" stroke="#0A0A12" strokeWidth="8" />
                  <circle
                    cx="50"
                    cy="50"
                    r={radius}
                    fill="none"
                    stroke={color}
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    className="transition-all duration-500"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-lg font-bold font-mono text-[#F8F8FC]">
                  {rate.value}%
                </span>
              </div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-[#6E6E82] mt-2">{rate.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
