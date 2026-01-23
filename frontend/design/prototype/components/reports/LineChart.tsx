"use client";

import { useState } from "react";

/**
 * Data point for the line chart
 */
export interface LineChartDataPoint {
  [key: string]: string | number;
}

/**
 * LineChart props
 */
export interface LineChartProps {
  /** Array of data points */
  data: LineChartDataPoint[];
  /** Key for x-axis values */
  xKey: string;
  /** Key for y-axis values */
  yKey: string;
  /** Line color */
  color?: string;
  /** Chart height */
  height?: number;
}

/**
 * LineChart - Simple SVG line chart component
 *
 * Features:
 * - SVG line chart
 * - Grid lines
 * - Axis labels
 * - Hover tooltip placeholder
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Primary accent: #3B82F6 (accent-blue)
 * - Grid: #E2E8F0 (card-border)
 * - Text: #64748B (text-secondary)
 */
export function LineChart({
  data,
  xKey,
  yKey,
  color = "#3B82F6",
  height = 240,
}: LineChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // Chart dimensions
  const padding = { top: 20, right: 20, bottom: 40, left: 50 };
  const width = 600;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate scales
  const yValues = data.map((d) => Number(d[yKey]));
  const maxY = Math.max(...yValues);
  const minY = Math.min(0, Math.min(...yValues));
  const yRange = maxY - minY || 1;

  // Generate path
  const getX = (index: number) =>
    padding.left + (index / (data.length - 1 || 1)) * chartWidth;
  const getY = (value: number) =>
    padding.top + chartHeight - ((value - minY) / yRange) * chartHeight;

  const pathD = data
    .map((d, i) => {
      const x = getX(i);
      const y = getY(Number(d[yKey]));
      return `${i === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");

  // Area path (for gradient fill)
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

  return (
    <div className="w-full">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        style={{ height: `${height}px` }}
      >
        {/* Gradient definition */}
        <defs>
          <linearGradient id="lineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
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
          const showLabel = i % Math.ceil(data.length / 6) === 0 || i === data.length - 1;
          if (!showLabel) return null;
          return (
            <text
              key={i}
              x={getX(i)}
              y={height - 10}
              textAnchor="middle"
              className="text-xs fill-[#64748B]"
            >
              {String(d[xKey]).slice(0, 6)}
            </text>
          );
        })}

        {/* Area fill */}
        <path d={areaD} fill="url(#lineGradient)" />

        {/* Line */}
        <path d={pathD} fill="none" stroke={color} strokeWidth="2" />

        {/* Data points */}
        {data.map((d, i) => (
          <g key={i}>
            <circle
              cx={getX(i)}
              cy={getY(Number(d[yKey]))}
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
              x={getX(hoveredIndex) - 40}
              y={getY(Number(data[hoveredIndex][yKey])) - 35}
              width="80"
              height="25"
              rx="4"
              fill="#1E293B"
            />
            <text
              x={getX(hoveredIndex)}
              y={getY(Number(data[hoveredIndex][yKey])) - 18}
              textAnchor="middle"
              className="text-xs fill-white font-medium"
            >
              {data[hoveredIndex][xKey]}: {data[hoveredIndex][yKey]}
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

export default LineChart;
