"use client";

/**
 * ALSScorecard.tsx - ALS Score Radar Visualization
 * Phase 21: Deep Research & UI
 *
 * Hover pop-over showing the 5-point ALS breakdown:
 * - Data Quality (max 20)
 * - Authority (max 25)
 * - Company Fit (max 25)
 * - Timing (max 15)
 * - Risk (max 15)
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ALSBreakdown {
  dataQuality: number;
  authority: number;
  companyFit: number;
  timing: number;
  risk: number;
}

interface ALSScorecardProps {
  score: number;
  breakdown?: ALSBreakdown;
  showBadge?: boolean;
  size?: "sm" | "md" | "lg";
}

const getTier = (score: number): { name: string; color: string } => {
  if (score >= 85) return { name: "Hot", color: "from-orange-500 to-red-500" };
  if (score >= 60) return { name: "Warm", color: "from-yellow-500 to-orange-500" };
  if (score >= 35) return { name: "Cool", color: "from-blue-400 to-blue-600" };
  if (score >= 20) return { name: "Cold", color: "from-gray-400 to-gray-600" };
  return { name: "Dead", color: "from-gray-600 to-gray-800" };
};

const getTierBadgeColor = (tier: string): string => {
  switch (tier) {
    case "Hot":
      return "bg-orange-500/20 text-orange-400 border-orange-500/30 hover:bg-orange-500/30";
    case "Warm":
      return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30 hover:bg-yellow-500/30";
    case "Cool":
      return "bg-blue-500/20 text-blue-400 border-blue-500/30 hover:bg-blue-500/30";
    case "Cold":
      return "bg-gray-500/20 text-gray-400 border-gray-500/30 hover:bg-gray-500/30";
    default:
      return "bg-gray-600/20 text-gray-500 border-gray-600/30 hover:bg-gray-600/30";
  }
};

// Simple radar chart using SVG
function RadarChart({ breakdown }: { breakdown: ALSBreakdown }) {
  const center = 60;
  const maxRadius = 45;

  // Normalize values to percentages
  const values = [
    (breakdown.dataQuality / 20) * 100,
    (breakdown.authority / 25) * 100,
    (breakdown.companyFit / 25) * 100,
    (breakdown.timing / 15) * 100,
    (breakdown.risk / 15) * 100,
  ];

  const labels = ["Data", "Authority", "Fit", "Timing", "Risk"];
  const angles = values.map((_, i) => (Math.PI * 2 * i) / values.length - Math.PI / 2);

  // Calculate points for the polygon
  const points = values
    .map((value, i) => {
      const r = (value / 100) * maxRadius;
      const x = center + r * Math.cos(angles[i]);
      const y = center + r * Math.sin(angles[i]);
      return `${x},${y}`;
    })
    .join(" ");

  // Background grid lines
  const gridLevels = [0.25, 0.5, 0.75, 1];

  return (
    <svg viewBox="0 0 120 120" className="w-full h-full">
      {/* Background grid */}
      {gridLevels.map((level) => (
        <polygon
          key={level}
          points={angles
            .map((angle) => {
              const r = maxRadius * level;
              const x = center + r * Math.cos(angle);
              const y = center + r * Math.sin(angle);
              return `${x},${y}`;
            })
            .join(" ")}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="0.5"
        />
      ))}

      {/* Axis lines */}
      {angles.map((angle, i) => (
        <line
          key={i}
          x1={center}
          y1={center}
          x2={center + maxRadius * Math.cos(angle)}
          y2={center + maxRadius * Math.sin(angle)}
          stroke="rgba(255,255,255,0.1)"
          strokeWidth="0.5"
        />
      ))}

      {/* Data polygon */}
      <polygon
        points={points}
        fill="url(#radarGradient)"
        fillOpacity="0.5"
        stroke="url(#radarStroke)"
        strokeWidth="2"
      />

      {/* Data points */}
      {values.map((value, i) => {
        const r = (value / 100) * maxRadius;
        const x = center + r * Math.cos(angles[i]);
        const y = center + r * Math.sin(angles[i]);
        return (
          <circle
            key={i}
            cx={x}
            cy={y}
            r="3"
            fill="white"
            stroke="rgba(139, 92, 246, 1)"
            strokeWidth="1.5"
          />
        );
      })}

      {/* Labels */}
      {labels.map((label, i) => {
        const r = maxRadius + 12;
        const x = center + r * Math.cos(angles[i]);
        const y = center + r * Math.sin(angles[i]);
        return (
          <text
            key={label}
            x={x}
            y={y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-gray-400 text-[8px]"
          >
            {label}
          </text>
        );
      })}

      {/* Gradients */}
      <defs>
        <linearGradient id="radarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="rgba(59, 130, 246, 0.5)" />
          <stop offset="100%" stopColor="rgba(139, 92, 246, 0.5)" />
        </linearGradient>
        <linearGradient id="radarStroke" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="rgba(59, 130, 246, 1)" />
          <stop offset="100%" stopColor="rgba(139, 92, 246, 1)" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export function ALSScorecard({
  score,
  breakdown,
  showBadge = true,
  size = "md",
}: ALSScorecardProps) {
  const tier = getTier(score);
  const [isHovered, setIsHovered] = useState(false);

  const sizeClasses = {
    sm: "text-xs",
    md: "text-sm",
    lg: "text-base",
  };

  // Default breakdown if not provided
  const defaultBreakdown: ALSBreakdown = breakdown || {
    dataQuality: Math.round((score / 100) * 20),
    authority: Math.round((score / 100) * 25),
    companyFit: Math.round((score / 100) * 25),
    timing: Math.round((score / 100) * 15),
    risk: Math.round((score / 100) * 15),
  };

  const ScoreContent = (
    <div className="space-y-4 p-1">
      {/* Radar Chart */}
      <div className="w-32 h-32 mx-auto">
        <RadarChart breakdown={defaultBreakdown} />
      </div>

      {/* Score Details */}
      <div className="space-y-2">
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-400">Data Quality</span>
          <span className="text-white font-medium">
            {defaultBreakdown.dataQuality}/20
          </span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-400">Authority</span>
          <span className="text-white font-medium">
            {defaultBreakdown.authority}/25
          </span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-400">Company Fit</span>
          <span className="text-white font-medium">
            {defaultBreakdown.companyFit}/25
          </span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-400">Timing</span>
          <span className="text-white font-medium">
            {defaultBreakdown.timing}/15
          </span>
        </div>
        <div className="flex justify-between items-center text-xs">
          <span className="text-gray-400">Risk</span>
          <span className="text-white font-medium">
            {defaultBreakdown.risk}/15
          </span>
        </div>
      </div>

      {/* Total */}
      <div className="pt-2 border-t border-white/10">
        <div className="flex justify-between items-center">
          <span className="text-gray-300 font-medium">Total ALS Score</span>
          <span
            className={`font-bold bg-gradient-to-r ${tier.color} bg-clip-text text-transparent`}
          >
            {score}/100
          </span>
        </div>
      </div>
    </div>
  );

  if (!showBadge) {
    return <div className="bg-[#1a1a1f] rounded-lg p-4">{ScoreContent}</div>;
  }

  return (
    <TooltipProvider>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          <Badge
            className={`cursor-pointer transition-all ${getTierBadgeColor(tier.name)} ${sizeClasses[size]}`}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
          >
            {tier.name} ({score})
          </Badge>
        </TooltipTrigger>
        <TooltipContent
          side="bottom"
          className="w-64 bg-[#1a1a1f] border-white/10 p-4"
        >
          {ScoreContent}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default ALSScorecard;
