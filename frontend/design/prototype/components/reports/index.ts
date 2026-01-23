/**
 * Reports Components - Agency OS Dashboard Prototype
 *
 * This module exports all report-related components for the dashboard.
 * All components use Tailwind CSS and lucide-react icons.
 * Charts are simple SVG implementations - no external library required.
 *
 * This is a PROTOTYPE - all components use static demo data.
 */

// Individual report components
export { MetricCard } from "./MetricCard";
export type { MetricCardProps } from "./MetricCard";

export { DateRangePicker } from "./DateRangePicker";
export type { DateRangePickerProps } from "./DateRangePicker";

export { LineChart } from "./LineChart";
export type { LineChartProps, LineChartDataPoint } from "./LineChart";

export { BarChart } from "./BarChart";
export type { BarChartProps, BarChartDataPoint } from "./BarChart";

export { DonutChart } from "./DonutChart";
export type { DonutChartProps, DonutChartDataPoint } from "./DonutChart";

export { ChannelBreakdown } from "./ChannelBreakdown";
export type { ChannelBreakdownProps, ChannelMetrics } from "./ChannelBreakdown";

export { CampaignPerformance } from "./CampaignPerformance";
export type { CampaignPerformanceProps, CampaignPerformanceData } from "./CampaignPerformance";

export { TrendChart } from "./TrendChart";
export type { TrendChartProps, TrendDataPoint } from "./TrendChart";

// Full page component
export { ReportsPage } from "./ReportsPage";
