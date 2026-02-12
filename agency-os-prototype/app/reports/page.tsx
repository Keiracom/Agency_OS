"use client"

import { TrendingUp, TrendingDown, Calendar, Download, Mail, Linkedin, MessageSquare, Phone } from "lucide-react"
import { NumberTicker } from "@/components/ui/number-ticker"

const monthlyData = [
  { month: "Aug", meetings: 6, pipeline: 28 },
  { month: "Sep", meetings: 8, pipeline: 35 },
  { month: "Oct", meetings: 7, pipeline: 31 },
  { month: "Nov", meetings: 10, pipeline: 42 },
  { month: "Dec", meetings: 9, pipeline: 38 },
  { month: "Jan", meetings: 12, pipeline: 47 },
]

const channelStats = [
  { channel: "Email", icon: Mail, sent: 3420, opened: 1245, replied: 156, meetings: 18, color: "mint" },
  { channel: "LinkedIn", icon: Linkedin, sent: 890, opened: 456, replied: 67, meetings: 8, color: "sky" },
  { channel: "SMS", icon: MessageSquare, sent: 520, opened: 478, replied: 34, meetings: 4, color: "green" },
  { channel: "Voice AI", icon: Phone, sent: 180, opened: 180, replied: 42, meetings: 5, color: "purple" },
]

export default function ReportsPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Reports</h1>
            <p className="text-gray-500 text-sm mt-1">Analytics and performance insights</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 border border-gray-300 rounded-lg px-3 py-2">
              <Calendar className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-700">Last 6 months</span>
            </div>
            <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </header>

      <div className="p-8">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <p className="text-sm text-gray-500 uppercase tracking-wide font-medium mb-2">Total Meetings</p>
            <p className="text-4xl font-extrabold text-gray-900">
              <NumberTicker value={52} delay={0.1} />
            </p>
            <p className="text-sm text-mint-500 font-medium mt-2 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" /> +23% vs prev period
            </p>
          </div>
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <p className="text-sm text-gray-500 uppercase tracking-wide font-medium mb-2">Pipeline Generated</p>
            <p className="text-4xl font-extrabold text-gray-900">
              $<NumberTicker value={221} delay={0.2} />K
            </p>
            <p className="text-sm text-mint-500 font-medium mt-2 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" /> +31% vs prev period
            </p>
          </div>
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <p className="text-sm text-gray-500 uppercase tracking-wide font-medium mb-2">Avg Reply Rate</p>
            <p className="text-4xl font-extrabold text-gray-900">
              <NumberTicker value={5.8} delay={0.3} decimalPlaces={1} />%
            </p>
            <p className="text-sm text-mint-500 font-medium mt-2 flex items-center gap-1">
              <TrendingUp className="w-4 h-4" /> +0.8% vs prev period
            </p>
          </div>
          <div className="bg-white rounded-xl p-6 border border-gray-200">
            <p className="text-sm text-gray-500 uppercase tracking-wide font-medium mb-2">Cost per Meeting</p>
            <p className="text-4xl font-extrabold text-gray-900">
              $<NumberTicker value={127} delay={0.4} />
            </p>
            <p className="text-sm text-mint-500 font-medium mt-2 flex items-center gap-1">
              <TrendingDown className="w-4 h-4" /> -12% vs prev period
            </p>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid gap-6 lg:grid-cols-2 mb-8">
          {/* Meetings Trend */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-lg mb-6">Meetings Over Time</h3>
            <div className="flex items-end gap-4 h-48">
              {monthlyData.map((data, index) => (
                <div key={data.month} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full bg-gradient-to-t from-mint-500 to-mint-400 rounded-t-lg transition-all duration-500"
                    style={{
                      height: `${(data.meetings / 12) * 100}%`,
                      animationDelay: `${index * 100}ms`,
                    }}
                  />
                  <p className="text-xs text-gray-500 mt-2">{data.month}</p>
                  <p className="text-sm font-semibold text-gray-900">{data.meetings}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline Trend */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="font-semibold text-lg mb-6">Pipeline Value ($K)</h3>
            <div className="flex items-end gap-4 h-48">
              {monthlyData.map((data, index) => (
                <div key={data.month} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full bg-gradient-to-t from-mint-600 to-mint-500 rounded-t-lg transition-all duration-500"
                    style={{
                      height: `${(data.pipeline / 50) * 100}%`,
                      animationDelay: `${index * 100}ms`,
                    }}
                  />
                  <p className="text-xs text-gray-500 mt-2">{data.month}</p>
                  <p className="text-sm font-semibold text-gray-900">${data.pipeline}K</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Channel Performance */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="font-semibold text-lg">Channel Performance</h3>
          </div>
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Channel</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Sent</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Opened</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Replied</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reply Rate</th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Meetings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {channelStats.map((channel) => (
                <tr key={channel.channel} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl bg-${channel.color}-100 flex items-center justify-center`}>
                        <channel.icon className={`w-5 h-5 text-${channel.color}-600`} />
                      </div>
                      <span className="font-medium text-gray-900">{channel.channel}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-900">{channel.sent.toLocaleString()}</td>
                  <td className="px-6 py-4 text-gray-900">{channel.opened.toLocaleString()}</td>
                  <td className="px-6 py-4 text-gray-900">{channel.replied}</td>
                  <td className="px-6 py-4">
                    <span className="text-mint-600 font-semibold">
                      {((channel.replied / channel.sent) * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-lg font-bold text-mint-600">{channel.meetings}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
