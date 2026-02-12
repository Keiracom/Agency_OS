"use client"

import { Plus, Mail, Linkedin, MessageSquare, Phone, Play, Pause, MoreHorizontal } from "lucide-react"
import { campaignsData } from "@/data/demo"

const statusColors = {
  active: "bg-green-100 text-green-800 border-green-200",
  paused: "bg-yellow-100 text-yellow-800 border-yellow-200",
  completed: "bg-mint-100 text-mint-800 border-mint-200",
  draft: "bg-gray-100 text-gray-600 border-gray-200",
}

const channelIcons = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  voice: Phone,
}

export default function CampaignsPage() {
  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-8 py-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Campaigns</h1>
            <p className="text-gray-500 text-sm mt-1">Manage your outreach campaigns</p>
          </div>
          <button className="px-4 py-2 text-sm font-medium text-white bg-mint-500 rounded-lg hover:bg-mint-600 transition-colors flex items-center gap-2">
            <Plus className="w-4 h-4" />
            New Campaign
          </button>
        </div>
      </header>

      {/* Campaign Cards */}
      <div className="p-8">
        <div className="grid gap-6 md:grid-cols-2">
          {campaignsData.map((campaign) => (
            <div
              key={campaign.id}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden card-hover"
            >
              {/* Card Header */}
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold text-lg">{campaign.name}</h3>
                  <span
                    className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
                      statusColors[campaign.status as keyof typeof statusColors]
                    }`}
                  >
                    {campaign.status.charAt(0).toUpperCase() + campaign.status.slice(1)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {campaign.status === "active" ? (
                    <button className="p-2 text-yellow-600 hover:bg-yellow-50 rounded-lg transition-colors">
                      <Pause className="w-4 h-4" />
                    </button>
                  ) : campaign.status === "paused" ? (
                    <button className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors">
                      <Play className="w-4 h-4" />
                    </button>
                  ) : null}
                  <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors">
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Channels */}
              <div className="px-6 py-3 border-b border-gray-100 flex items-center gap-2">
                <span className="text-xs text-gray-500 uppercase tracking-wide font-medium">Channels:</span>
                <div className="flex items-center gap-2">
                  {campaign.channels.map((channel) => {
                    const Icon = channelIcons[channel as keyof typeof channelIcons]
                    return (
                      <div
                        key={channel}
                        className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center"
                        title={channel}
                      >
                        <Icon className="w-4 h-4 text-gray-600" />
                      </div>
                    )
                  })}
                </div>
                <span className="ml-auto text-xs text-gray-400">Started {campaign.startDate}</span>
              </div>

              {/* Stats */}
              <div className="px-6 py-4 grid grid-cols-4 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">{campaign.sent.toLocaleString()}</p>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Sent</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">{campaign.opened.toLocaleString()}</p>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Opened</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">{campaign.replied}</p>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Replied</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-mint-600">{campaign.meetings}</p>
                  <p className="text-xs text-gray-500 uppercase tracking-wide">Meetings</p>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="px-6 pb-4">
                <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                  <span>Reply Rate</span>
                  <span>{((campaign.replied / campaign.sent) * 100).toFixed(1)}%</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-mint-400 to-mint-500 rounded-full"
                    style={{ width: `${(campaign.replied / campaign.sent) * 100}%` }}
                  />
                </div>
              </div>

              {/* Card Footer */}
              <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
                <a href={`/campaigns/${campaign.id}`} className="text-sm text-mint-600 font-medium hover:underline">
                  View Details →
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
