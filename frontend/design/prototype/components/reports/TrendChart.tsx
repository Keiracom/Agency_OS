"use client";

import { useState } from "react";

/**
 * Data point for the trend chart
 */
export interface TrendDataPoint {
  date: string;
  count: number;
}

/**
 * TrendChart props
 */
export interface TrendChartProps {
  /** Array of data points with date and count */
  data: TrendDataPoint[];
  /** Target value for overlay line */
  target?: number;
  /** Chart height */
  height?: number;
  /** Line color */
  color?: string;
}

/**
 * TrendChart - Meetings over time component
 *
 * Features:
 * - Line chart showing trend
 * - 30-day view
 * - Target line overlay
 * - Hover tooltips
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Primary accent: #3B82F6 (accent-blue)
 * - Target line: #10B981 (accent-green)
 * - Grid: #E2E8F0 (card-border)
 * - Text: #64748B (text-secondary)
 */
export function TrendChart({
  data,
  target,
  height = 280,
  color = "#3B82F6",
}: TrendChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Chart dimensions
  const padding = { top: 30, right: 30, bottom: 50, left: 50 };
  const width = 800;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate scales
  const counts = data.map((d) => d.count);
  const maxY = Math.max(Math.max(...counts), target || 0);
  const minY = 0;
  const yRange = maxY - minY || 1;

  // Generate path
  const getX = (index: number) =>
    padding.left + (index / (data.length - 1 || 1)) * chartWidth;
  const getY = (value: number) =>
    padding.top + chartHeight - ((value - minY) / yRange) * chartHeight;

  const pathD = data
    .map((d, i) => {
      const x = getX(i);
      const y = getY(d.count);
      return `${i === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  // Area path
  const areaD = `${pathD} L ${getX(data.length - 1)} ${
    padding.top + chartHeight
  } L ${getX(0)} ${padding.top + chartHeight} Z`;

  // Y-axis labels (5 steps)
  const yLabels = Array.from({ length: 5 }, (_, i) => {
    const value = minY + (yRange * (4 - i)) / 4;
    return {
      value: Math.round(value),
      y: padding.top + (i / 4) * chartHeight,
    };
  });

  // Grid lines
  const gridLines = yLabels.map((label) => label.y);

  // Format date for display
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-AU", { month: "short", day: "numeric" });
  };

  // Calculate total meetings
  const totalMeetings = data.reduce((sum, d) => sum + d.count, 0);
  const avgMeetings = data.length > 0 ? (totalMeetings / data.length).toFixed(1) : 0;

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm">
      <div className="px-6 py-4 border-b border-[#E2E8F0] flex items-center justify-between">
        <h2 className="text-sm font-semibold text-[#64748B] uppercase tracking-wider">
          Meetings Trend
        </h2>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 rounded-full bg-[#3B82F6]" />
            <span className="text-xs text-[#64748B]">Meetings</span>
          </div>
          {target && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-0.5 rounded-full bg-[#10B981]" />
              <span className="text-xs text-[#64748B]">Target ({target}/day)</span>
            </div>
          )}
        </div>
      </div>

      {/* Summary stats */}
      <div className="px-6 py-4 bg-[#F8FAFC] border-b border-[#E2E8F0] flex gap-8">
        <div>
          <span className="text-xs text-[#64748B] block">Total Meetings</span>
          <span className="text-xl font-bold text-[#1E293B]">{totalMeetings}</span>
        </div>
        <div>
          <span className="text-xs text-[#64748B] block">Daily Average</span>
          <span className="text-xl font-bold text-[#1E293B]">{avgMeetings}</span>
        </div>
        {target && (
          <div>
            <span className="text-xs text-[#64748B] block">vs Target</span>
            <span
              className={`text-xl font-bold ${
                Number(avgMeetings) >= target ? "text-[#10B981]" : "text-[#EF4444]"
              }`}
            >
              {Number(avgMeetings) >= target ? "On Track" : "Below Target"}
            </span>
          </div>
        )}
      </div>

      {/* Chart */}
      <div className="p-6">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full"
          style={{ height: `${height}px` }}
        >
          {/* Gradient definition */}
          <defs>
            <linearGradient id="trendGradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0.2" />
              <stop offset="100%" stopColor={color} stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {gridLines.map((y, i) => (
            <line
              key={i}
              x1={padding.left}
              y1={y}
              x2={width - padding.right}
              y2={y}
              stroke="#E2E8F0"
              strokeDasharray="4 4"
            />
          ))}

          {/* Y-axis labels */}
          {yLabels.map((label, i) => (
            <text
              key={i}
              x={padding.left - 10}
              y={label.y}
              textAnchor="end"
              alignmentBaseline="middle"
              className="text-xs fill-[#64748B]"
            >
              {label.value}
            </text>
          ))}

          {/* X-axis labels */}
          {data.map((d, i) => {
            // Show every nth label to avoid crowding
            const showLabel = i % Math.ceil(data.length / 8) === 0 || i === data.length - 1;
            if (!showLabel) return null;
            return (
              <text
                key={i}
                x={getX(i)}
                y={height - 15}
                textAnchor="middle"
                className="text-xs fill-[#64748B]"
              >
                {formatDate(d.date)}
              </text>
            );
          })}

          {/* Target line */}
          {target && (
            <line
              x1={padding.left}
              y1={getY(target)}
              x2={width - padding.right}
              y2={getY(target)}
              stroke="#10B981"
              strokeWidth="2"
              strokeDasharray="8 4"
            />
          )}

          {/* Area fill */}
          <path d={areaD} fill="url(#trendGradient)" />

          {/* Line */}
          <path d={pathD} fill="none" stroke={color} strokeWidth="2.5" />

          {/* Data points */}
          {data.map((d, i) => (
            <g key={i}>
              <circle
                cx={getX(i)}
                cy={getY(d.count)}
                r={hoveredIndex === i ? 6 : 4}
                fill="white"
                stroke={color}
                strokeWidth="2"
                className="cursor-pointer transition-all"
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            </g>
          ))}

          {/* Tooltip */}
          {hoveredIndex !== null && (
            <g>
              <rect
                x={getX(hoveredIndex) - 50}
                y={getY(data[hoveredIndex].count) - 45}
                width="100"
                height="35"
                rx="6"
                fill="#1E293B"
              />
              <text
                x={getX(hoveredIndex)}
                y={getY(data[hoveredIndex].count) - 28}
                textAnchor="middle"
                className="text-xs fill-[#94A3B8]"
              >
                {formatDate(data[hoveredIndex].date)}
              </text>
              <text
                x={getX(hoveredIndex)}
                y={getY(data[hoveredIndex].count) - 13}
                textAnchor="middle"
                className="text-sm fill-white font-semibold"
              >
                {data[hoveredIndex].count} meetings
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  );
}

export default TrendChart;
