"use client";

/**
 * Data point for the bar chart
 */
export interface BarChartDataPoint {
  [key: string]: string | number;
}

/**
 * BarChart props
 */
export interface BarChartProps {
  /** Array of data points */
  data: BarChartDataPoint[];
  /** Key for x-axis values (labels) */
  xKey: string;
  /** Key for y-axis values (bar heights) */
  yKey: string;
  /** Bar color */
  color?: string;
  /** Chart height */
  height?: number;
}

/**
 * BarChart - Vertical bar chart component
 *
 * Features:
 * - Vertical bars
 * - Axis labels
 * - Value labels on bars
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Primary accent: #3B82F6 (accent-blue)
 * - Grid: #E2E8F0 (card-border)
 * - Text: #64748B (text-secondary)
 */
export function BarChart({
  data,
  xKey,
  yKey,
  color = "#3B82F6",
  height = 240,
}: BarChartProps) {
  // Chart dimensions
  const padding = { top: 30, right: 20, bottom: 50, left: 50 };
  const width = 600;
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Calculate scales
  const yValues = data.map((d) => Number(d[yKey]));
  const maxY = Math.max(...yValues);
  const minY = 0;
  const yRange = maxY - minY || 1;

  // Bar dimensions
  const barWidth = (chartWidth / data.length) * 0.6;
  const barGap = (chartWidth / data.length) * 0.4;

  const getX = (index: number) =>
    padding.left + index * (barWidth + barGap) + barGap / 2;
  const getHeight = (value: number) => ((value - minY) / yRange) * chartHeight;
  const getY = (value: number) => padding.top + chartHeight - getHeight(value);

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

        {/* Bars */}
        {data.map((d, i) => {
          const value = Number(d[yKey]);
          const barHeight = getHeight(value);
          const x = getX(i);
          const y = getY(value);

          return (
            <g key={i}>
              {/* Bar */}
              <rect
                x={x}
                y={y}
                width={barWidth}
                height={barHeight}
                fill={color}
                rx="4"
                className="transition-all hover:opacity-80"
              />

              {/* Value label on bar */}
              <text
                x={x + barWidth / 2}
                y={y - 8}
                textAnchor="middle"
                className="text-xs fill-[#1E293B] font-medium"
              >
                {value}
              </text>

              {/* X-axis label */}
              <text
                x={x + barWidth / 2}
                y={height - 15}
                textAnchor="middle"
                className="text-xs fill-[#64748B]"
              >
                {String(d[xKey]).slice(0, 10)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default BarChart;
