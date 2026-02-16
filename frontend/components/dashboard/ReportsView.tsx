'use client';

import React, { useState } from 'react';
import { 
  BarChart3, TrendingUp, Mail, Phone, MessageSquare, 
  Briefcase, Package, Zap, Lightbulb, MapPin, Target,
  Download, FileText, ChevronUp, ChevronDown, Flame
} from 'lucide-react';

// ============================================================================
// MOCK DATA (matches API shape)
// ============================================================================

const mockReportData = {
  period: 'Feb 1-28, 2026',
  summary: {
    meetingsBooked: { value: 52, change: 23, trend: 'up' as const },
    pipelineGenerated: { value: 221000, change: 31, trend: 'up' as const },
    showRate: { value: 68, change: 5, trend: 'up' as const },
    roi: { value: 8.2, change: 1.4, trend: 'up' as const },
  },
  channels: [
    { id: 'email', name: 'Email', icon: 'mail', volume: 3420, delivered: 3318, engaged: 1245, replied: 156, replyRate: 4.6, meetings: 18, color: 'purple' },
    { id: 'linkedin', name: 'LinkedIn', icon: 'briefcase', volume: 890, delivered: 712, engaged: 456, replied: 67, replyRate: 7.5, meetings: 12, color: 'blue' },
    { id: 'sms', name: 'SMS', icon: 'message', volume: 520, delivered: 507, engaged: 478, replied: 142, replyRate: 27.3, meetings: 8, color: 'teal' },
    { id: 'voice', name: 'Voice AI', icon: 'phone', volume: 180, delivered: 180, engaged: 118, replied: 42, replyRate: 23.3, meetings: 11, color: 'amber' },
    { id: 'mail', name: 'Direct Mail', icon: 'package', volume: 45, delivered: 45, engaged: 12, replied: 3, replyRate: 6.7, meetings: 3, color: 'pink' },
  ],
  funnel: [
    { stage: 'Contacted', count: 5055, percentage: 100, label: 'Total Touches' },
    { stage: 'Engaged', count: 2123, percentage: 42, label: 'Opens/Views' },
    { stage: 'Replied', count: 404, percentage: 8, label: 'Positive' },
    { stage: 'Booked', count: 52, percentage: 1, label: 'Meetings' },
  ],
  meetingsOverTime: [
    { month: 'Sep', value: 6 },
    { month: 'Oct', value: 8 },
    { month: 'Nov', value: 7 },
    { month: 'Dec', value: 10 },
    { month: 'Jan', value: 9 },
    { month: 'Feb', value: 12 },
  ],
  responseRates: {
    overall: 8.5,
    sms: 27,
    voice: 23,
  },
  insights: {
    whoConverts: [
      { role: 'CEO/Founder', multiplier: 2.3 },
      { role: 'Marketing Dir', multiplier: 1.8 },
    ],
    bestTiming: { day: 'Tuesday', hour: '10am' },
    discovery: 'Leads with "Growth" in title convert 2.1x better. Auto-adjusting targeting.',
  },
  leadSources: [
    { name: 'Data Partner', count: 847, percentage: 65, color: 'purple' },
    { name: 'LinkedIn', count: 286, percentage: 22, color: 'blue' },
    { name: 'Referral', count: 104, percentage: 8, color: 'teal' },
    { name: 'Website', count: 65, percentage: 5, color: 'amber' },
  ],
  tierBreakdown: [
    { tier: 'Hot', leads: 127, convRate: 18.9, width: 85 },
    { tier: 'Warm', leads: 384, convRate: 5.2, width: 65 },
    { tier: 'Cool', leads: 512, convRate: 1.4, width: 45 },
    { tier: 'Cold', leads: 227, convRate: 0.4, width: 25 },
  ],
  voicePerformance: {
    callsMade: 180,
    connected: 118,
    booked: 11,
    bookRate: 9.3,
    objections: [
      { text: '"Using another agency"', count: 12, recovery: 67 },
      { text: '"Not the right time"', count: 8, recovery: 63 },
      { text: '"Too expensive"', count: 4, recovery: 50 },
    ],
  },
  roiSummary: {
    totalSpend: 27000,
    pipelineGenerated: 221000,
    roi: 8.2,
  },
};

// ============================================================================
// STYLE CONSTANTS (Bloomberg Dark Mode)
// ============================================================================

