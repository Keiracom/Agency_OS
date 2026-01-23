/**
 * Campaign Card - Priority slider and stats
 * Open in Codux to adjust card layout, slider styling
 */

"use client";

import { Bot, Pencil, Mail, Linkedin, Phone, MessageSquare } from "lucide-react";

type Channel = "email" | "linkedin" | "sms" | "voice";
type Status = "active" | "paused" | "draft";

interface CampaignCardProps {
  name: string;
  isAI?: boolean;
  priority: number;
  onPriorityChange?: (value: number) => void;
  meetings: number;
  replyRate: number;
  channels: Channel[];
  status: Status;
}

const channelIcons: Record<Channel, typeof Mail> = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  voice: Phone,
};

const statusColors: Record<Status, { dot: string; text: string }> = {
  active: { dot: "bg-[#10B981]", text: "text-[#10B981]" },
  paused: { dot: "bg-[#F59E0B]", text: "text-[#F59E0B]" },
  draft: { dot: "bg-[#94A3B8]", text: "text-[#94A3B8]" },
};

export function CampaignCard({
  name,
  isAI = false,
  priority,
  onPriorityChange,
  meetings,
  replyRate,
  channels,
  status,
}: CampaignCardProps) {
  const statusStyle = statusColors[status];

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] p-5 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          {isAI ? (
            <Bot className="h-5 w-5 text-[#3B82F6]" />
          ) : (
            <Pencil className="h-5 w-5 text-[#94A3B8]" />
          )}
          <span className="font-semibold text-[#1E293B]">{name}</span>
        </div>
        <span className={`
          px-2 py-1 rounded-full text-xs font-medium
          ${isAI ? "bg-[#DBEAFE] text-[#2563EB]" : "bg-[#F1F5F9] text-[#64748B]"}
        `}>
          {isAI ? "AI SUGGESTED" : "CUSTOM"}
        </span>
      </div>

      {/* Priority Slider */}
      <div className="mb-4">
        <div className="flex justify-between text-xs text-[#94A3B8] mb-2">
          <span>Low</span>
          <span>High</span>
        </div>
        <input
          type="range"
          min={10}
          max={80}
          value={priority}
          onChange={(e) => onPriorityChange?.(Number(e.target.value))}
          className="w-full h-2 bg-[#E2E8F0] rounded-lg appearance-none cursor-pointer accent-[#3B82F6]"
        />
        <div className="text-center mt-2">
          <span className="text-2xl font-bold text-[#1E293B]">{priority}%</span>
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-sm text-[#64748B] mb-4">
        <span><span className="font-medium text-[#1E293B]">{meetings}</span> meetings</span>
        <span className="text-[#E2E8F0]">|</span>
        <span><span className="font-medium text-[#1E293B]">{replyRate.toFixed(1)}%</span> reply rate</span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {channels.map((channel) => {
            const Icon = channelIcons[channel];
            return (
              <div key={channel} className="flex items-center gap-1 px-2 py-1 rounded bg-[#F1F5F9] text-xs text-[#64748B]">
                <Icon className="h-3 w-3" />
                <span className="capitalize">{channel}</span>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-1.5">
          <div className={`h-2 w-2 rounded-full ${statusStyle.dot}`} />
          <span className={`text-xs font-medium capitalize ${statusStyle.text}`}>{status}</span>
        </div>
      </div>
    </div>
  );
}

export default CampaignCard;
