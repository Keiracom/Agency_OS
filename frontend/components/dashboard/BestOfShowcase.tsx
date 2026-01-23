"use client";

/**
 * BestOfShowcase.tsx - High-Performing Content Display
 * Phase H - Item 47: Best Of Showcase
 *
 * Displays top-performing content examples to clients, showcasing
 * emails/messages that achieved strong engagement (replies, clicks, opens).
 */

import { useState } from "react";
import { useBestOfShowcase } from "@/hooks/use-reports";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Mail,
  MessageSquare,
  Linkedin,
  Phone,
  Send,
  Trophy,
  Star,
  Eye,
  MousePointer,
  MessageCircle,
  Calendar,
  Sparkles,
} from "lucide-react";
import type { BestOfContentItem } from "@/lib/api/types";

// Channel configuration
const channelConfig: Record<string, { icon: React.ReactNode; color: string }> = {
  email: { icon: <Mail className="h-4 w-4" />, color: "bg-blue-500/10 text-blue-400" },
  sms: { icon: <MessageSquare className="h-4 w-4" />, color: "bg-purple-500/10 text-purple-400" },
  linkedin: { icon: <Linkedin className="h-4 w-4" />, color: "bg-sky-500/10 text-sky-400" },
  voice: { icon: <Phone className="h-4 w-4" />, color: "bg-green-500/10 text-green-400" },
  mail: { icon: <Send className="h-4 w-4" />, color: "bg-orange-500/10 text-orange-400" },
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-AU", {
    month: "short",
    day: "numeric",
  });
}

function PerformanceBadge({ item }: { item: BestOfContentItem }) {
  if (item.got_conversion) {
    return (
      <Badge className="bg-green-500/20 text-green-400 border-green-500/30">
        <Calendar className="h-3 w-3 mr-1" />
        Meeting
      </Badge>
    );
  }
  if (item.got_reply) {
    return (
      <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">
        <MessageCircle className="h-3 w-3 mr-1" />
        Reply
      </Badge>
    );
  }
  if (item.email_click_count > 0) {
    return (
      <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
        <MousePointer className="h-3 w-3 mr-1" />
        Clicked
      </Badge>
    );
  }
  return (
    <Badge className="bg-yellow-500/20 text-yellow-400 border-yellow-500/30">
      <Eye className="h-3 w-3 mr-1" />
      Opened
    </Badge>
  );
}

function BestOfCard({
  item,
  rank,
  onClick,
}: {
  item: BestOfContentItem;
  rank: number;
  onClick: () => void;
}) {
  const channel = channelConfig[item.channel] || channelConfig.email;

  return (
    <div
      className="flex items-start gap-3 p-3 rounded-lg hover:bg-white/5 cursor-pointer transition-colors"
      onClick={onClick}
    >
      {/* Rank */}
      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-yellow-500/20 to-orange-500/20 flex items-center justify-center">
        <span className="text-xs font-bold text-yellow-400">
          {rank <= 3 ? <Star className="h-3 w-3 fill-yellow-400" /> : rank}
        </span>
      </div>

      {/* Channel Icon */}
      <div className={`flex-shrink-0 p-1.5 rounded ${channel.color}`}>
        {channel.icon}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium text-white truncate">
            {item.lead_name || item.lead_email || "Unknown"}
          </span>
          <PerformanceBadge item={item} />
        </div>
        {item.subject && (
          <p className="text-xs text-gray-400 truncate">{item.subject}</p>
        )}
        <p className="text-[10px] text-gray-500 mt-1">
          {formatDate(item.timestamp)} · {item.performance_reason}
        </p>
      </div>
    </div>
  );
}

