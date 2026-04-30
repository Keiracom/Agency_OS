/**
 * ChannelMatrix.tsx - 5-Channel Performance Matrix
 * Mini cards with channel-specific colors (amber theme)
 */

"use client";

import { Mail, Briefcase, MessageCircle, Phone, Send } from "lucide-react";
import { channelData, type ChannelType } from "@/lib/mock/reports-data";

const channelConfig: Record<ChannelType, { icon: React.ReactNode; rateColor: string; barColor: string }> = {
  email: { icon: <Mail className="w-6 h-6" />, rateColor: "text-[#D4956A]", barColor: "bg-[#D4956A]" },
  linkedin: { icon: <Briefcase className="w-6 h-6" />, rateColor: "text-[#0A66C2]", barColor: "bg-[#0A66C2]" },
  sms: { icon: <MessageCircle className="w-6 h-6" />, rateColor: "text-amber", barColor: "bg-amber" },
  voice: { icon: <Phone className="w-6 h-6" />, rateColor: "text-amber-500", barColor: "bg-amber-500" },
  mail: { icon: <Send className="w-6 h-6" />, rateColor: "text-amber", barColor: "bg-amber" },
};

export function ChannelMatrix() {
  const maxMeetings = Math.max(...channelData.map((c) => c.meetings));

  return (
    <div className="bg-bg-surface border border-default rounded-xl overflow-hidden mb-6">
      <div className="flex items-center justify-between px-5 py-4 border-b border-default">
        <h3 className="text-sm font-semibold text-ink">5-Channel Performance Matrix</h3>
        <span className="text-xs text-ink-3">Feb 1-28, 2026</span>
      </div>
      <div className="p-5 grid grid-cols-5 gap-3">
        {channelData.map((ch) => {
          const cfg = channelConfig[ch.channel];
          const barWidth = (ch.meetings / maxMeetings) * 100;
          return (
            <div key={ch.channel} className="bg-bg-cream rounded-lg p-4 text-center">
              <div className="text-ink-3 mb-2 flex justify-center">{cfg.icon}</div>
              <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-3 mb-3">{ch.name}</p>
              <div className="mb-2">
                <p className="text-xl font-bold font-mono text-ink">{ch.volume.toLocaleString()}</p>
                <p className="text-[10px] text-ink-3">{ch.volumeLabel}</p>
              </div>
              <div className="mb-2">
                <p className={`text-xl font-bold font-mono ${cfg.rateColor}`}>{ch.replyRate}%</p>
                <p className="text-[10px] text-ink-3">Reply Rate</p>
              </div>
              <div className="mb-2">
                <p className="text-xl font-bold font-mono text-[#22C55E]">{ch.meetings}</p>
                <p className="text-[10px] text-ink-3">Meetings</p>
              </div>
              <div className="h-1 bg-bg-surface rounded-full mt-2 overflow-hidden">
                <div className={`h-full rounded-full ${cfg.barColor}`} style={{ width: `${barWidth}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
