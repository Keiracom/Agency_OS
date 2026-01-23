/**
 * FILE: frontend/components/campaigns/CampaignPriorityPanel.tsx
 * PURPOSE: Container panel for campaign allocation UI
 * PHASE: Phase I Dashboard Redesign (Item 53)
 *
 * Layout:
 * - Header: "YOUR CAMPAIGNS" + slot count + Add button
 * - Body: Children slot for campaign cards
 * - Footer: Pending changes + Cancel/Confirm buttons
 *
 * States: initial, pending, processing, success, error
 */

"use client";

import * as React from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Plus, Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

export type PanelState = "initial" | "pending" | "processing" | "success" | "error";

interface CampaignPriorityPanelProps {
  /** Current panel state */
  state: PanelState;
  /** Number of campaigns currently used */
  usedSlots: number;
  /** Maximum number of campaigns allowed (from tier) */
  maxSlots: number;
  /** Children (campaign cards) */
  children: React.ReactNode;
  /** Callback when Add Campaign is clicked */
  onAddCampaign?: () => void;
  /** Callback when Cancel is clicked */
  onCancel?: () => void;
  /** Callback when Confirm is clicked */
  onConfirm?: () => void;
  /** Callback when Try Again is clicked (error state) */
  onRetry?: () => void;
  /** Callback when View Campaigns is clicked (success state) */
  onViewCampaigns?: () => void;
  /** Error message to display */
  errorMessage?: string;
  /** Additional class names */
  className?: string;
}

/**
 * Container panel for campaign priority allocation.
 *
 * Handles layout and state transitions for the campaign allocation UI.
 */
export function CampaignPriorityPanel({
  state,
  usedSlots,
  maxSlots,
  children,
  onAddCampaign,
  onCancel,
  onConfirm,
  onRetry,
  onViewCampaigns,
  errorMessage,
  className,
}: CampaignPriorityPanelProps) {
  const canAddCampaign = usedSlots < maxSlots;

  return (
    <Card className={cn("w-full", className)}>
      {/* Header */}
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <h2 className="text-lg font-semibold">Your Campaigns</h2>
          <p className="text-sm text-muted-foreground">
            {usedSlots} of {maxSlots} slots used
          </p>
        </div>
        {state === "initial" || state === "pending" ? (
          <Button
            variant="outline"
            size="sm"
            onClick={onAddCampaign}
            disabled={!canAddCampaign}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Campaign
          </Button>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Main content area - changes based on state */}
        {state === "processing" ? (
          <ProcessingState />
        ) : state === "success" ? (
          <SuccessState onViewCampaigns={onViewCampaigns} />
        ) : state === "error" ? (
          <ErrorState message={errorMessage} onRetry={onRetry} />
        ) : (
          <>
            {/* Campaign cards */}
            <div className="space-y-4">{children}</div>

            {/* Empty slot placeholder */}
            {canAddCampaign && (
              <button
                onClick={onAddCampaign}
                className="w-full border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center text-muted-foreground hover:border-muted-foreground/50 hover:text-muted-foreground/75 transition-colors"
              >
                <Plus className="h-6 w-6 mx-auto mb-2" />
                <span className="text-sm">Add another campaign</span>
              </button>
            )}
          </>
        )}

        {/* Footer - only show for pending state */}
        {state === "pending" && (
          <PendingFooter onCancel={onCancel} onConfirm={onConfirm} />
        )}
      </CardContent>
    </Card>
  );
}

/**
 * Processing state content
 */
function ProcessingState() {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
      <h3 className="text-lg font-medium mb-2">Preparing your campaigns...</h3>
      <div className="text-sm text-muted-foreground space-y-1">
        <p>Finding ideal prospects</p>
        <p>Researching & qualifying</p>
        <p>Setting up outreach sequences</p>
      </div>
      <p className="text-xs text-muted-foreground mt-4">
        This usually takes 30-60 seconds
      </p>
    </div>
  );
}

/**
 * Success state content
 */
function SuccessState({ onViewCampaigns }: { onViewCampaigns?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <CheckCircle className="h-10 w-10 text-green-500 mb-4" />
      <h3 className="text-lg font-medium mb-2">Campaigns ready!</h3>
      <p className="text-sm text-muted-foreground mb-6">
        Your priorities have been updated.
        <br />
        Outreach will begin during business hours.
      </p>
      {onViewCampaigns && (
        <Button onClick={onViewCampaigns}>View Campaigns</Button>
      )}
    </div>
  );
}

/**
 * Error state content
 */
function ErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <XCircle className="h-10 w-10 text-destructive mb-4" />
      <h3 className="text-lg font-medium mb-2">Something went wrong</h3>
      <p className="text-sm text-muted-foreground mb-6">
        {message || "We couldn't update your campaigns."}
        <br />
        Your previous settings are still active.
      </p>
      <div className="flex gap-3">
        {onRetry && (
          <Button variant="outline" onClick={onRetry}>
            Try Again
          </Button>
        )}
        <Button variant="ghost" asChild>
          <a href="mailto:support@agencyos.com">Contact Support</a>
        </Button>
      </div>
    </div>
  );
}

/**
 * Pending changes footer
 */
function PendingFooter({
  onCancel,
  onConfirm,
}: {
  onCancel?: () => void;
  onConfirm?: () => void;
}) {
  return (
    <div className="border-t pt-4 mt-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-amber-600">
          <AlertTriangle className="h-4 w-4" />
          <span className="text-sm font-medium">Changes pending</span>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={onConfirm}>Confirm & Activate</Button>
        </div>
      </div>
    </div>
  );
}

export default CampaignPriorityPanel;
