/**
 * FILE: frontend/app/dashboard/replies/page.tsx
 * PURPOSE: Inbox-style view of lead replies
 * PHASE: 14 (Missing UI)
 * TASK: MUI-001
 */

"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Mail,
  MessageSquare,
  Linkedin,
  Search,
  Check,
  X,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Calendar,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  Clock,
  Inbox,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useReplies, useMarkReplyHandled, type Reply, type IntentType } from "@/hooks/use-replies";
import { TableSkeleton } from "@/components/ui/loading-skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { EmptyState, NoSearchResults } from "@/components/ui/empty-state";
import { useToast } from "@/hooks/use-toast";
import type { ChannelType } from "@/lib/api/types";

const channelIcons: Record<ChannelType, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  linkedin: Linkedin,
  voice: MessageSquare,
  mail: Mail,
};

const intentConfig: Record<IntentType, { label: string; icon: typeof Calendar; color: string }> = {
  meeting_request: { label: "Meeting", icon: Calendar, color: "bg-green-100 text-green-800" },
  interested: { label: "Interested", icon: ThumbsUp, color: "bg-blue-100 text-blue-800" },
  question: { label: "Question", icon: HelpCircle, color: "bg-yellow-100 text-yellow-800" },
  not_interested: { label: "Not Interested", icon: ThumbsDown, color: "bg-gray-100 text-gray-800" },
  unsubscribe: { label: "Unsubscribe", icon: X, color: "bg-red-100 text-red-800" },
  out_of_office: { label: "OOO", icon: Clock, color: "bg-purple-100 text-purple-800" },
  auto_reply: { label: "Auto-Reply", icon: MessageSquare, color: "bg-gray-100 text-gray-600" },
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function RepliesPage() {
  const [intentFilter, setIntentFilter] = useState<IntentType | undefined>();
  const [channelFilter, setChannelFilter] = useState<ChannelType | undefined>();
  const [handledFilter, setHandledFilter] = useState<boolean | undefined>(false); // Default: unhandled
  const [page, setPage] = useState(1);
  const [selectedReply, setSelectedReply] = useState<Reply | null>(null);
  const { toast } = useToast();

  const { data, isLoading, error, refetch } = useReplies({
    page,
    page_size: 20,
    intent: intentFilter,
    channel: channelFilter,
    handled: handledFilter,
  });

  const markHandledMutation = useMarkReplyHandled();

  const handleMarkHandled = async (reply: Reply, handled: boolean) => {
    try {
      await markHandledMutation.mutateAsync({ replyId: reply.id, handled });
      toast({ title: handled ? "Marked as handled" : "Marked as unhandled" });
      if (selectedReply?.id === reply.id) {
        setSelectedReply(null);
      }
    } catch {
      toast({ title: "Failed to update reply", variant: "destructive" });
    }
  };

  const replies = data?.items || [];
  const totalPages = data?.total_pages || 1;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Replies</h1>
          <p className="text-muted-foreground">
            Manage incoming replies from your campaigns
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={handledFilter === false ? "default" : "outline"}
            onClick={() => {
              setHandledFilter(handledFilter === false ? undefined : false);
              setPage(1);
            }}
          >
            <Inbox className="mr-2 h-4 w-4" />
            Unhandled
          </Button>
          <Button
            variant={handledFilter === true ? "default" : "outline"}
            onClick={() => {
              setHandledFilter(handledFilter === true ? undefined : true);
              setPage(1);
            }}
          >
            <Check className="mr-2 h-4 w-4" />
            Handled
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <span className="text-sm text-muted-foreground py-2">Intent:</span>
        {(Object.keys(intentConfig) as IntentType[]).map((intent) => (
          <Button
            key={intent}
            size="sm"
            variant={intentFilter === intent ? "default" : "outline"}
            onClick={() => {
              setIntentFilter(intentFilter === intent ? undefined : intent);
              setPage(1);
            }}
            className="h-8"
          >
            {intentConfig[intent].label}
          </Button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="text-sm text-muted-foreground py-2">Channel:</span>
        {(["email", "sms", "linkedin"] as ChannelType[]).map((channel) => {
          const Icon = channelIcons[channel];
          return (
            <Button
              key={channel}
              size="sm"
              variant={channelFilter === channel ? "default" : "outline"}
              onClick={() => {
                setChannelFilter(channelFilter === channel ? undefined : channel);
                setPage(1);
              }}
              className="h-8 gap-1"
            >
              <Icon className="h-3 w-3" />
              {channel.charAt(0).toUpperCase() + channel.slice(1)}
            </Button>
          );
        })}
      </div>

      {/* Replies List */}
      <Card>
        <CardHeader>
          <CardTitle>
            {handledFilter === false
              ? "Unhandled Replies"
              : handledFilter === true
                ? "Handled Replies"
                : "All Replies"}
          </CardTitle>
          <CardDescription>
            {data?.total ? `${data.total.toLocaleString()} replies` : "Click on a reply to view details"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <TableSkeleton rows={10} />
          ) : error ? (
            <ErrorState error={error} onRetry={refetch} />
          ) : replies.length === 0 ? (
            intentFilter || channelFilter ? (
              <NoSearchResults
                query={intentFilter || channelFilter || ""}
                onClear={() => {
                  setIntentFilter(undefined);
                  setChannelFilter(undefined);
                  setPage(1);
                }}
              />
            ) : (
              <EmptyState
                icon={Inbox}
                title="No replies yet"
                description="Replies from your leads will appear here"
              />
            )
          ) : (
            <>
              <div className="space-y-2">
                {replies.map((reply) => {
                  const ChannelIcon = channelIcons[reply.channel] || Mail;
                  const intentCfg = reply.intent ? intentConfig[reply.intent] : null;

                  return (
                    <div
                      key={reply.id}
                      onClick={() => setSelectedReply(reply)}
                      className={`flex items-start gap-4 p-4 rounded-lg border cursor-pointer transition-colors hover:bg-muted/50 ${
                        reply.handled ? "opacity-60" : ""
                      }`}
                    >
                      {/* Channel Icon */}
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
                        <ChannelIcon className="h-5 w-5 text-muted-foreground" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium">
                            {reply.lead?.first_name} {reply.lead?.last_name}
                          </span>
                          {reply.lead?.company && (
                            <span className="text-sm text-muted-foreground">
                              at {reply.lead.company}
                            </span>
                          )}
                        </div>

                        {reply.subject && (
                          <p className="text-sm font-medium mb-1 truncate">
                            {reply.subject}
                          </p>
                        )}

                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {reply.content || "No content preview available"}
                        </p>

                        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                          <span>{formatDate(reply.received_at)}</span>
                          {reply.campaign_name && (
                            <>
                              <span>·</span>
                              <span>{reply.campaign_name}</span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Right Side */}
                      <div className="flex flex-col items-end gap-2">
                        {intentCfg && (
                          <Badge className={intentCfg.color}>
                            {intentCfg.label}
                          </Badge>
                        )}

                        <div className="flex gap-1">
                          {reply.handled ? (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="h-7"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleMarkHandled(reply, false);
                              }}
                            >
                              <X className="h-3 w-3 mr-1" />
                              Unhandle
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleMarkHandled(reply, true);
                              }}
                            >
                              <Check className="h-3 w-3 mr-1" />
                              Handle
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-muted-foreground">
                    Page {page} of {totalPages}
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Reply Detail Dialog */}
      <Dialog open={!!selectedReply} onOpenChange={() => setSelectedReply(null)}>
        <DialogContent className="max-w-2xl">
          {selectedReply && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span>
                    {selectedReply.lead?.first_name} {selectedReply.lead?.last_name}
                  </span>
                  {selectedReply.intent && intentConfig[selectedReply.intent] && (
                    <Badge className={intentConfig[selectedReply.intent].color}>
                      {intentConfig[selectedReply.intent].label}
                    </Badge>
                  )}
                </DialogTitle>
                <DialogDescription>
                  {selectedReply.lead?.company && `${selectedReply.lead.company} · `}
                  {selectedReply.lead?.email}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Metadata */}
                <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    {(() => {
                      const Icon = channelIcons[selectedReply.channel] || Mail;
                      return <Icon className="h-4 w-4" />;
                    })()}
                    {selectedReply.channel}
                  </div>
                  <div>{formatDate(selectedReply.received_at)}</div>
                  {selectedReply.campaign_name && (
                    <div>Campaign: {selectedReply.campaign_name}</div>
                  )}
                </div>

                {/* Subject */}
                {selectedReply.subject && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground mb-1">
                      Subject
                    </p>
                    <p className="font-medium">{selectedReply.subject}</p>
                  </div>
                )}

                {/* Content */}
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">
                    Message
                  </p>
                  <div className="bg-muted p-4 rounded-lg whitespace-pre-wrap">
                    {selectedReply.content || "No content available"}
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-4 border-t">
                  <Link href={`/dashboard/leads/${selectedReply.lead_id}`}>
                    <Button variant="outline">
                      <ExternalLink className="h-4 w-4 mr-2" />
                      View Lead
                    </Button>
                  </Link>

                  {selectedReply.handled ? (
                    <Button
                      variant="outline"
                      onClick={() => handleMarkHandled(selectedReply, false)}
                    >
                      <X className="h-4 w-4 mr-2" />
                      Mark Unhandled
                    </Button>
                  ) : (
                    <Button onClick={() => handleMarkHandled(selectedReply, true)}>
                      <Check className="h-4 w-4 mr-2" />
                      Mark Handled
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
