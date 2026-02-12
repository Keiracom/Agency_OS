"use client"

import { Search, Filter, Mail, Linkedin, Archive, Star, Trash2 } from "lucide-react"
import { repliesData } from "@/data/demo"

const sentimentColors = {
  positive: "border-l-green-500",
  negative: "border-l-red-500",
  neutral: "border-l-gray-400",
}

const channelIcons = {
  email: Mail,
  linkedin: Linkedin,
}

export default function RepliesPage() {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar - Reply List */}
      <div className="w-96 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-xl font-bold mb-4">Inbox</h1>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search replies..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-2 mt-3">
            <button className="px-3 py-1 text-sm font-medium bg-mint-100 text-mint-700 rounded-lg">All</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg">Unread</button>
            <button className="px-3 py-1 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-lg">Positive</button>
          </div>
        </div>

        {/* Reply List */}
        <div className="flex-1 overflow-auto">
          {repliesData.map((reply, index) => {
            const ChannelIcon = channelIcons[reply.channel as keyof typeof channelIcons]
            return (
              <div
                key={reply.id}
                className={`p-4 border-b border-gray-100 cursor-pointer hover:bg-gray-50 transition-colors border-l-4 ${
                  sentimentColors[reply.sentiment as keyof typeof sentimentColors]
                } ${index === 0 ? "bg-mint-50" : ""}`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-gradient-to-br from-mint-500 to-mint-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                    {reply.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className={`font-medium text-sm truncate ${reply.isUnread ? "text-gray-900" : "text-gray-600"}`}>
                        {reply.name}
                      </p>
                      {reply.isUnread && (
                        <span className="w-2 h-2 bg-mint-500 rounded-full" />
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{reply.company}</p>
                  </div>
                  <div className="flex items-center gap-1">
                    <ChannelIcon className="w-3 h-3 text-gray-400" />
                    <span className="text-xs text-gray-400">{reply.time}</span>
                  </div>
                </div>
                <p className={`text-sm truncate ${reply.isUnread ? "font-medium text-gray-900" : "text-gray-600"}`}>
                  {reply.subject}
                </p>
                <p className="text-sm text-gray-500 truncate mt-1">{reply.preview}</p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Main Content - Email Preview */}
      <div className="flex-1 flex flex-col">
        {/* Email Header */}
        <div className="bg-white border-b border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-mint-500 to-mint-600 rounded-full flex items-center justify-center text-white font-bold">
                DP
              </div>
              <div>
                <h2 className="font-semibold text-lg">David Park</h2>
                <p className="text-sm text-gray-500">david@momentummedia.com.au • Momentum Media</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors" title="Star">
                <Star className="w-5 h-5" />
              </button>
              <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors" title="Archive">
                <Archive className="w-5 h-5" />
              </button>
              <button className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg transition-colors" title="Delete">
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>
          <h3 className="text-xl font-medium">Re: Quick question about your agency</h3>
          <p className="text-sm text-gray-500 mt-1">2 hours ago via Email</p>
        </div>

        {/* Email Body */}
        <div className="flex-1 p-8 overflow-auto">
          <div className="max-w-2xl">
            <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
              <p className="text-gray-700 leading-relaxed">
                Hi there,
              </p>
              <p className="text-gray-700 leading-relaxed mt-4">
                Yes, I'd be interested in learning more. Can we schedule a call next week? 
                I'm particularly interested in understanding how your multi-channel approach 
                works and what kind of results you've seen for agencies similar to ours.
              </p>
              <p className="text-gray-700 leading-relaxed mt-4">
                We're currently doing about $40K MRR and looking to scale to $100K by end of year. 
                Would love to see if Agency OS could help accelerate that.
              </p>
              <p className="text-gray-700 leading-relaxed mt-4">
                Best,<br />
                David
              </p>
            </div>

            {/* Quick Actions */}
            <div className="bg-mint-50 rounded-xl border border-mint-200 p-4">
              <p className="text-sm font-medium text-mint-800 mb-3">Quick Actions</p>
              <div className="flex flex-wrap gap-2">
                <button className="px-4 py-2 text-sm font-medium text-white bg-mint-500 rounded-lg hover:bg-mint-600 transition-colors">
                  Schedule Meeting
                </button>
                <button className="px-4 py-2 text-sm font-medium text-mint-700 bg-white border border-mint-300 rounded-lg hover:bg-mint-50 transition-colors">
                  Reply Now
                </button>
                <button className="px-4 py-2 text-sm font-medium text-mint-700 bg-white border border-mint-300 rounded-lg hover:bg-mint-50 transition-colors">
                  Mark as Hot Lead
                </button>
                <button className="px-4 py-2 text-sm font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
                  Add Note
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Reply Box */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="max-w-2xl mx-auto">
            <textarea
              placeholder="Write a reply..."
              className="w-full p-4 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-mint-500 focus:border-transparent"
              rows={3}
            />
            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-2 text-sm text-gray-500">
                <span>Replying as: dave@example.com</span>
              </div>
              <button className="px-6 py-2 text-sm font-medium text-white bg-mint-500 rounded-lg hover:bg-mint-600 transition-colors">
                Send Reply
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
