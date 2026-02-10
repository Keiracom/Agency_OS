'use client';

import { LeadRadarScores } from '@/data/mock-lead-detail';
import { BarChart3 } from 'lucide-react';

interface LeadRadarChartProps {
  scores: LeadRadarScores;
}

interface ScoreBarProps {
  label: string;
  value: number;
  max: number;
  inverted?: boolean; // For risk: lower is better
}

function ScoreBar({ label, value, max, inverted = false }: ScoreBarProps) {
  const percentage = (value / max) * 100;
  // For display, if inverted, show complement
  const displayPercentage = inverted ? 100 - percentage : percentage;
  
  // Color logic: high = green, medium = orange, low = blue
  let colorClass = 'bg-status-success'; // green
  if (displayPercentage < 60) {
    colorClass = 'bg-accent-blue'; // blue for low
  } else if (displayPercentage < 80) {
    colorClass = 'bg-status-warning'; // orange for medium
  }

  return (
    <div className="flex items-center gap-4 py-3 border-b border-border-subtle last:border-b-0">
      <span className="flex-1 text-sm text-secondary">{label}</span>
      <div className="w-28 h-2 bg-elevated rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
          style={{ width: `${displayPercentage}%` }}
        />
      </div>
      <span className="text-sm font-semibold font-mono text-primary min-w-[50px] text-right">
        {inverted ? `${100 - value}%` : `${value}%`}
      </span>
    </div>
  );
}

export function LeadRadarChart({ scores }: LeadRadarChartProps) {
  // Calculate points for SVG radar polygon
  const centerX = 100;
  const centerY = 100;
  const maxRadius = 70;

  // Order: dataQuality (top), authority (right), companyFit (bottom-right), timing (bottom-left), engagement (left)
  const dataPoints = [
    { angle: -90, value: scores.dataQuality / 100 },   // top
    { angle: -18, value: scores.authority / 100 },     // right
    { angle: 54, value: scores.companyFit / 100 },     // bottom-right
    { angle: 126, value: (100 - scores.risk) / 100 },  // bottom-left (inverted risk)
    { angle: 198, value: scores.timing / 100 },        // left
  ];

  const points = dataPoints.map((point) => {
    const radians = (point.angle * Math.PI) / 180;
    const radius = maxRadius * point.value;
    return {
      x: centerX + radius * Math.cos(radians),
      y: centerY + radius * Math.sin(radians),
    };
  });

  const polygonPoints = points.map((p) => `${p.x},${p.y}`).join(' ');

  // Grid polygons (at 25%, 50%, 75%, 100%)
  const gridLevels = [0.25, 0.5, 0.75, 1];
  const gridPolygons = gridLevels.map((level) => {
    const gridPoints = dataPoints.map((point) => {
      const radians = (point.angle * Math.PI) / 180;
      const radius = maxRadius * level;
      return `${centerX + radius * Math.cos(radians)},${centerY + radius * Math.sin(radians)}`;
    });
    return gridPoints.join(' ');
  });

  // Axis lines from center to each vertex
  const axisEndpoints = dataPoints.map((point) => {
    const radians = (point.angle * Math.PI) / 180;
    return {
      x: centerX + maxRadius * Math.cos(radians),
      y: centerY + maxRadius * Math.sin(radians),
    };
  });

  const labels = [
    { text: 'Data Quality', x: 100, y: 20 },
    { text: 'Authority', x: 175, y: 70 },
    { text: 'Company Fit', x: 155, y: 155 },
    { text: 'Timing', x: 45, y: 155 },
    { text: 'Low Risk', x: 25, y: 70 },
  ];

  return (
    <div className="bg-surface border border-border-subtle rounded-xl overflow-hidden">
      <div className="px-6 py-5 border-b border-border-subtle flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BarChart3 className="w-4 h-4 text-accent-primary" />
          <span className="text-sm font-semibold text-primary">Engagement Profile</span>
        </div>
        <span className="text-xs text-muted">Score breakdown by signal</span>
      </div>

      <div className="p-6">
        <div className="flex gap-8 items-center">
          {/* Radar Chart SVG */}
          <div className="w-64 h-64 shrink-0">
            <svg viewBox="0 0 200 200" className="w-full h-full">
              {/* Grid polygons */}
              {gridPolygons.map((points, i) => (
                <polygon
                  key={i}
                  points={points}
                  fill="none"
                  stroke="var(--border-subtle)"
                  strokeWidth="1"
                  opacity={0.3}
                />
              ))}

              {/* Axis lines */}
              {axisEndpoints.map((point, i) => (
                <line
                  key={i}
                  x1={centerX}
                  y1={centerY}
                  x2={point.x}
                  y2={point.y}
                  stroke="var(--border-default)"
                  strokeWidth="1"
                />
              ))}

              {/* Data polygon */}
              <defs>
                <linearGradient id="radarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#7C3AED" stopOpacity="0.4" />
                  <stop offset="100%" stopColor="#3B82F6" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              <polygon
                points={polygonPoints}
                fill="url(#radarGradient)"
                stroke="#7C3AED"
                strokeWidth="2"
                opacity="0.9"
              />

              {/* Data points */}
              {points.map((point, i) => (
                <circle
                  key={i}
                  cx={point.x}
                  cy={point.y}
                  r="5"
                  fill="#7C3AED"
                />
              ))}

              {/* Labels */}
              {labels.map((label, i) => (
                <text
                  key={i}
                  x={label.x}
                  y={label.y}
                  textAnchor="middle"
                  fill="var(--text-secondary)"
                  fontSize="9"
                  fontWeight="500"
                >
                  {label.text}
                </text>
              ))}
            </svg>
          </div>

          {/* Score bars */}
          <div className="flex-1">
            <ScoreBar label="Data Quality" value={scores.dataQuality} max={100} />
            <ScoreBar label="Authority (Title)" value={scores.authority} max={100} />
            <ScoreBar label="Company Fit" value={scores.companyFit} max={100} />
            <ScoreBar label="Timing" value={scores.timing} max={100} />
            <ScoreBar label="Risk Level" value={scores.risk} max={100} inverted />
          </div>
        </div>
      </div>
    </div>
  );
}
