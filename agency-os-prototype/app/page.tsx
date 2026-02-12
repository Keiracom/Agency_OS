"use client"

import { TrendingUp, X, Flame, Calendar, Bell, Settings } from "lucide-react"
import { NumberTicker } from "@/components/ui/number-ticker"
import { dashboardData } from "@/data/demo"

export default function DashboardPage() {
  const data = dashboardData

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-4">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-500">Friday, January 31, 2026</span>
          <div className="flex items-center gap-3">
            <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
              <Bell className="w-5 h-5" />
            </button>
            <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Dashboard Content */}
      <div className="p-8 max-w-6xl">
        {/* Greeting */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">{data.greeting}</h1>
          <p className="text-gray-500 mt-1">{data.subtext}</p>
        </div>

        {/* Celebration Banner */}
        {data.celebration.show && (
          <div className="mb-6">
            <div className="celebration-glow bg-gradient-to-r from-mint-500 to-mint-600 rounded-2xl p-5 flex items-center gap-4 text-white">
              <div className="text-3xl">🎉</div>
              <div className="flex-1">
                <p className="text-lg font-semibold">{data.celebration.title}</p>
                <p className="text-sm text-mint-100">{data.celebration.subtitle}</p>
              </div>
              <button className="p-2 rounded-full hover:bg-white/10 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* Hero Card: Meetings vs Goal */}
        <div className="mb-6">
          <div className="shine-border bg-white rounded-2xl p-8 shadow-sm">
            <div className="flex items-center gap-12">
              {/* Main Metric */}
              <div className="flex-1">
                <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Meetings This Month
                </p>
                <p className="text-7xl font-extrabold text-gray-900 leading-none">
                  <NumberTicker value={data.meetingsGoal.current} delay={0.2} />
                </p>
                <p className="text-lg text-gray-500 mt-2">
                  Goal: {data.meetingsGoal.target} •{" "}
                  <span className="text-mint-500 font-semibold">
                    {data.meetingsGoal.targetHit
                      ? `Target hit ${data.meetingsGoal.daysEarly} days early ✓`
                      : `${data.meetingsGoal.target - data.meetingsGoal.current} to go`}
                  </span>
                </p>

                {/* Momentum */}
                <div className="flex items-center gap-3 mt-5 pt-5 border-t border-gray-100">
                  <TrendingUp className="w-6 h-6 text-mint-500" />
                  <p className="text-sm text-gray-500">
                    <span className="font-semibold text-mint-500">
                      ↑ {data.momentum.percentChange}% vs last month
                    </span>{" "}
                    • {data.momentum.label}
                  </p>
                </div>
              </div>

              {/* Gauge */}
              <div className="w-[200px]">
                <svg viewBox="0 0 200 120" width="200" height="120">
                  <defs>
                    <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#0eb77a" />
                      <stop offset="50%" stopColor="#2dd498" />
                      <stop offset="100%" stopColor="#5eebb8" />
                    </linearGradient>
                  </defs>
                  <path
                    d="M 20 100 A 80 80 0 0 1 180 100"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="20"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 20 100 A 80 80 0 0 1 180 100"
                    fill="none"
                    stroke="url(#gaugeGradient)"
                    strokeWidth="20"
                    strokeLinecap="round"
                    strokeDasharray="251.2"
                    strokeDashoffset="0"
                    style={{ transition: "stroke-dashoffset 1s ease-out" }}
                  />
                </svg>
                <div className="text-center mt-3">
                  <p className="text-base font-bold text-mint-500">
                    {data.meetingsGoal.percentComplete}% — Target Exceeded!
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {data.quickStats.map((stat, index) => (
            <div
              key={index}
              className="card-hover mint-hover-overlay bg-white rounded-xl p-5 text-center border border-gray-100"
            >
              <p className="text-3xl font-extrabold text-gray-900">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-1 uppercase tracking-wide font-medium">
                {stat.label}
              </p>
              <p
                className={`text-xs font-medium mt-2 ${
                  stat.changeDirection === "up"
                    ? "text-mint-500"
                    : "text-gray-400"
                }`}
              >
                {stat.change}
              </p>
            </div>
          ))}
        </div>

        {/* Two Column Grid: Hot Prospects + Week Ahead */}
        <div className="grid gap-6 lg:grid-cols-2 mb-6">
          {/* Hot Prospects */}
          <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-orange-500" />
                <h3 className="font-semibold">Hot Right Now</h3>
              </div>
              <a
                href="/leads"
                className="text-sm text-mint-600 font-medium hover:underline"
              >
                View all →
              </a>
            </div>
            <div className="divide-y divide-gray-50">
              {data.hotProspects.map((prospect) => (
                <a
                  key={prospect.id}
                  href={`/leads/${prospect.id}`}
                  className={`flex items-center gap-4 p-4 hover:shadow-md transition-shadow ${
                    prospect.isVeryHot
                      ? "bg-red-50 border-l-4 border-l-red-500"
                      : "bg-orange-50 border-l-4 border-l-orange-500"
                  }`}
                >
                  <div className="w-11 h-11 bg-gradient-to-br from-mint-500 to-mint-600 rounded-full flex items-center justify-center text-white font-bold">
                    {prospect.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 truncate">{prospect.name}</p>
                    <p className="text-sm text-gray-500 truncate">
                      {prospect.company} • {prospect.title}
                    </p>
                    <p
                      className={`text-xs font-medium mt-1 ${
                        prospect.isVeryHot ? "text-red-600" : "text-orange-600"
                      }`}
                    >
                      {prospect.signal}
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className={`text-xl font-extrabold ${
                        prospect.isVeryHot ? "text-red-500" : "text-orange-500"
                      }`}
                    >
                      {prospect.score}
                    </p>
                    <p className="text-[10px] text-gray-500 uppercase">Score</p>
                  </div>
                </a>
              ))}
            </div>
          </div>

          {/* Week Ahead */}
          <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-mint-600" />
                <h3 className="font-semibold">Week Ahead</h3>
              </div>
              <span className="text-sm text-gray-500">{data.weekAhead.length} meetings</span>
            </div>
            <div className="divide-y divide-gray-50">
              {data.weekAhead.map((meeting) => (
                <div key={meeting.id} className="p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`text-xs font-semibold uppercase ${
                        meeting.isToday ? "text-mint-600" : "text-gray-500"
                      }`}
                    >
                      {meeting.time}
                    </span>
                    {meeting.dealValue && (
                      <span className="text-xs bg-mint-100 text-mint-700 px-2 py-0.5 rounded-full font-medium">
                        {meeting.dealValue} deal
                      </span>
                    )}
                  </div>
                  <p className="font-medium text-gray-900">{meeting.title}</p>
                  <p className="text-sm text-gray-500">
                    {meeting.contact} • {meeting.company}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Two Column Grid: Insight + Warm Replies */}
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Insight Card */}
          <div className="bg-gradient-to-br from-mint-50 to-mint-100/50 rounded-xl p-6 border border-mint-200">
            <div className="text-4xl mb-4">{data.insight.icon}</div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">{data.insight.headline}</h3>
            <p className="text-sm text-gray-600 leading-relaxed">{data.insight.detail}</p>
          </div>

          {/* Warm Replies */}
          <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="live-pulse absolute inline-flex h-full w-full rounded-full bg-mint-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-mint-500" />
                </span>
                <h3 className="font-semibold">Warm Replies</h3>
              </div>
              <a href="/replies" className="text-sm text-mint-600 font-medium hover:underline">
                View inbox →
              </a>
            </div>
            <div className="divide-y divide-gray-50">
              {data.warmReplies.map((reply) => (
                <a key={reply.id} href={`/replies/${reply.id}`} className="block p-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-mint-500 to-mint-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                      {reply.initials}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-gray-900 truncate">{reply.name}</p>
                      <p className="text-xs text-gray-500">{reply.company}</p>
                    </div>
                    <span className="text-xs text-gray-400">{reply.time}</span>
                  </div>
                  <p className="text-sm text-gray-600 line-clamp-2">"{reply.preview}"</p>
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