const colors = {
  bgVoid: '#05050A',
  bgBase: '#0A0A12',
  bgSurface: '#12121D',
  bgSurfaceHover: '#1A1A28',
  bgElevated: '#222233',
  borderSubtle: '#1E1E2E',
  borderDefault: '#2A2A3D',
  borderStrong: '#3A3A50',
  textPrimary: '#F8F8FC',
  textSecondary: '#B4B4C4',
  textMuted: '#6E6E82',
  accentPrimary: '#7C3AED',
  accentPrimaryHover: '#9061F9',
  accentTeal: '#14B8A6',
  accentBlue: '#3B82F6',
  accentPink: '#EC4899',
  statusSuccess: '#22C55E',
  statusWarning: '#F59E0B',
  statusError: '#EF4444',
  tierHot: '#EF4444',
  tierWarm: '#F59E0B',
  tierCool: '#3B82F6',
  tierCold: '#6B7280',
};

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

// Channel Icon Mapper
const ChannelIcon: React.FC<{ channel: string; className?: string; style?: React.CSSProperties }> = ({ channel, className = 'w-5 h-5', style }) => {
  switch (channel) {
    case 'mail': return <Mail className={className} style={style} />;
    case 'briefcase': return <Briefcase className={className} style={style} />;
    case 'message': return <MessageSquare className={className} style={style} />;
    case 'phone': return <Phone className={className} style={style} />;
    case 'package': return <Package className={className} style={style} />;
    default: return <Mail className={className} style={style} />;
  }
};

