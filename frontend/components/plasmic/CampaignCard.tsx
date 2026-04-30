/**
 * FILE: frontend/components/plasmic/CampaignCard.tsx
 * PURPOSE: Campaign priority card with slider - Plasmic design spec
 * DESIGN: Name + AI badge + priority slider + stats
 */

"use client";

import { cn } from "@/lib/utils";
import { Bot, Pencil, Mail, Linkedin, Phone, MessageSquare } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Slider } from "@/components/ui/slider";

type CampaignStatus = "active" | "paused" | "draft";
type Channel = "email" | "linkedin" | "sms" | "voice";

interface CampaignCardProps {
  name: string;
  isAI?: boolean;
  priority: number; // 0-100
  onPriorityChange?: (value: number) => void;
  meetings: number;
  replyRate: number;
  showRate?: number;
  channels: Channel[];
  status: CampaignStatus;
  className?: string;
  disabled?: boolean;
}

const channelIcons: Record<Channel, React.ElementType> = {
  email: Mail,
  linkedin: Linkedin,
  sms: MessageSquare,
  voice: Phone,
};

const statusConfig: Record<CampaignStatus, { color: string; bg: string }> = {
  active: { color: "text-[#10B981]", bg: "bg-[#10B981]" },
  paused: { color: "text-[#F59E0B]", bg: "bg-[#F59E0B]" },
  draft: { color: "text-[#6B7280]", bg: "bg-[#6B7280]" },
};

export function CampaignCard({
  name,
  isAI = false,
  priority,
  onPriorityChange,
  meetings,
  replyRate,
  showRate,
  channels,
  status,
  className,
  disabled = false,
}: CampaignCardProps) {
  const statusCfg = statusConfig[status];

  return (
    <Card
      className={cn(
        "bg-[#1a1a1f] border-white/10 transition-all",
        disabled && "opacity-50",
        className
      )}
    >
      <CardContent className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2">
            {isAI ? (
              <Bot className="h-5 w-5 text-[#2196F3]" />
            ) : (
              <Pencil className="h-5 w-5 text-ink/40" />
            )}
            <span className="font-semibold text-ink">{name}</span>
          </div>
          <Badge
            className={cn(
              "text-xs font-medium",
              isAI
                ? "bg-[#2196F3]/20 text-[#2196F3] hover:bg-[#2196F3]/30"
                : "bg-bg-panel/10 text-ink/60 hover:bg-bg-panel/20"
            )}
          >
            {isAI ? "AI SUGGESTED" : "CUSTOM"}
          </Badge>
        </div>

        {/* Priority Slider */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-ink/40 mb-2">
            <span>Low</span>
            <span>High</span>
          </div>
          <Slider
            value={[priority]}
            onValueChange={(values) => onPriorityChange?.(values[0])}
            min={10}
            max={80}
            step={1}
            disabled={disabled}
            className="mb-2"
          />
          <div className="text-center">
            <span className="text-2xl font-bold text-ink">{priority}%</span>
          </div>
        </div>

        {/* Stats Row */}
        <div className="flex items-center gap-4 text-sm text-ink/60 mb-4">
          <span>
            <span className="font-medium text-ink">{meetings}</span> meetings
          </span>
          <span className="text-ink/20">|</span>
          <span>
            <span className="font-medium text-ink">{replyRate.toFixed(1)}%</span> reply rate
          </span>
          {showRate !== undefined && (
            <>
              <span className="text-ink/20">|</span>
              <span>
                <span className="font-medium text-ink">{showRate}%</span> show rate
              </span>
            </>
          )}
        </div>

        {/* Footer: Channels + Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {channels.map((channel) => {
              const Icon = channelIcons[channel];
              return (
                <div
                  key={channel}
                  className="flex items-center gap-1 px-2 py-1 rounded bg-bg-panel/5 text-xs text-ink/60"
                >
                  <Icon className="h-3 w-3" />
                  <span className="capitalize">{channel}</span>
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-1.5">
            <div className={cn("h-2 w-2 rounded-full", statusCfg.bg)} />
            <span className={cn("text-xs font-medium capitalize", statusCfg.color)}>
              {status}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default CampaignCard;
