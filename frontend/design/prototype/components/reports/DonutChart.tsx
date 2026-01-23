"use client";

/**
 * Data point for the donut chart
 */
export interface DonutChartDataPoint {
  label: string;
  value: number;
  color: string;
}

/**
 * DonutChart props
 */
export interface DonutChartProps {
  /** Array of data points with label, value, and color */
  data: DonutChartDataPoint[];
  /** Chart size (width and height) */
  size?: number;
  /** Show legend */
  showLegend?: boolean;
  /** Center label */
  centerLabel?: string;
  /** Center value */
  centerValue?: string | number;
}

/**
 * DonutChart - Donut/pie chart component
 *
 * Features:
 * - SVG donut chart
 * - Center total display
 * - Legend with colors and values
 *
 * Design tokens from DESIGN_SYSTEM.md:
 * - Text primary: #1E293B
 * - Text secondary: #64748B
 */
export function DonutChart({
  data,
  size = 200,
  showLegend = true,
  centerLabel = "Total",
  centerValue,
}: DonutChartProps) {
  // Calculate total
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const displayValue = centerValue ?? total;

  // Donut dimensions
  const center = size / 2;
  const radius = size / 2 - 10;
  const innerRadius = radius * 0.6;
  const strokeWidth = radius - innerRadius;

  // Calculate arc paths
  let currentAngle = -90; // Start from top

  const arcs = data.map((d) => {
    const percentage = total > 0 ? d.value / total : 0;
    const angle = percentage * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    currentAngle = endAngle;

    // Convert angles to radians
    const startRad = (startAngle * Math.PI) / 180;
    const endRad = (endAngle * Math.PI) / 180;

    // Calculate arc points
    const arcRadius = (radius + innerRadius) / 2;
    const x1 = center + arcRadius * Math.cos(startRad);
    const y1 = center + arcRadius * Math.sin(startRad);
    const x2 = center + arcRadius * Math.cos(endRad);
    const y2 = center + arcRadius * Math.sin(endRad);

    // Large arc flag
    const largeArc = angle > 180 ? 1 : 0;

    // Calculate circumference for stroke-dasharray
    const circumference = 2 * Math.PI * arcRadius;
    const dashLength = (percentage * circumference);

    return {
      ...d,
      percentage,
      startAngle,
      endAngle,
      arcRadius,
      circumference,
      dashLength,
      dashOffset: 0,
    };
  });

  // Calculate cumulative offsets
  let cumulativeOffset = 0;
  const arcsWithOffsets = arcs.map((arc) => {
    const offset = cumulativeOffset;
    cumulativeOffset += arc.dashLength;
    return { ...arc, dashOffset: arc.circumference - offset };
  });

  return (
    <div className="flex items-center gap-8">
      {/* Donut SVG */}
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Background circle */}
          <circle
            cx={center}
            cy={center}
            r={(radius + innerRadius) / 2}
            fill="none"
            stroke="#F1F5F9"
            strokeWidth={strokeWidth}
          />

          {/* Data arcs */}
          {arcsWithOffsets.map((arc, i) => (
            <circle
              key={i}
              cx={center}
              cy={center}
              r={arc.arcRadius}
              fill="none"
              stroke={arc.color}
              strokeWidth={strokeWidth}
              strokeDasharray={`${arc.dashLength} ${arc.circumference}`}
              strokeDashoffset={arc.dashOffset}
              transform={`rotate(-90 ${center} ${center})`}
              className="transition-all duration-300"
            />
          ))}
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xs text-[#64748B]">{centerLabel}</span>
          <span className="text-2xl font-bold text-[#1E293B]">{displayValue}</span>
        </div>
      </div>

      {/* Legend */}
      {showLegend && (
        <div className="flex flex-col gap-3">
          {data.map((d, i) => (
            <div key={i} className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: d.color }}
              />
              <div className="flex flex-col">
                <span className="text-sm text-[#1E293B]">{d.label}</span>
                <span className="text-xs text-[#64748B]">
                  {d.value} ({total > 0 ? Math.round((d.value / total) * 100) : 0}%)
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default DonutChart;