// Executive Summary Card
const ExecCard: React.FC<{
  label: string;
  value: string | number;
  suffix?: string;
  change: number;
  trend: 'up' | 'down';
  periodLabel?: string;
  accentColor: string;
}> = ({ label, value, suffix, change, trend, periodLabel = 'vs last period', accentColor }) => (
  <div 
    className="relative rounded-xl p-5 overflow-hidden border"
    style={{ 
      background: colors.bgSurface, 
      borderColor: colors.borderSubtle,
    }}
  >
    {/* Top accent line */}
    <div 
      className="absolute top-0 left-0 right-0 h-0.5"
      style={{ background: accentColor }}
    />
    
    <div 
      className="text-[11px] font-semibold uppercase tracking-wider mb-2"
      style={{ color: colors.textMuted }}
    >
      {label}
    </div>
    
    <div 
      className="text-4xl font-extrabold font-mono leading-none"
      style={{ color: colors.textPrimary }}
    >
      {value}
      {suffix && (
        <span className="text-lg" style={{ color: colors.textMuted }}>{suffix}</span>
      )}
    </div>
    
    <div className="flex items-center gap-2 mt-3 text-xs">
      <span 
        className="flex items-center gap-1 font-semibold"
        style={{ color: trend === 'up' ? colors.statusSuccess : colors.statusError }}
      >
        {trend === 'up' ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {change}%
      </span>
      <span style={{ color: colors.textMuted }}>{periodLabel}</span>
    </div>
  </div>
);

// Channel Mini Card
const ChannelMiniCard: React.FC<{
  channel: typeof mockReportData.channels[0];
  maxMeetings: number;
}> = ({ channel, maxMeetings }) => {
  const colorMap: Record<string, string> = {
    purple: colors.accentPrimary,
    blue: colors.accentBlue,
    teal: colors.accentTeal,
    amber: colors.statusWarning,
    pink: colors.accentPink,
  };
  const accent = colorMap[channel.color] || colors.accentPrimary;
  
  return (
    <div 
      className="rounded-lg p-4 text-center"
      style={{ background: colors.bgBase }}
    >
      <div className="text-2xl mb-2 flex justify-center" style={{ color: accent }}>
        <ChannelIcon channel={channel.icon} className="w-6 h-6" />
      </div>
      <div 
        className="text-[11px] font-semibold uppercase tracking-wider mb-3"
        style={{ color: colors.textMuted }}
      >
        {channel.name}
      </div>
      
      <div className="mb-2">
        <div className="text-xl font-bold font-mono" style={{ color: colors.textPrimary }}>
          {channel.volume.toLocaleString()}
        </div>
        <div className="text-[10px]" style={{ color: colors.textMuted }}>Sent</div>
      </div>
      
      <div className="mb-2">
        <div className="text-xl font-bold font-mono" style={{ color: accent }}>
          {channel.replyRate}%
        </div>
        <div className="text-[10px]" style={{ color: colors.textMuted }}>Reply Rate</div>
      </div>
      
      <div className="mb-2">
        <div className="text-xl font-bold font-mono" style={{ color: colors.statusSuccess }}>
          {channel.meetings}
        </div>
        <div className="text-[10px]" style={{ color: colors.textMuted }}>Meetings</div>
      </div>
      
      {/* Mini progress bar */}
      <div className="h-1 rounded-full mt-2" style={{ background: colors.bgSurface }}>
        <div 
          className="h-full rounded-full transition-all duration-500"
          style={{ 
            width: `${(channel.meetings / maxMeetings) * 100}%`,
            background: accent,
          }}
        />
      </div>
    </div>
  );
};

// Progress Ring
const ProgressRing: React.FC<{
  value: number;
  label: string;
  color: string;
}> = ({ value, label, color }) => {
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (value / 100) * circumference;
  
  return (
    <div className="text-center">
      <div className="relative w-20 h-20 mx-auto">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            strokeWidth="8"
            stroke={colors.bgBase}
          />
          <circle
            cx="50" cy="50" r="40"
            fill="none"
            strokeWidth="8"
            stroke={color}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            className="transition-all duration-500"
          />
        </svg>
        <span 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-lg font-bold font-mono"
          style={{ color: colors.textPrimary }}
        >
          {value}%
        </span>
      </div>
      <div 
        className="text-[11px] font-medium uppercase tracking-wider mt-2"
        style={{ color: colors.textMuted }}
      >
        {label}
      </div>
    </div>
  );
};

// Funnel Stage
const FunnelStage: React.FC<{
  stage: string;
  count: number;
  percentage: number;
  label: string;
  index: number;
}> = ({ stage, count, percentage, label, index }) => {
  const stageColors = [
    colors.accentPrimary,
    colors.accentBlue,
    colors.accentTeal,
    colors.statusSuccess,
  ];
  
  return (
    <div className="flex items-center gap-4">
      <div 
        className="w-24 text-right text-xs font-medium"
        style={{ color: colors.textSecondary }}
      >
        {stage}
      </div>
      <div 
        className="flex-1 h-8 rounded-md overflow-hidden relative"
        style={{ background: colors.bgBase }}
      >
        <div 
          className="h-full rounded-md flex items-center justify-end pr-3 transition-all duration-500"
          style={{ 
            width: `${percentage}%`,
            background: `linear-gradient(90deg, ${stageColors[index]}40, ${stageColors[index]})`,
          }}
        >
          <span className="text-xs font-semibold font-mono text-text-primary">
            {percentage}%
          </span>
        </div>
      </div>
      <div className="w-24">
        <div className="text-sm font-bold font-mono" style={{ color: colors.textPrimary }}>
          {count.toLocaleString()}
        </div>
        <div className="text-[11px]" style={{ color: colors.textMuted }}>{label}</div>
      </div>
    </div>
  );
};

// Tier Badge
const TierBadge: React.FC<{ tier: string }> = ({ tier }) => {
  const tierConfig: Record<string, { bg: string; text: string }> = {
    Hot: { bg: `${colors.tierHot}26`, text: colors.tierHot },
    Warm: { bg: `${colors.tierWarm}26`, text: colors.tierWarm },
    Cool: { bg: `${colors.tierCool}26`, text: colors.tierCool },
    Cold: { bg: `${colors.tierCold}26`, text: colors.tierCold },
  };
  const config = tierConfig[tier] || tierConfig.Cold;
  
  return (
    <span 
      className="w-12 py-1.5 text-center text-[10px] font-bold uppercase rounded"
      style={{ background: config.bg, color: config.text }}
    >
      {tier}
    </span>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

export const ReportsView: React.FC = () => {
  const [dateRange, setDateRange] = useState<'month' | 'lastMonth' | 'quarter' | 'custom'>('month');
  const data = mockReportData;
  const maxMeetings = Math.max(...data.channels.map(c => c.meetings));
  const maxMonthValue = Math.max(...data.meetingsOverTime.map(m => m.value));

  return (
    <div 
      className="min-h-screen"
      style={{ background: colors.bgVoid }}
    >
      {/* Header */}
      <header 
        className="px-8 py-4 flex items-center justify-between border-b"
        style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
      >
        <div className="flex items-center gap-6">
          <div>
            <h1 className="text-sm font-semibold" style={{ color: colors.textPrimary }}>
              Analytics Terminal
            </h1>
            <p className="text-xs" style={{ color: colors.textMuted }}>
              Multi-Channel Performance Intelligence
            </p>
          </div>
          
          {/* Date Selector */}
          <div 
            className="flex gap-1 p-1 rounded-lg border"
            style={{ background: colors.bgBase, borderColor: colors.borderSubtle }}
          >
            {(['month', 'lastMonth', 'quarter', 'custom'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setDateRange(range)}
                className="px-4 py-2 text-xs font-medium rounded-md transition-all"
                style={{ 
                  background: dateRange === range ? colors.accentPrimary : 'transparent',
                  color: dateRange === range ? '#fff' : colors.textMuted,
                }}
              >
                {range === 'month' ? 'This Month' : 
                 range === 'lastMonth' ? 'Last Month' : 
                 range === 'quarter' ? 'Quarter' : 'Custom'}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex gap-3">
          <button 
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border transition-all hover:bg-opacity-80"
            style={{ 
              background: 'transparent', 
              borderColor: colors.borderDefault,
              color: colors.textSecondary,
            }}
          >
            <Download className="w-4 h-4" /> CSV
          </button>
          <button 
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg transition-all hover:bg-opacity-80"
            style={{ background: colors.accentPrimary, color: '#fff' }}
          >
            <FileText className="w-4 h-4" /> Export PDF
          </button>
        </div>
      </header>

      <div className="p-6 space-y-6">
        {/* Executive Summary */}
        <div className="grid grid-cols-4 gap-4">
          <ExecCard
            label="Meetings Booked"
            value={data.summary.meetingsBooked.value}
            change={data.summary.meetingsBooked.change}
            trend={data.summary.meetingsBooked.trend}
            accentColor={colors.accentPrimary}
          />
          <ExecCard
            label="Pipeline Generated"
            value={`$${Math.floor(data.summary.pipelineGenerated.value / 1000)}`}
            suffix="K"
            change={data.summary.pipelineGenerated.change}
            trend={data.summary.pipelineGenerated.trend}
            accentColor={colors.accentTeal}
          />
          <ExecCard
            label="Show Rate"
            value={data.summary.showRate.value}
            suffix="%"
            change={data.summary.showRate.change}
            trend={data.summary.showRate.trend}
            periodLabel="above benchmark"
            accentColor={colors.accentBlue}
          />
          <ExecCard
            label="Return on Investment"
            value={data.summary.roi.value}
            suffix="x"
            change={data.summary.roi.change}
            trend={data.summary.roi.trend}
            periodLabel="vs last quarter"
            accentColor={colors.statusSuccess}
          />
        </div>

        {/* 5-Channel Performance Matrix */}
        <div 
          className="rounded-xl border overflow-hidden"
          style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
        >
          <div 
            className="px-5 py-4 flex items-center justify-between border-b"
            style={{ borderColor: colors.borderSubtle }}
          >
            <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
              <BarChart3 className="w-4 h-4" style={{ color: colors.accentPrimary }} />
              5-Channel Performance Matrix
            </div>
            <span className="text-xs" style={{ color: colors.textMuted }}>{data.period}</span>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-5 gap-3">
              {data.channels.map((channel) => (
                <ChannelMiniCard key={channel.id} channel={channel} maxMeetings={maxMeetings} />
              ))}
            </div>
          </div>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-2 gap-6">
          {/* Meetings Over Time */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <TrendingUp className="w-4 h-4" style={{ color: colors.accentPrimary }} />
                Meetings Over Time
              </div>
            </div>
            <div className="p-5">
              <div className="flex items-end gap-2 h-52">
                {data.meetingsOverTime.map((month, i) => (
                  <div key={month.month} className="flex-1 flex flex-col items-center h-full">
                    <div className="flex-1 w-full flex items-end justify-center">
                      <div 
                        className="w-4/5 rounded-t transition-all duration-500 hover:brightness-125 group relative"
                        style={{ 
                          height: `${(month.value / maxMonthValue) * 100}%`,
                          background: `linear-gradient(180deg, ${colors.accentPrimary}, ${colors.accentPrimary}80)`,
                        }}
                      >
                        <span 
                          className="absolute -top-6 left-1/2 -translate-x-1/2 text-xs font-semibold font-mono opacity-0 group-hover:opacity-100 transition-opacity"
                          style={{ color: colors.textPrimary }}
                        >
                          {month.value}
                        </span>
                      </div>
                    </div>
                    <div className="text-[11px] font-medium mt-2" style={{ color: colors.textMuted }}>
                      {month.month}
                    </div>
                    <div className="text-xs font-semibold font-mono" style={{ color: colors.textSecondary }}>
                      {month.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Conversion Funnel */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <Target className="w-4 h-4" style={{ color: colors.accentTeal }} />
                Conversion Funnel
              </div>
            </div>
            <div className="p-5 space-y-2">
              {data.funnel.map((stage, i) => (
                <FunnelStage key={stage.stage} {...stage} index={i} />
              ))}
            </div>
          </div>
        </div>

        {/* Key Metrics Row */}
        <div className="grid grid-cols-3 gap-6">
          {/* Response Rates */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <Zap className="w-4 h-4" style={{ color: colors.statusWarning }} />
                Response Rates
              </div>
            </div>
            <div className="p-5">
              <div className="flex justify-around">
                <ProgressRing value={data.responseRates.overall} label="Overall" color={colors.accentPrimary} />
                <ProgressRing value={data.responseRates.sms} label="SMS" color={colors.accentTeal} />
                <ProgressRing value={data.responseRates.voice} label="Voice" color={colors.statusSuccess} />
              </div>
            </div>
          </div>

          {/* What's Working */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <Lightbulb className="w-4 h-4" style={{ color: colors.accentPrimary }} />
                What's Working
              </div>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg p-3" style={{ background: colors.bgBase }}>
                  <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: colors.textMuted }}>
                    Who Converts
                  </div>
                  {data.insights.whoConverts.map((item) => (
                    <div key={item.role} className="flex justify-between items-center py-1.5">
                      <span className="text-xs" style={{ color: colors.textSecondary }}>{item.role}</span>
                      <span className="text-xs font-semibold font-mono" style={{ color: colors.statusSuccess }}>
                        {item.multiplier}x ↑
                      </span>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg p-3" style={{ background: colors.bgBase }}>
                  <div className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: colors.textMuted }}>
                    Best Timing
                  </div>
                  <div className="flex justify-between items-center py-1.5">
                    <span className="text-xs" style={{ color: colors.textSecondary }}>Day</span>
                    <span className="text-xs font-semibold font-mono" style={{ color: colors.statusSuccess }}>
                      {data.insights.bestTiming.day}
                    </span>
                  </div>
                  <div className="flex justify-between items-center py-1.5">
                    <span className="text-xs" style={{ color: colors.textSecondary }}>Hour</span>
                    <span className="text-xs font-semibold font-mono" style={{ color: colors.statusSuccess }}>
                      {data.insights.bestTiming.hour}
                    </span>
                  </div>
                </div>
              </div>
              
              {/* Discovery Banner */}
              <div 
                className="mt-3 p-3.5 rounded-lg border"
                style={{ 
                  background: `linear-gradient(135deg, ${colors.accentPrimary}1A, ${colors.accentBlue}1A)`,
                  borderColor: `${colors.accentPrimary}4D`,
                }}
              >
                <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: colors.accentPrimary }}>
                  <Flame className="w-3.5 h-3.5" /> This Week
                </div>
                <p className="text-xs leading-relaxed" style={{ color: colors.textPrimary }}>
                  {data.insights.discovery}
                </p>
              </div>
            </div>
          </div>

          {/* Lead Sources */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <MapPin className="w-4 h-4" style={{ color: colors.accentBlue }} />
                Lead Sources
              </div>
            </div>
            <div className="p-5 space-y-3">
              {data.leadSources.map((source) => {
                const colorMap: Record<string, string> = {
                  purple: colors.accentPrimary,
                  blue: colors.accentBlue,
                  teal: colors.accentTeal,
                  amber: colors.statusWarning,
                };
                return (
                  <div key={source.name} className="flex items-center gap-3">
                    <div 
                      className="w-8 h-8 rounded-md flex items-center justify-center text-sm"
                      style={{ background: `${colorMap[source.color]}26` }}
                    >
                      {source.name === 'Data Partner' ? '🚀' : 
                       source.name === 'LinkedIn' ? '💼' :
                       source.name === 'Referral' ? '🤝' : '🌐'}
                    </div>
                    <div className="flex-1">
                      <div className="text-xs font-medium" style={{ color: colors.textPrimary }}>
                        {source.name}
                      </div>
                      <div className="h-1 rounded-full mt-1.5" style={{ background: colors.bgBase }}>
                        <div 
                          className="h-full rounded-full transition-all duration-500"
                          style={{ 
                            width: `${source.percentage}%`,
                            background: colorMap[source.color],
                          }}
                        />
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-semibold font-mono" style={{ color: colors.textPrimary }}>
                        {source.count}
                      </div>
                      <div className="text-[11px]" style={{ color: colors.textMuted }}>
                        {source.percentage}%
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-2 gap-6">
          {/* Conversion by Tier */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <Target className="w-4 h-4" style={{ color: colors.accentPrimary }} />
                Conversion Rate by Tier
              </div>
            </div>
            <div className="p-5 space-y-3">
              {data.tierBreakdown.map((tier) => {
                const tierColors: Record<string, string> = {
                  Hot: colors.tierHot,
                  Warm: colors.tierWarm,
                  Cool: colors.tierCool,
                  Cold: colors.tierCold,
                };
                return (
                  <div key={tier.tier} className="flex items-center gap-3">
                    <TierBadge tier={tier.tier} />
                    <div 
                      className="flex-1 h-6 rounded overflow-hidden"
                      style={{ background: colors.bgBase }}
                    >
                      <div 
                        className="h-full rounded flex items-center pl-2.5 transition-all duration-500"
                        style={{ 
                          width: `${tier.width}%`,
                          background: `linear-gradient(90deg, ${tierColors[tier.tier]}4D, ${tierColors[tier.tier]})`,
                        }}
                      >
                        <span className="text-[11px] font-semibold font-mono text-text-primary">
                          {tier.leads} leads
                        </span>
                      </div>
                    </div>
                    <div className="w-20 text-right">
                      <div className="text-sm font-bold font-mono" style={{ color: colors.textPrimary }}>
                        {tier.convRate}%
                      </div>
                      <div className="text-[10px]" style={{ color: colors.textMuted }}>Conv Rate</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Voice AI Performance */}
          <div 
            className="rounded-xl border overflow-hidden"
            style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
          >
            <div 
              className="px-5 py-4 flex items-center justify-between border-b"
              style={{ borderColor: colors.borderSubtle }}
            >
              <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
                <Phone className="w-4 h-4" style={{ color: colors.statusWarning }} />
                Smart Calling Performance
              </div>
              <span className="flex items-center gap-1.5 text-xs font-medium" style={{ color: colors.statusSuccess }}>
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: colors.statusSuccess }} />
                Active
              </span>
            </div>
            <div className="p-5">
              {/* Voice Stats Grid */}
              <div className="grid grid-cols-4 gap-3 mb-4">
                {[
                  { value: data.voicePerformance.callsMade, label: 'Calls Made' },
                  { value: data.voicePerformance.connected, label: 'Connected' },
                  { value: data.voicePerformance.booked, label: 'Booked' },
                  { value: `${data.voicePerformance.bookRate}%`, label: 'Book Rate' },
                ].map((stat) => (
                  <div 
                    key={stat.label}
                    className="text-center p-4 rounded-lg"
                    style={{ background: colors.bgBase }}
                  >
                    <div className="text-2xl font-bold font-mono" style={{ color: colors.textPrimary }}>
                      {stat.value}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider mt-1" style={{ color: colors.textMuted }}>
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Objections */}
              <div className="text-[11px] font-semibold uppercase tracking-wider mb-2.5 flex items-center gap-1.5" style={{ color: colors.textMuted }}>
                <Lightbulb className="w-3.5 h-3.5" /> Objections Handled
              </div>
              <div className="space-y-2">
                {data.voicePerformance.objections.map((obj) => (
                  <div 
                    key={obj.text}
                    className="flex items-center justify-between px-3 py-2.5 rounded-md"
                    style={{ background: colors.bgBase }}
                  >
                    <span className="text-xs" style={{ color: colors.textSecondary }}>{obj.text}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono" style={{ color: colors.textMuted }}>
                        {obj.count} calls
                      </span>
                      <span className="text-xs font-semibold font-mono" style={{ color: colors.statusSuccess }}>
                        {obj.recovery}% recovered
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ROI Summary */}
        <div 
          className="rounded-xl border overflow-hidden"
          style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
        >
          <div 
            className="px-5 py-4 border-b"
            style={{ borderColor: colors.borderSubtle }}
          >
            <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
              💰 ROI Summary — This Period
            </div>
          </div>
          <div className="p-5">
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 rounded-lg" style={{ background: colors.bgBase }}>
                <div className="text-3xl font-extrabold font-mono" style={{ color: colors.statusError }}>
                  ${Math.floor(data.roiSummary.totalSpend / 1000)}K
                </div>
                <div className="text-[11px] uppercase tracking-wider mt-1" style={{ color: colors.textMuted }}>
                  Total Spend
                </div>
              </div>
              <div className="text-center p-4 rounded-lg" style={{ background: colors.bgBase }}>
                <div className="text-3xl font-extrabold font-mono" style={{ color: colors.statusSuccess }}>
                  ${Math.floor(data.roiSummary.pipelineGenerated / 1000)}K
                </div>
                <div className="text-[11px] uppercase tracking-wider mt-1" style={{ color: colors.textMuted }}>
                  Pipeline Generated
                </div>
              </div>
              <div className="text-center p-4 rounded-lg" style={{ background: colors.bgBase }}>
                <div 
                  className="text-3xl font-extrabold font-mono bg-clip-text text-transparent"
                  style={{ backgroundImage: `linear-gradient(135deg, ${colors.accentPrimary}, ${colors.accentBlue})` }}
                >
                  {data.roiSummary.roi}x
                </div>
                <div className="text-[11px] uppercase tracking-wider mt-1" style={{ color: colors.textMuted }}>
                  Return on Investment
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Detailed Channel Table */}
        <div 
          className="rounded-xl border overflow-hidden"
          style={{ background: colors.bgSurface, borderColor: colors.borderSubtle }}
        >
          <div 
            className="px-5 py-4 border-b"
            style={{ borderColor: colors.borderSubtle }}
          >
            <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: colors.textPrimary }}>
              <FileText className="w-4 h-4" /> Detailed Channel Breakdown
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr style={{ background: colors.bgBase }}>
                  {['Channel', 'Volume', 'Delivered', 'Engaged', 'Replied', 'Reply Rate', 'Meetings'].map((header, i) => (
                    <th 
                      key={header}
                      className={`px-4 py-3 text-[10px] font-semibold uppercase tracking-wider border-b ${i === 6 ? 'text-right' : 'text-left'}`}
                      style={{ color: colors.textMuted, borderColor: colors.borderSubtle }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.channels.map((channel) => {
                  const colorMap: Record<string, string> = {
                    purple: colors.accentPrimary,
                    blue: colors.accentBlue,
                    teal: colors.accentTeal,
                    amber: colors.statusWarning,
                    pink: colors.accentPink,
                  };
                  return (
                    <tr 
                      key={channel.id}
                      className="transition-colors hover:bg-opacity-50"
                      style={{ '--hover-bg': colors.bgSurfaceHover } as React.CSSProperties}
                      onMouseEnter={(e) => e.currentTarget.style.background = colors.bgSurfaceHover}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <td className="px-4 py-3.5 border-b" style={{ borderColor: colors.borderSubtle }}>
                        <div className="flex items-center gap-3">
                          <div 
                            className="w-9 h-9 rounded-lg flex items-center justify-center"
                            style={{ background: `${colorMap[channel.color]}26` }}
                          >
                            <ChannelIcon channel={channel.icon} className="w-4 h-4" style={{ color: colorMap[channel.color] } as React.CSSProperties} />
                          </div>
                          <span className="font-semibold text-sm" style={{ color: colors.textPrimary }}>
                            {channel.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 font-mono text-sm border-b" style={{ color: colors.textSecondary, borderColor: colors.borderSubtle }}>
                        {channel.volume.toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-sm border-b" style={{ color: colors.textSecondary, borderColor: colors.borderSubtle }}>
                        {channel.delivered.toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-sm border-b" style={{ color: colors.textSecondary, borderColor: colors.borderSubtle }}>
                        {channel.engaged.toLocaleString()}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-sm border-b" style={{ color: colors.textSecondary, borderColor: colors.borderSubtle }}>
                        {channel.replied}
                      </td>
                      <td className="px-4 py-3.5 font-mono text-sm font-semibold border-b" style={{ color: colors.statusSuccess, borderColor: colors.borderSubtle }}>
                        {channel.replyRate}%
                      </td>
                      <td className="px-4 py-3.5 font-mono text-base font-bold text-right border-b" style={{ color: colors.accentPrimary, borderColor: colors.borderSubtle }}>
                        {channel.meetings}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportsView;
