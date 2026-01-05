"use client";

/**
 * FILE: frontend/components/landing/DashboardDemo.tsx
 * PURPOSE: Animated dashboard demo - fixed colors and reduced animation jitter
 * FEATURES: Static stats, smooth activity feed, smooth typing
 */

import { useState, useEffect, useRef, useMemo } from "react";
import { Mail, Linkedin, MessageSquare, Phone, Calendar, Lock, TrendingUp } from "lucide-react";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip } from "recharts";

// Activity feed data
const activities = [
  { name: "Sarah Chen", company: "Bloom Digital", action: "Opened email", channel: "email" as const },
  { name: "Michael Jones", company: "Growth Labs", action: "Clicked link", channel: "email" as const },
  { name: "Lisa Wong", company: "Pixel Perfect", action: "Accepted connection", channel: "linkedin" as const },
  { name: "David Park", company: "Momentum Media", action: "Replied to SMS", channel: "sms" as const },
  { name: "Emma Wilson", company: "Digital First", action: "Answered call", channel: "phone" as const },
  { name: "James Liu", company: "Scale Agency", action: "Booked meeting", channel: "calendar" as const },
  { name: "Anna Smith", company: "Brand Forward", action: "Opened email", channel: "email" as const },
  { name: "Tom Brown", company: "Creative Co", action: "Viewed profile", channel: "linkedin" as const },
];

const channelIcons = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  phone: Phone,
  calendar: Calendar,
};

const channelStyles = {
  email: { icon: "text-blue-400", bg: "bg-blue-500/20" },
  linkedin: { icon: "text-sky-400", bg: "bg-sky-500/20" },
  sms: { icon: "text-green-400", bg: "bg-green-500/20" },
  phone: { icon: "text-purple-400", bg: "bg-purple-500/20" },
  calendar: { icon: "text-emerald-400", bg: "bg-emerald-500/20" },
};

// Pipeline growth data - 6 months showing upward trend to $284K
const pipelineData = [
  { month: "Aug", value: 142 },
  { month: "Sep", value: 168 },
  { month: "Oct", value: 195 },
  { month: "Nov", value: 221 },
  { month: "Dec", value: 256 },
  { month: "Jan", value: 284 },
];

interface DashboardDemoProps {
  className?: string;
}

export default function DashboardDemo({ className = "" }: DashboardDemoProps) {
  const [visibleActivities, setVisibleActivities] = useState(() => activities.slice(0, 5));
  const activityIndexRef = useRef(5);

  // Pre-compute time ago values to avoid re-renders
  const timeAgoValues = useMemo(() => [2, 5, 12, 18, 31], []);

  // Rotate activity feed - using ref to avoid re-renders
  useEffect(() => {
    const interval = setInterval(() => {
      const nextIdx = activityIndexRef.current % activities.length;
      const newActivity = activities[nextIdx];
      activityIndexRef.current += 1;

      setVisibleActivities((current) => [newActivity, ...current.slice(0, 4)]);
    }, 4000); // Slower rotation

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={`rounded-2xl overflow-hidden border border-white/10 bg-[#12121a] shadow-2xl ${className}`}>
      {/* Browser Chrome */}
      <div className="flex items-center gap-2 px-4 py-3 bg-[#1a1a24] border-b border-white/10">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
          <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
          <div className="w-3 h-3 rounded-full bg-[#28c840]" />
        </div>
        <div className="flex-1 flex justify-center">
          <div className="px-4 py-1.5 rounded-lg bg-[#0a0a0f] text-white/60 text-xs flex items-center gap-2">
            <Lock className="w-3 h-3 text-green-500" />
            app.agencyos.com.au
          </div>
        </div>
      </div>

      {/* Dashboard Content */}
      <div className="p-6 md:p-8 bg-[#0a0a0f]">
        {/* Stats Row - Static values for stability */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/60 text-xs uppercase tracking-wider">Pipeline</span>
              <span className="text-xs text-emerald-400">↑ 12%</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold text-white">$284K</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/60 text-xs uppercase tracking-wider">Meetings</span>
              <span className="text-xs text-emerald-400">↑ 8 this week</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold text-white">47</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/60 text-xs uppercase tracking-wider">Reply Rate</span>
              <span className="text-xs text-emerald-400">↑ 2.1%</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold text-white">12%</p>
          </div>
          <div className="p-4 rounded-xl bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/60 text-xs uppercase tracking-wider">Leads</span>
              <span className="text-xs text-blue-400">Active</span>
            </div>
            <p className="text-2xl md:text-3xl font-bold text-white">2,847</p>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Live Activity Feed */}
          <div className="rounded-xl bg-white/5 border border-white/10 overflow-hidden">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                Live Activity
              </h3>
              <span className="text-xs text-white/50">Auto-updating</span>
            </div>
            <div className="divide-y divide-white/5">
              {visibleActivities.map((activity, idx) => {
                const Icon = channelIcons[activity.channel];
                const style = channelStyles[activity.channel];
                return (
                  <div
                    key={`${activity.name}-${idx}-${activityIndexRef.current}`}
                    className="px-4 py-3 flex items-center gap-3 transition-opacity duration-500"
                    style={{ opacity: idx === 0 ? 1 : 1 }}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${style.bg}`}>
                      <Icon className={`w-4 h-4 ${style.icon}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{activity.name}</p>
                      <p className="text-xs text-white/50">{activity.action}</p>
                    </div>
                    <span className="text-xs text-white/40">{timeAgoValues[idx]}s ago</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Pipeline Growth Chart */}
          <div className="rounded-xl bg-white/5 border border-white/10 overflow-hidden">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <h3 className="font-semibold text-sm text-white flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                Pipeline Growth
              </h3>
              <span className="text-xs px-2 py-1 rounded-full bg-emerald-500/20 text-emerald-300">
                +100% YoY
              </span>
            </div>
            <div className="p-4">
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={pipelineData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
                    <defs>
                      <linearGradient id="pipelineGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity={0.8} />
                        <stop offset="100%" stopColor="#22c55e" stopOpacity={0.2} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="month"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }}
                      tickFormatter={(value) => `$${value}K`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a24',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: '8px',
                        color: '#fff',
                        fontSize: '12px',
                      }}
                      formatter={(value: number) => [`$${value}K`, 'Pipeline']}
                      labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#22c55e"
                      strokeWidth={3}
                      dot={{ fill: '#22c55e', strokeWidth: 0, r: 4 }}
                      activeDot={{ fill: '#22c55e', strokeWidth: 2, stroke: '#fff', r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* ALS Score Distribution */}
        <div className="mt-6 rounded-xl bg-white/5 border border-white/10 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-sm text-white">Lead Quality Distribution</h3>
            <span className="text-xs text-white/50">Agency Lead Score (ALS)</span>
          </div>
          <div className="grid grid-cols-5 gap-3">
            {[
              { label: "Hot", value: 24, color: "bg-red-500", textColor: "text-red-400" },
              { label: "Warm", value: 31, color: "bg-orange-500", textColor: "text-orange-400" },
              { label: "Cool", value: 28, color: "bg-blue-500", textColor: "text-blue-400" },
              { label: "Cold", value: 12, color: "bg-gray-500", textColor: "text-gray-400" },
              { label: "Dead", value: 5, color: "bg-gray-700", textColor: "text-gray-500" },
            ].map((tier) => (
              <div key={tier.label}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className={`font-medium ${tier.textColor}`}>{tier.label}</span>
                  <span className="text-white/60">{tier.value}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
                  <div
                    className={`h-full ${tier.color} rounded-full`}
                    style={{ width: `${tier.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
