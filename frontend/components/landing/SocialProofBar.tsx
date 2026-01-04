/**
 * FILE: frontend/components/landing/SocialProofBar.tsx
 * PURPOSE: Stats bar showing key metrics with animated counters
 * PHASE: 21
 */

"use client";

interface StatItem {
  value: string;
  label: string;
  sublabel?: string;
}

interface SocialProofBarProps {
  stats?: StatItem[];
  className?: string;
}

const defaultStats: StatItem[] = [
  { value: "55%+", label: "Open rate", sublabel: "Industry avg: 15-20%" },
  { value: "12%+", label: "Reply rate", sublabel: "3x typical cold email" },
  { value: "<14 days", label: "To first meeting", sublabel: "From campaign launch" },
  { value: "5 channels", label: "Unified", sublabel: "One dashboard" },
];

export default function SocialProofBar({
  stats = defaultStats,
  className = "",
}: SocialProofBarProps) {
  return (
    <div className={`py-12 border-y border-white/10 ${className}`}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {stats.map((stat, index) => (
            <div key={index} className="flex flex-col items-center text-center">
              <div className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                {stat.value}
              </div>
              <div className="text-sm font-medium text-white mt-2">
                {stat.label}
              </div>
              {stat.sublabel && (
                <div className="text-xs text-white/50 mt-0.5">
                  {stat.sublabel}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
