"use client"

import { Search, Filter, Download, Mail, Linkedin, MessageSquare, Phone } from "lucide-react"
import { leadsData } from "@/data/demo"

const tierColors = {
  hot: "bg-red-100 text-red-800 border-red-200",
  warm: "bg-orange-100 text-orange-800 border-orange-200",
  cool: "bg-mint-100 text-mint-800 border-mint-200",
  cold: "bg-gray-100 text-gray-600 border-gray-200",
}

const channelIcons = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  phone: Phone,
}

export default function LeadsPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Leads</h1>
            <p className="text-gray-500 text-sm mt-1">Manage and track your prospects</p>
          </div>
          <div className="flex items-center gap-3">
            <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </button>
            <button className="px-4 py-2 text-sm font-medium text-white bg-mint-500 rounded-lg hover:bg-mint-600 transition-colors">
              + Add Lead
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search leads..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent"
            />
          </div>
          <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <div className="flex items-center gap-2 border border-gray-300 rounded-lg p-1">
            <button className="px-3 py-1 text-sm font-medium bg-mint-100 text-mint-700 rounded">All</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded">Hot</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded">Warm</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded">Cool</button>
          </div>
        </div>
      </header>

      {/* Table */}
      <div className="p-8">
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  <input type="checkbox" className="rounded border-gray-300" />
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Lead
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Company
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Tier
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Channel
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Last Activity
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {leadsData.map((lead) => {
                const ChannelIcon = channelIcons[lead.channel as keyof typeof channelIcons]
                return (
                  <tr key={lead.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <input type="checkbox" className="rounded border-gray-300" />
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-mint-500 to-mint-600 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                          {lead.name.split(" ").map(n => n[0]).join("")}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{lead.name}</p>
                          <p className="text-sm text-gray-500">{lead.title}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-gray-900">{lead.company}</p>
                      <p className="text-sm text-gray-500">{lead.email}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-lg font-bold text-gray-900">{lead.score}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold border ${tierColors[lead.tier as keyof typeof tierColors]}`}>
                        {lead.tier.charAt(0).toUpperCase() + lead.tier.slice(1)}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <ChannelIcon className="w-4 h-4 text-gray-500" />
                        <span className="text-sm text-gray-600 capitalize">{lead.channel}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {lead.lastActivity}
                    </td>
                    <td className="px-6 py-4">
                      <button className="text-sm text-mint-600 font-medium hover:underline">
                        View →
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-gray-500">Showing 1-8 of 247 leads</p>
          <div className="flex items-center gap-2">
            <button className="px-3 py-1 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50">
              Previous
            </button>
            <button className="px-3 py-1 text-sm font-medium text-white bg-mint-500 rounded">1</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50">2</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50">3</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50">
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
