"use client";

/**
 * CampaignPriorityCard.tsx - Campaign card with priority slider
 * Design System: frontend/design/prototype/DESIGN_SYSTEM.md
 *
 * Features:
 * - AI Suggested badge (purple)
 * - Priority slider with percentage display
 * - Metrics row: meetings, reply rate
 * - Channel badges (email, linkedin, sms, voice)
 * - Status indicator (green dot for active)
 */

import { Mail, Linkedin, MessageSquare, Phone } from "lucide-react";

type Channel = "email" | "linkedin" | "sms" | "voice";
type CampaignStatus = "active" | "paused" | "draft";

interface CampaignPriorityCardProps {
  name: string;
  isAI?: boolean;
  priority: number;
  onPriorityChange: (value: number) => void;
  meetings: number;
  replyRate: number;
  channels: Channel[];
  status: CampaignStatus;
}

const channelConfig: Record<Channel, { icon: typeof Mail; color: string; label: string }> = {
  email: { icon: Mail, color: "bg-[#3B82F6]", label: "Email" },
  linkedin: { icon: Linkedin, color: "bg-[#0077B5]", label: "LinkedIn" },
  sms: { icon: MessageSquare, color: "bg-[#10B981]", label: "SMS" },
  voice: { icon: Phone, color: "bg-[#8B5CF6]", label: "Voice" },
};

export function CampaignPriorityCard({
  name,
  isAI = false,
  priority,
  onPriorityChange,
  meetings,
  replyRate,
  channels,
  status,
}: CampaignPriorityCardProps) {
  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onPriorityChange(Number(e.target.value));
  };

  return (
    <div className="bg-white rounded-xl border border-[#E2E8F0] shadow-sm p-5">
      {/* Header: Name + AI badge + Status */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {/* Status indicator */}
          <div
            className={`w-2 h-2 rounded-full ${
              status === "active"
                ? "bg-[#10B981]"
                : status === "paused"
                ? "bg-[#F97316]"
                : "bg-[#94A3B8]"
            }`}
          />
          <h3 className="text-base font-semibold text-[#1E293B]">{name}</h3>
          {isAI && (
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-[#EDE9FE] text-[#7C3AED]">
              AI Suggested
            </span>
          )}
        </div>

        {/* Channel badges */}
        <div className="flex items-center gap-1">
          {channels.map((channel) => {
            const config = channelConfig[channel];
            const IconComponent = config.icon;
            return (
              <div
                key={channel}
                className={`${config.color} p-1.5 rounded-md`}
                title={config.label}
              >
                <IconComponent className="h-3.5 w-3.5 text-white" />
              </div>
            );
          })}
        </div>
      </div>

      {/* Priority slider */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-[#64748B]">Priority</span>
          <span className="text-sm font-semibold text-[#1E293B]">{priority}%</span>
        </div>
        <div className="relative">
          <input
            type="range"
            min="0"
            max="100"
            value={priority}
            onChange={handleSliderChange}
            className="w-full h-2 bg-[#E2E8F0] rounded-full appearance-none cursor-pointer
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-5
              [&::-webkit-slider-thumb]:h-5
              [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:bg-[#3B82F6]
              [&::-webkit-slider-thumb]:border-2
              [&::-webkit-slider-thumb]:border-white
              [&::-webkit-slider-thumb]:shadow-md
              [&::-webkit-slider-thumb]:cursor-pointer
              [&::-moz-range-thumb]:w-5
              [&::-moz-range-thumb]:h-5
              [&::-moz-range-thumb]:rounded-full
              [&::-moz-range-thumb]:bg-[#3B82F6]
              [&::-moz-range-thumb]:border-2
              [&::-moz-range-thumb]:border-white
              [&::-moz-range-thumb]:shadow-md
              [&::-moz-range-thumb]:cursor-pointer"
            style={{
              background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${priority}%, #E2E8F0 ${priority}%, #E2E8F0 100%)`,
            }}
          />
        </div>
      </div>

      {/* Metrics row */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-[#1E293B]">{meetings}</span>
          <span className="text-[#64748B]">meetings</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-semibold text-[#1E293B]">{replyRate}%</span>
          <span className="text-[#64748B]">reply rate</span>
        </div>
      </div>
    </div>
  );
}