function ContentDetailModal({
  item,
  open,
  onClose,
}: {
  item: BestOfContentItem | null;
  open: boolean;
  onClose: () => void;
}) {
  if (!item) return null;

  const channel = channelConfig[item.channel] || channelConfig.email;

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Trophy className="h-5 w-5 text-yellow-400" />
            Top Performer
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* Performance Summary */}
          <div className="flex items-center gap-3 p-3 bg-gradient-to-r from-yellow-500/10 to-orange-500/10 rounded-lg border border-yellow-500/20">
            <Sparkles className="h-5 w-5 text-yellow-400" />
            <span className="text-sm text-yellow-200">{item.performance_reason}</span>
          </div>

          {/* Metadata */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Recipient:</span>
              <span className="ml-2 text-gray-300">{item.lead_name || item.lead_email || "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">Company:</span>
              <span className="ml-2 text-gray-300">{item.lead_company || "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">Campaign:</span>
              <span className="ml-2 text-gray-300">{item.campaign_name || "—"}</span>
            </div>
            <div>
              <span className="text-gray-500">Sent:</span>
              <span className="ml-2 text-gray-300">{formatDate(item.timestamp)}</span>
            </div>
          </div>

          {/* Engagement Stats */}
          <div className="flex items-center gap-6 p-3 bg-white/5 rounded-lg">
            <div className="flex items-center gap-2">
              <Eye className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-300">{item.email_open_count} opens</span>
            </div>
            <div className="flex items-center gap-2">
              <MousePointer className="h-4 w-4 text-gray-400" />
              <span className="text-sm text-gray-300">{item.email_click_count} clicks</span>
            </div>
            {item.got_reply && (
              <div className="flex items-center gap-2">
                <MessageCircle className="h-4 w-4 text-green-400" />
                <span className="text-sm text-green-400">Got reply</span>
              </div>
            )}
            {item.got_conversion && (
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-green-400" />
                <span className="text-sm text-green-400">Led to meeting</span>
              </div>
            )}
          </div>

          {/* Subject */}
          {item.subject && (
            <div>
              <h4 className="text-sm font-medium text-gray-400 mb-1">Subject</h4>
              <p className="text-gray-200">{item.subject}</p>
            </div>
          )}

          {/* Full Content */}
          <div>
            <h4 className="text-sm font-medium text-gray-400 mb-1">Content</h4>
            <div className="p-4 bg-white/5 rounded-lg">
              <pre className="whitespace-pre-wrap text-sm text-gray-300 font-sans">
                {item.full_message_body || item.content_preview || "No content available"}
              </pre>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

interface BestOfShowcaseProps {
  limit?: number;
  periodDays?: number;
  showHeader?: boolean;
  compact?: boolean;
}

export function BestOfShowcase({
  limit = 5,
  periodDays = 30,
  showHeader = true,
  compact = false,
}: BestOfShowcaseProps) {
  const [selectedItem, setSelectedItem] = useState<BestOfContentItem | null>(null);
  const { data, isLoading, error } = useBestOfShowcase({ limit, period_days: periodDays });

  if (isLoading) {
    return (
      <Card>
        {showHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Trophy className="h-4 w-4 text-yellow-400" />
              Top Performers
            </CardTitle>
          </CardHeader>
        )}
        <CardContent className={compact ? "p-3" : "p-4"}>
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center gap-3 animate-pulse">
                <div className="w-6 h-6 rounded-full bg-white/10" />
                <div className="w-8 h-8 rounded bg-white/10" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-white/10 rounded w-3/4" />
                  <div className="h-3 bg-white/10 rounded w-1/2" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error || !data?.items.length) {
    return (
      <Card>
        {showHeader && (
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Trophy className="h-4 w-4 text-yellow-400" />
              Top Performers
            </CardTitle>
          </CardHeader>
        )}
        <CardContent className={compact ? "p-3" : "p-6"}>
          <div className="text-center text-gray-500">
            <Trophy className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No high performers yet</p>
            <p className="text-xs mt-1">Content that gets engagement will appear here</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        {showHeader && (
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Trophy className="h-4 w-4 text-yellow-400" />
                Top Performers
              </CardTitle>
              <span className="text-xs text-gray-500">
                Last {data.period_days} days
              </span>
            </div>
          </CardHeader>
        )}
        <CardContent className={compact ? "p-2" : "p-3"}>
          <div className="space-y-1">
            {data.items.map((item, idx) => (
              <BestOfCard
                key={item.id}
                item={item}
                rank={idx + 1}
                onClick={() => setSelectedItem(item)}
              />
            ))}
          </div>
          {data.total_high_performers > limit && (
            <p className="text-xs text-gray-500 text-center mt-3">
              +{data.total_high_performers - limit} more high performers
            </p>
          )}
        </CardContent>
      </Card>

      <ContentDetailModal
        item={selectedItem}
        open={!!selectedItem}
        onClose={() => setSelectedItem(null)}
      />
    </>
  );
}

export default BestOfShowcase;
