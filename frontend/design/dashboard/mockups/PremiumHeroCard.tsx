"use client";

import { TrendingUp, TrendingDown, Calendar, Zap } from "lucide-react";

/**
 * Premium Hero Metrics Card
 * 
 * Inspired by EqtyLab's dark glassmorphism aesthetic.
 * Features: aurora glow background, glass card, animated accents.
 * 
 * Drop this into components/dashboard/ and import into your dashboard page.
 */

interface PremiumHeroCardProps {
  meetingsBooked: number;
  showRate: number;
  vsLastMonth: number;
  status: "ahead" | "on_track" | "behind";
}

export function PremiumHeroCard({
  meetingsBooked = 12,
  showRate = 85,
  vsLastMonth = 3,
  status = "on_track",
}: PremiumHeroCardProps) {
  const statusConfig = {
    ahead: { label: "Ahead of pace", color: "text-emerald-400", glow: "shadow-emerald-500/20" },
    on_track: { label: "On track", color: "text-cyan-400", glow: "shadow-cyan-500/20" },
    behind: { label: "Behind pace", color: "text-amber-400", glow: "shadow-amber-500/20" },
  };

  const { label, color, glow } = statusConfig[status];
  const isPositive = vsLastMonth >= 0;

  return (
    <div className="relative overflow-hidden rounded-2xl">
      {/* Aurora background effect */}
      <div className="absolute inset-0 bg-[#0a0a0f]">
        <div 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] opacity-30"
          style={{
            background: "radial-gradient(ellipse at center, rgba(16,185,129,0.3) 0%, rgba(6,182,212,0.15) 40%, transparent 70%)",
            filter: "blur(40px)",
            animation: "pulse 8s ease-in-out infinite",
          }}
        />
        {/* Flowing wave line */}
        <svg 
          className="absolute bottom-0 left-0 w-full h-24 opacity-20"
          viewBox="0 0 1200 100"
          preserveAspectRatio="none"
        >
          <path
            d="M0,50 Q300,20 600,50 T1200,50 L1200,100 L0,100 Z"
            fill="url(#wave-gradient)"
          />
          <defs>
            <linearGradient id="wave-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="rgba(16,185,129,0.5)" />
              <stop offset="50%" stopColor="rgba(6,182,212,0.5)" />
              <stop offset="100%" stopColor="rgba(16,185,129,0.5)" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {/* Glass card content */}
      <div 
        className={`relative z-10 p-8 backdrop-blur-xl bg-white/[0.03] border border-white/[0.08] rounded-2xl ${glow} shadow-2xl`}
      >
        <div className="grid grid-cols-2 gap-8">
          {/* Meetings Booked */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-gray-400 text-sm font-medium">
              <Calendar className="w-4 h-4" />
              <span>Meetings Booked</span>
            </div>
            <div className="flex items-baseline gap-3">
              <span className="text-5xl font-light text-white tracking-tight">
                {meetingsBooked}
              </span>
              <div className={`flex items-center gap-1 text-sm ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
                {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                <span>{isPositive ? "+" : ""}{vsLastMonth} vs last month</span>
              </div>
            </div>
            <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${color} bg-white/[0.05]`}>
              <Zap className="w-3 h-3" />
              {label}
            </div>
          </div>

          {/* Show Rate */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-gray-400 text-sm font-medium">
              <span>Show Rate</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-5xl font-light text-white tracking-tight">
                {showRate}
              </span>
              <span className="text-2xl text-gray-500">%</span>
            </div>
            {/* Mini progress bar */}
            <div className="w-full h-1.5 bg-white/[0.08] rounded-full overflow-hidden">
              <div 
                className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500"
                style={{ width: `${showRate}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* CSS for pulse animation */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: translate(-50%, -50%) scale(1); }
          50% { opacity: 0.5; transform: translate(-50%, -50%) scale(1.1); }
        }
      `}</style>
    </div>
  );
}

export default PremiumHeroCard;
