"use client";

/**
 * LeadBulkActions.tsx - Bulk Operations Toolbar for Leads
 * Purpose: Provide multi-select bulk actions for lead management
 * Layer: Frontend Component
 * Consumers: Lead list views, dashboard lead tables
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import {
  ChevronDown,
  Mail,
  UserX,
  Trash2,
  Tag,
  RefreshCw,
  Download,
  ArrowRight,
  Loader2,
  X,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

// Bulk action types
export type BulkActionType =
  | "send_email"
  | "assign_campaign"
  | "add_tag"
  | "update_status"
  | "re_enrich"
  | "export"
  | "suppress"
  | "delete";

// Campaign for assignment
export interface CampaignOption {
  id: string;
  name: string;
}

// Status options for bulk update
export type LeadStatusOption =
  | "new"
  | "enriched"
  | "scored"
  | "in_sequence"
  | "converted"
  | "unsubscribed"
  | "bounced";

// Bulk action options passed with certain actions
export interface BulkActionOptions {
  campaignId?: string;
  tagName?: string;
  status?: LeadStatusOption;
}

// Result of a bulk operation
export interface BulkActionResult {
  success: boolean;
  processed: number;
  failed: number;
  message?: string;
}

// Props for the component
export interface LeadBulkActionsProps {
  /** Array of selected lead IDs */
  selectedIds: string[];
  /** Callback to execute a bulk action */
  onAction: (
    action: BulkActionType,
    leadIds: string[],
    options?: BulkActionOptions
  ) => Promise<BulkActionResult>;
  /** Callback to clear current selection */
  onClearSelection: () => void;
  /** Available campaigns for assignment (optional) */
  campaigns?: CampaignOption[];
  /** Available tags for tagging (optional) */
  tags?: string[];
  /** Custom class name */
  className?: string;
  /** Whether the component is disabled */
  disabled?: boolean;
}

