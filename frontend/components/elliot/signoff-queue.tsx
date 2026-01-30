/**
 * FILE: frontend/components/elliot/signoff-queue.tsx
 * PURPOSE: Sign-off Queue component for approving/rejecting knowledge actions
 * PHASE: Elliot Dashboard
 */

"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useSignoffQueue, useSignoffAction, type SignoffItem } from "@/hooks/use-elliot";
import {
  CheckCircle2,
  XCircle,
  RefreshCw,
  Clock,
  AlertTriangle,
  ClipboardCheck,
  Microscope,
  Hammer,
  Search,
  Loader2,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";

type SignoffStatus = "pending" | "approved" | "rejected" | "all";

const actionTypeConfig: Record<string, { icon: typeof Microscope; label: string; color: string }> = {
  evaluate_tool: { icon: Microscope, label: "Evaluate Tool", color: "text-blue-500" },
  build_poc: { icon: Hammer, label: "Build PoC", color: "text-purple-500" },
  research: { icon: Search, label: "Research", color: "text-green-500" },
};

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
}

function SignoffCard({ 
  item, 
  onApprove, 
  onReject,
  isProcessing,
}: { 
  item: SignoffItem;
  onApprove: () => void;
  onReject: () => void;
  isProcessing: boolean;
}) {
  const config = actionTypeConfig[item.action_type] || actionTypeConfig.research;
  const ActionIcon = config.icon;

  return (
    <div className="flex items-start gap-4 rounded-lg border p-4 transition-colors hover:bg-muted/50">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted">
        <ActionIcon className={`h-5 w-5 ${config.color}`} />
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-medium">{item.title}</span>
          <Badge variant="outline" className="text-xs">
            {config.label}
          </Badge>
          {item.status !== "pending" && (
            <Badge variant={item.status === "approved" ? "secondary" : "destructive"}>
              {item.status === "approved" ? "Approved" : "Rejected"}
            </Badge>
          )}
        </div>
        <p className="text-sm text-muted-foreground line-clamp-2">
          {item.summary}
        </p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatTimeAgo(item.created_at)}
          </span>
          {item.decided_at && (
            <span>Decided: {formatTimeAgo(item.decided_at)}</span>
          )}
        </div>
        
        {item.status === "pending" && (
          <div className="flex items-center gap-2 pt-2">
            <Button
              size="sm"
              variant="default"
              onClick={onApprove}
              disabled={isProcessing}
              className="bg-green-600 hover:bg-green-700"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4 mr-1" />
              )}
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={onReject}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <XCircle className="h-4 w-4 mr-1" />
              )}
              Reject
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export function SignoffQueue() {
  const [filter, setFilter] = useState<SignoffStatus>("pending");
  const [processingId, setProcessingId] = useState<string | null>(null);
  const { data: items, isLoading, error, refetch } = useSignoffQueue(filter);
  const signoffAction = useSignoffAction();
  const { toast } = useToast();

  const handleAction = async (id: string, action: "approved" | "rejected") => {
    setProcessingId(id);
    try {
      await signoffAction.mutateAsync({ id, action });
      toast({
        title: action === "approved" ? "Approved" : "Rejected",
        description: `Item has been ${action}`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to process action",
        variant: "destructive",
      });
    } finally {
      setProcessingId(null);
    }
  };

  const pendingCount = items?.filter(i => i.status === "pending").length || 0;

  return (
    <div className="space-y-6">
      {/* Summary Card */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
          <ClipboardCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{pendingCount}</div>
          <p className="text-xs text-muted-foreground">
            {pendingCount === 0 ? "All caught up!" : "Items awaiting your decision"}
          </p>
        </CardContent>
      </Card>

      {/* Sign-off List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Sign-off Queue</CardTitle>
              <CardDescription>Review and approve/reject knowledge actions</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Select value={filter} onValueChange={(v) => setFilter(v as SignoffStatus)}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Filter" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="approved">Approved</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                  <SelectItem value="all">All</SelectItem>
                </SelectContent>
              </Select>
              <Button variant="outline" size="icon" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-start gap-4 rounded-lg border p-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-8 w-32" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <AlertTriangle className="mr-2 h-5 w-5" />
              Failed to load queue
            </div>
          ) : !items || items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <ClipboardCheck className="h-12 w-12 mb-2 opacity-50" />
              <p>No items in queue</p>
              <p className="text-sm">
                {filter === "pending" 
                  ? "All caught up! No pending sign-offs." 
                  : "No items match this filter."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {items.map((item) => (
                <SignoffCard
                  key={item.id}
                  item={item}
                  onApprove={() => handleAction(item.id, "approved")}
                  onReject={() => handleAction(item.id, "rejected")}
                  isProcessing={processingId === item.id}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
