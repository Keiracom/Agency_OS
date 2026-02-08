/**
 * RepliesContent.tsx - Replies Page Content
 * Phase: Operation Modular Cockpit
 * Uses intent classification per REPLY_HANDLING.md
 */

"use client";

import { useState } from "react";
import {
  Mail,
  Linkedin,
  MessageCircle,
  CheckCircle,
  Calendar,
  Clock,
  Send,
  Sparkles,
} from "lucide-react";
import { ChannelIcon, TierBadge } from "@/components/dashboard";
import { useReplies } from "@/hooks/use-replies";

interface RepliesContentProps {
  campaignId?: string | null;
}

// Intent configuration per REPLY_HANDLING.md
const intentConfig: Record<string, { label: string; style: string }> = {
  meeting_interest: { label: "Meeting Interest", style: "bg-emerald-100 text-emerald-700" },
  question: { label: "Question", style: "bg-blue-100 text-blue-700" },
  positive_engagement: { label: "Positive", style: "bg-sky-100 text-sky-700" },
  not_interested: { label: "Not Interested", style: "bg-orange-100 text-orange-700" },
  out_of_office: { label: "Out of Office", style: "bg-slate-100 text-slate-600" },
  wrong_person: { label: "Wrong Person", style: "bg-amber-100 text-amber-700" },
  referral: { label: "Referral", style: "bg-purple-100 text-purple-700" },
  angry_or_complaint: { label: "Complaint", style: "bg-red-100 text-red-700" },
};