export function LeadBulkActions({
  selectedIds,
  onAction,
  onClearSelection,
  campaigns = [],
  tags = [],
  className,
  disabled = false,
}: LeadBulkActionsProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [currentAction, setCurrentAction] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    action: BulkActionType;
    title: string;
    description: string;
    options?: BulkActionOptions;
  }>({
    open: false,
    action: "delete",
    title: "",
    description: "",
  });

  const { toast } = useToast();
  const selectedCount = selectedIds.length;

  // Don't render if nothing is selected
  if (selectedCount === 0) {
    return null;
  }

  // Actions that require confirmation
  const confirmationRequired: BulkActionType[] = ["delete", "suppress"];

  // Get confirmation dialog content for an action
  const getConfirmationContent = (action: BulkActionType) => {
    const plural = selectedCount > 1 ? "s" : "";

    switch (action) {
      case "delete":
        return {
          title: "Delete Leads",
          description: `You are about to delete ${selectedCount} lead${plural}. This action cannot be undone. Are you sure you want to continue?`,
        };
      case "suppress":
        return {
          title: "Suppress Leads",
          description: `You are about to suppress ${selectedCount} lead${plural}. Suppressed leads will not receive any outreach. This can be reversed later.`,
        };
      default:
        return { title: "", description: "" };
    }
  };

  // Handle action initiation
  const handleAction = async (
    action: BulkActionType,
    options?: BulkActionOptions
  ) => {
    // Check if confirmation is required
    if (confirmationRequired.includes(action)) {
      const content = getConfirmationContent(action);
      setConfirmDialog({
        open: true,
        action,
        title: content.title,
        description: content.description,
        options,
      });
      return;
    }

    // Execute action directly
    await executeAction(action, options);
  };

  // Execute the bulk action
  const executeAction = async (
    action: BulkActionType,
    options?: BulkActionOptions
  ) => {
    setIsLoading(true);
    setProgress(0);
    setCurrentAction(getActionLabel(action));

    try {
      // Simulate progress for better UX on large batches
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + Math.random() * 15;
        });
      }, 200);

      const result = await onAction(action, selectedIds, options);

      clearInterval(progressInterval);
      setProgress(100);

      if (result.success) {
        toast({
          title: "Bulk action completed",
          description:
            result.message ||
            `Successfully processed ${result.processed} lead${result.processed !== 1 ? "s" : ""}`,
        });
        onClearSelection();
      } else {
        toast({
          title: "Bulk action partially completed",
          description:
            result.message ||
            `Processed ${result.processed}, failed ${result.failed}`,
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Bulk action failed",
        description:
          error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
      setProgress(0);
      setCurrentAction(null);
      setConfirmDialog({ ...confirmDialog, open: false });
    }
  };

  // Get human-readable label for an action
  const getActionLabel = (action: BulkActionType): string => {
    switch (action) {
      case "send_email":
        return "Sending emails";
      case "assign_campaign":
        return "Assigning to campaign";
      case "add_tag":
        return "Adding tags";
      case "update_status":
        return "Updating status";
      case "re_enrich":
        return "Re-enriching leads";
      case "export":
        return "Exporting to CSV";
      case "suppress":
        return "Suppressing leads";
      case "delete":
        return "Deleting leads";
      default:
        return "Processing";
    }
  };

  // Handle confirmation dialog confirm
  const handleConfirm = () => {
    executeAction(confirmDialog.action, confirmDialog.options);
  };

  return (
    <>
      <div
        className={`flex items-center gap-3 rounded-lg border bg-muted/50 px-3 py-2 ${className || ""}`}
      >
        {/* Selection indicator */}
        <div className="flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">
            {selectedCount} selected
          </span>
        </div>

        {/* Progress indicator during loading */}
        {isLoading && (
          <div className="flex items-center gap-2">
            <Progress value={progress} className="h-2 w-24" />
            <span className="text-xs text-muted-foreground">
              {currentAction}...
            </span>
          </div>
        )}

        {/* Actions dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              disabled={isLoading || disabled}
            >
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ChevronDown className="mr-2 h-4 w-4" />
              )}
              Actions
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            {/* Outreach actions */}
            <DropdownMenuItem
              onClick={() => handleAction("send_email")}
              disabled={isLoading}
            >
              <Mail className="mr-2 h-4 w-4" />
              Send Bulk Email
            </DropdownMenuItem>

            {/* Campaign assignment */}
            {campaigns.length > 0 && (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger disabled={isLoading}>
                  <ArrowRight className="mr-2 h-4 w-4" />
                  Assign to Campaign
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {campaigns.map((campaign) => (
                    <DropdownMenuItem
                      key={campaign.id}
                      onClick={() =>
                        handleAction("assign_campaign", {
                          campaignId: campaign.id,
                        })
                      }
                    >
                      {campaign.name}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            )}

            {/* Tag management */}
            {tags.length > 0 ? (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger disabled={isLoading}>
                  <Tag className="mr-2 h-4 w-4" />
                  Add Tag
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent>
                  {tags.map((tag) => (
                    <DropdownMenuItem
                      key={tag}
                      onClick={() =>
                        handleAction("add_tag", { tagName: tag })
                      }
                    >
                      {tag}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            ) : (
              <DropdownMenuItem
                onClick={() => handleAction("add_tag")}
                disabled={isLoading}
              >
                <Tag className="mr-2 h-4 w-4" />
                Add Tag
              </DropdownMenuItem>
            )}

            {/* Status update */}
            <DropdownMenuSub>
              <DropdownMenuSubTrigger disabled={isLoading}>
                <AlertCircle className="mr-2 h-4 w-4" />
                Update Status
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                <DropdownMenuItem
                  onClick={() =>
                    handleAction("update_status", { status: "new" })
                  }
                >
                  New
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleAction("update_status", { status: "enriched" })
                  }
                >
                  Enriched
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleAction("update_status", { status: "scored" })
                  }
                >
                  Scored
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleAction("update_status", { status: "in_sequence" })
                  }
                >
                  In Sequence
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() =>
                    handleAction("update_status", { status: "converted" })
                  }
                >
                  Converted
                </DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>

            <DropdownMenuSeparator />

            {/* Data operations */}
            <DropdownMenuItem
              onClick={() => handleAction("re_enrich")}
              disabled={isLoading}
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Re-enrich All
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => handleAction("export")}
              disabled={isLoading}
            >
              <Download className="mr-2 h-4 w-4" />
              Export to CSV
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            {/* Destructive actions */}
            <DropdownMenuItem
              onClick={() => handleAction("suppress")}
              disabled={isLoading}
              className="text-orange-600 focus:text-orange-600"
            >
              <UserX className="mr-2 h-4 w-4" />
              Suppress All
            </DropdownMenuItem>

            <DropdownMenuItem
              onClick={() => handleAction("delete")}
              disabled={isLoading}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete All
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Clear selection button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onClearSelection}
          disabled={isLoading}
        >
          <X className="mr-1 h-4 w-4" />
          Clear
        </Button>
      </div>

      {/* Confirmation Dialog */}
      <AlertDialog
        open={confirmDialog.open}
        onOpenChange={(open) =>
          setConfirmDialog({ ...confirmDialog, open })
        }
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirmDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog.description}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirm}
              disabled={isLoading}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                "Confirm"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export default LeadBulkActions;