export function RepliesContent({ campaignId }: RepliesContentProps) {
  const [selectedReplyId, setSelectedReplyId] = useState<string | null>(null);
  const [channelFilter, setChannelFilter] = useState<string | null>(null);
  const [showHandled, setShowHandled] = useState(false);

  const { data: repliesData, isLoading } = useReplies({
    campaign_id: campaignId ?? undefined,
    handled: showHandled ? undefined : false,
  });

  const replies = repliesData?.items ?? [];
  const filteredReplies = channelFilter
    ? replies.filter(r => r.channel === channelFilter)
    : replies;
  const selectedReply = replies.find(r => r.id === selectedReplyId) ?? replies[0];

  const unhandledCount = replies.filter(r => !r.handled).length;

  return (
    <div className="p-6 min-h-screen">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Replies</h2>
          <p className="text-sm text-slate-500">{unhandledCount} pending replies requiring attention</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Channel Filter */}
          <div className="flex items-center gap-1 border border-slate-200 rounded-lg p-1">
            {[
              { key: null, label: "All" },
              { key: "email", label: "Email", icon: Mail },
              { key: "linkedin", label: "LinkedIn", icon: Linkedin },
              { key: "sms", label: "SMS", icon: MessageCircle },
            ].map((ch) => (
              <button
                key={ch.key ?? "all"}
                onClick={() => setChannelFilter(ch.key)}
                className={`px-2.5 py-1.5 text-xs font-medium rounded flex items-center gap-1.5 ${
                  channelFilter === ch.key ? "bg-blue-50 text-blue-700" : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                {ch.icon && <ch.icon className="w-3.5 h-3.5" />}
                {ch.label}
              </button>
            ))}
          </div>
          {/* Show Handled Toggle */}
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={showHandled}
              onChange={(e) => setShowHandled(e.target.checked)}
              className="w-4 h-4 rounded border-slate-300"
            />
            Show handled
          </label>
        </div>
      </div>

      {/* Split View */}
      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-180px)]">
        {/* Reply List */}
        <div className="col-span-4 bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden flex flex-col">
          <div className="p-3 border-b border-slate-100 flex items-center gap-2">
            <span className="text-xs text-slate-500">Filter by intent:</span>
            <button className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-lg">Meeting</button>
            <button className="px-2.5 py-1 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-50">Question</button>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
            {isLoading ? (
              <div className="p-4 animate-pulse">
                <div className="h-4 bg-slate-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-slate-200 rounded w-1/2" />
              </div>
            ) : filteredReplies.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                No replies found
              </div>
            ) : (
              filteredReplies.map((reply) => (
                <button
                  key={reply.id}
                  onClick={() => setSelectedReplyId(reply.id)}
                  className={`w-full p-3 text-left hover:bg-slate-50 transition-colors ${
                    selectedReplyId === reply.id ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
                  } ${!reply.handled ? "bg-blue-50/50" : ""}`}
                >
                  <div className="flex items-start gap-3">
                    <ChannelIcon channel={reply.channel} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className={`font-medium text-sm ${!reply.handled ? "text-slate-900" : "text-slate-600"}`}>
                          {reply.lead ? `${reply.lead.first_name ?? ""} ${reply.lead.last_name ?? ""}`.trim() || reply.lead.email : "Unknown"}
                        </span>
                        <div className="flex items-center gap-2">
                          {reply.handled && <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />}
                          <span className="text-xs text-slate-400">
                            {new Date(reply.received_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <p className="text-xs text-slate-600 truncate">{reply.content ?? reply.subject}</p>
                      <div className="flex items-center gap-2 mt-2">
                        {reply.intent && (
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${intentConfig[reply.intent]?.style ?? "bg-slate-100 text-slate-600"}`}>
                            {intentConfig[reply.intent]?.label ?? reply.intent}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Reply Detail */}
        <div className="col-span-8 bg-white rounded-xl border border-slate-200 shadow-lg overflow-hidden flex flex-col">
          {selectedReply ? (
            <>
              <div className="p-4 border-b border-slate-100">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">
                      {selectedReply.lead ? `${selectedReply.lead.first_name ?? ""} ${selectedReply.lead.last_name ?? ""}`.trim() || selectedReply.lead.email : "Unknown"}
                    </h3>
                    <p className="text-sm text-slate-500">{selectedReply.lead?.company ?? "—"}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedReply.intent && (
                      <span className={`px-2 py-1 rounded text-xs font-medium ${intentConfig[selectedReply.intent]?.style ?? "bg-slate-100"}`}>
                        {intentConfig[selectedReply.intent]?.label ?? selectedReply.intent}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex-1 p-4 overflow-y-auto">
                <div className="bg-slate-50 rounded-lg p-4 mb-4">
                  <p className="text-sm text-slate-700 leading-relaxed">
                    {selectedReply.content ?? selectedReply.subject}
                  </p>
                </div>

                {/* AI Suggested Response */}
                <div className="border border-purple-200 bg-purple-50 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Sparkles className="w-4 h-4 text-purple-600" />
                    <span className="text-sm font-medium text-purple-900">AI Suggested Response</span>
                  </div>
                  <p className="text-sm text-purple-800 leading-relaxed mb-3">
                    Hi {selectedReply.lead?.first_name ?? "there"}, thank you for your response! I'd be happy to share more details.
                  </p>
                  <div className="flex items-center gap-2">
                    <button className="px-3 py-1.5 bg-purple-600 text-white text-xs font-medium rounded-lg hover:bg-purple-700">
                      Use This Response
                    </button>
                    <button className="px-3 py-1.5 border border-purple-300 text-purple-700 text-xs font-medium rounded-lg hover:bg-purple-100">
                      Edit
                    </button>
                  </div>
                </div>
              </div>

              <div className="p-4 border-t border-slate-100">
                <textarea
                  placeholder="Type your reply..."
                  className="w-full px-4 py-3 border border-slate-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                />
                <div className="flex items-center justify-between mt-3">
                  <div className="flex items-center gap-2">
                    <button className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
                      <Calendar className="w-4 h-4" />
                    </button>
                    <button className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100">
                      <Clock className="w-4 h-4" />
                    </button>
                  </div>
                  <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-2">
                    <Send className="w-4 h-4" /> Send Reply
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400">
              Select a reply to view
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default RepliesContent;
