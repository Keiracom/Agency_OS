/**
 * FILE: frontend/components/campaigns/SequenceBuilder.tsx
 * PURPOSE: Visual sequence editor for campaign outreach steps
 * PHASE: Phase I Dashboard Redesign (Item 56)
 *
 * Features:
 * - Timeline view of sequence steps
 * - Add new steps via modal
 * - Edit existing steps via modal
 * - Delete existing steps with confirmation
 * - Configure delay between steps
 * - Preview content at each step
 * - Channel selection per step
 * - Read-only mode for viewing
 *
 * Future enhancements:
 * - Drag-and-drop reordering
 */

"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  Plus,
  Trash2,
  Pencil,
  Mail,
  MessageSquare,
  Linkedin,
  Phone,
  Clock,
  ChevronDown,
  AlertCircle,
} from "lucide-react";
import {
  useCampaignSequences,
  useCreateSequenceStep,
  useUpdateSequenceStep,
  useDeleteSequenceStep,
} from "@/hooks/use-campaigns";
import type { SequenceStep, ChannelType, SequenceStepCreate, SequenceStepUpdate } from "@/lib/api/types";

// ============================================
// Types
// ============================================

export interface SequenceBuilderProps {
  /** Campaign ID to load sequences for */
  campaignId: string;
  /** Whether the builder is read-only */
  isReadOnly?: boolean;
  /** Additional class names */
  className?: string;
}

// ============================================
// Channel Configuration
// ============================================

const CHANNEL_CONFIG: Record<
  ChannelType,
  { label: string; icon: React.ReactNode; color: string }
> = {
  email: {
    label: "Email",
    icon: <Mail className="h-4 w-4" />,
    color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  sms: {
    label: "SMS",
    icon: <MessageSquare className="h-4 w-4" />,
    color: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  },
  linkedin: {
    label: "LinkedIn",
    icon: <Linkedin className="h-4 w-4" />,
    color: "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400",
  },
  voice: {
    label: "Voice",
    icon: <Phone className="h-4 w-4" />,
    color: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  },
  mail: {
    label: "Direct Mail",
    icon: <Mail className="h-4 w-4" />,
    color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  },
};

// ============================================
// Main Component
// ============================================

/**
 * SequenceBuilder displays and manages campaign outreach sequence steps.
 *
 * Shows a timeline view of all steps with the ability to add and remove steps.
 * Future versions will support drag-and-drop reordering and inline editing.
 */
export function SequenceBuilder({
  campaignId,
  isReadOnly = false,
  className,
}: SequenceBuilderProps) {
  const { data: sequences, isLoading, error } = useCampaignSequences(campaignId);
  const [isAddDialogOpen, setIsAddDialogOpen] = React.useState(false);

  // Loading state
  if (isLoading) {
    return <SequenceBuilderSkeleton className={className} />;
  }

  // Error state
  if (error) {
    return (
      <Card className={cn("w-full", className)}>
        <CardContent className="py-8">
          <div className="flex flex-col items-center justify-center text-center">
            <AlertCircle className="h-10 w-10 text-destructive mb-4" />
            <h3 className="text-lg font-medium mb-2">Failed to load sequence</h3>
            <p className="text-sm text-muted-foreground">
              Please try refreshing the page.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const steps = sequences || [];
  const nextStepNumber = steps.length > 0
    ? Math.max(...steps.map(s => s.step_number)) + 1
    : 1;

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <CardTitle className="text-lg">Outreach Sequence</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            {steps.length} step{steps.length !== 1 ? "s" : ""} in this sequence
          </p>
        </div>
        {!isReadOnly && (
          <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Plus className="h-4 w-4 mr-1" />
                Add Step
              </Button>
            </DialogTrigger>
            <AddStepDialog
              campaignId={campaignId}
              nextStepNumber={nextStepNumber}
              onSuccess={() => setIsAddDialogOpen(false)}
            />
          </Dialog>
        )}
      </CardHeader>

      <CardContent>
        {steps.length === 0 ? (
          <EmptySequence isReadOnly={isReadOnly} onAdd={() => setIsAddDialogOpen(true)} />
        ) : (
          <SequenceTimeline
            steps={steps}
            campaignId={campaignId}
            isReadOnly={isReadOnly}
          />
        )}
      </CardContent>
    </Card>
  );
}

// ============================================
// Empty State
// ============================================

function EmptySequence({
  isReadOnly,
  onAdd,
}: {
  isReadOnly: boolean;
  onAdd: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <div className="rounded-full bg-muted p-3 mb-4">
        <Clock className="h-6 w-6 text-muted-foreground" />
      </div>
      <h3 className="text-base font-medium mb-2">No sequence steps yet</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        {isReadOnly
          ? "This campaign has no outreach sequence configured."
          : "Add steps to define your outreach sequence. Each step can use a different channel."}
      </p>
      {!isReadOnly && (
        <Button onClick={onAdd}>
          <Plus className="h-4 w-4 mr-1" />
          Add First Step
        </Button>
      )}
    </div>
  );
}

// ============================================
// Timeline View
// ============================================

function SequenceTimeline({
  steps,
  campaignId,
  isReadOnly,
}: {
  steps: SequenceStep[];
  campaignId: string;
  isReadOnly: boolean;
}) {
  const sortedSteps = [...steps].sort((a, b) => a.step_number - b.step_number);

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-border" />

      {/* Steps */}
      <div className="space-y-4">
        {sortedSteps.map((step, index) => (
          <SequenceStepCard
            key={step.id}
            step={step}
            campaignId={campaignId}
            isFirst={index === 0}
            isReadOnly={isReadOnly}
          />
        ))}
      </div>
    </div>
  );
}

// ============================================
// Step Card
// ============================================

function SequenceStepCard({
  step,
  campaignId,
  isFirst,
  isReadOnly,
}: {
  step: SequenceStep;
  campaignId: string;
  isFirst: boolean;
  isReadOnly: boolean;
}) {
  const deleteStep = useDeleteSequenceStep(campaignId);
  const channelConfig = CHANNEL_CONFIG[step.channel] || CHANNEL_CONFIG.email;
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = React.useState(false);

  return (
    <div className="relative pl-12">
      {/* Timeline node */}
      <div
        className={cn(
          "absolute left-4 w-5 h-5 rounded-full border-2 border-background",
          channelConfig.color.split(" ")[0] // Use first color class for background
        )}
      />

      {/* Delay indicator (except for first step) */}
      {!isFirst && (
        <div className="absolute left-12 -top-3 text-xs text-muted-foreground flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Wait {step.delay_days} day{step.delay_days !== 1 ? "s" : ""}
        </div>
      )}

      {/* Step card */}
      <div className="border rounded-lg p-4 bg-card">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className={cn("gap-1", channelConfig.color)}>
              {channelConfig.icon}
              {channelConfig.label}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Step {step.step_number}
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 w-8 p-0"
            >
              <ChevronDown
                className={cn(
                  "h-4 w-4 transition-transform",
                  isExpanded && "rotate-180"
                )}
              />
            </Button>
            {!isReadOnly && (
              <>
                {/* Edit button */}
                <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
                  <DialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </DialogTrigger>
                  <EditStepDialog
                    campaignId={campaignId}
                    step={step}
                    onSuccess={() => setIsEditDialogOpen(false)}
                  />
                </Dialog>

                {/* Delete button */}
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete Step {step.step_number}?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will permanently remove this step from the sequence.
                        This action cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={() => deleteStep.mutate(step.step_number)}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
                        Delete
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </>
            )}
          </div>
        </div>

        {/* Subject (for email) */}
        {step.channel === "email" && step.subject_template && (
          <p className="text-sm font-medium mb-1 truncate">
            {step.subject_template}
          </p>
        )}

        {/* Content preview */}
        <p
          className={cn(
            "text-sm text-muted-foreground",
            !isExpanded && "line-clamp-2"
          )}
        >
          {step.body_template}
        </p>

        {/* Expanded details */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t space-y-2">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              {step.skip_if_replied && (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Skip if replied
                </span>
              )}
              {step.skip_if_bounced && (
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                  Skip if bounced
                </span>
              )}
            </div>
            {step.purpose && (
              <p className="text-xs text-muted-foreground">
                <strong>Purpose:</strong> {step.purpose}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================
// Add Step Dialog
// ============================================

function AddStepDialog({
  campaignId,
  nextStepNumber,
  onSuccess,
}: {
  campaignId: string;
  nextStepNumber: number;
  onSuccess: () => void;
}) {
  const createStep = useCreateSequenceStep(campaignId);
  const [formData, setFormData] = React.useState<SequenceStepCreate>({
    step_number: nextStepNumber,
    channel: "email",
    delay_days: 3,
    body_template: "",
    skip_if_replied: true,
    skip_if_bounced: true,
  });
  const [subjectTemplate, setSubjectTemplate] = React.useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data: SequenceStepCreate = {
      ...formData,
      subject_template: formData.channel === "email" ? subjectTemplate : undefined,
    };

    try {
      await createStep.mutateAsync(data);
      onSuccess();
      // Reset form
      setFormData({
        step_number: nextStepNumber + 1,
        channel: "email",
        delay_days: 3,
        body_template: "",
        skip_if_replied: true,
        skip_if_bounced: true,
      });
      setSubjectTemplate("");
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <DialogContent className="sm:max-w-lg">
      <form onSubmit={handleSubmit}>
        <DialogHeader>
          <DialogTitle>Add Sequence Step</DialogTitle>
          <DialogDescription>
            Configure the next step in your outreach sequence.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Channel */}
          <div className="grid gap-2">
            <Label htmlFor="channel">Channel</Label>
            <Select
              value={formData.channel}
              onValueChange={(value: ChannelType) =>
                setFormData({ ...formData, channel: value })
              }
            >
              <SelectTrigger id="channel">
                <SelectValue placeholder="Select channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="email">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4" />
                    Email
                  </div>
                </SelectItem>
                <SelectItem value="sms">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    SMS
                  </div>
                </SelectItem>
                <SelectItem value="linkedin">
                  <div className="flex items-center gap-2">
                    <Linkedin className="h-4 w-4" />
                    LinkedIn
                  </div>
                </SelectItem>
                <SelectItem value="voice">
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4" />
                    Voice
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Delay */}
          <div className="grid gap-2">
            <Label htmlFor="delay">Wait (days before this step)</Label>
            <Input
              id="delay"
              type="number"
              min={0}
              max={30}
              value={formData.delay_days}
              onChange={(e) =>
                setFormData({ ...formData, delay_days: parseInt(e.target.value) || 0 })
              }
            />
          </div>

          {/* Subject (email only) */}
          {formData.channel === "email" && (
            <div className="grid gap-2">
              <Label htmlFor="subject">Subject Line</Label>
              <Input
                id="subject"
                placeholder="Enter email subject..."
                value={subjectTemplate}
                onChange={(e) => setSubjectTemplate(e.target.value)}
              />
            </div>
          )}

          {/* Body */}
          <div className="grid gap-2">
            <Label htmlFor="body">
              {formData.channel === "email" ? "Email Body" : "Message"}
            </Label>
            <Textarea
              id="body"
              placeholder="Enter your message..."
              value={formData.body_template}
              onChange={(e) =>
                setFormData({ ...formData, body_template: e.target.value })
              }
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              Use {"{{first_name}}"}, {"{{company}}"}, etc. for personalization.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="submit"
            disabled={createStep.isPending || !formData.body_template.trim()}
          >
            {createStep.isPending ? "Adding..." : "Add Step"}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  );
}

// ============================================
// Edit Step Dialog
// ============================================

function EditStepDialog({
  campaignId,
  step,
  onSuccess,
}: {
  campaignId: string;
  step: SequenceStep;
  onSuccess: () => void;
}) {
  const updateStep = useUpdateSequenceStep(campaignId);
  const [formData, setFormData] = React.useState<SequenceStepUpdate>({
    channel: step.channel,
    delay_days: step.delay_days,
    body_template: step.body_template,
    skip_if_replied: step.skip_if_replied,
    skip_if_bounced: step.skip_if_bounced,
  });
  const [subjectTemplate, setSubjectTemplate] = React.useState(
    step.subject_template || ""
  );

  // Reset form when step changes
  React.useEffect(() => {
    setFormData({
      channel: step.channel,
      delay_days: step.delay_days,
      body_template: step.body_template,
      skip_if_replied: step.skip_if_replied,
      skip_if_bounced: step.skip_if_bounced,
    });
    setSubjectTemplate(step.subject_template || "");
  }, [step]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data: SequenceStepUpdate = {
      ...formData,
      subject_template: formData.channel === "email" ? subjectTemplate : undefined,
    };

    try {
      await updateStep.mutateAsync({
        stepNumber: step.step_number,
        data,
      });
      onSuccess();
    } catch {
      // Error handled by mutation
    }
  };

  return (
    <DialogContent className="sm:max-w-lg">
      <form onSubmit={handleSubmit}>
        <DialogHeader>
          <DialogTitle>Edit Step {step.step_number}</DialogTitle>
          <DialogDescription>
            Update this step in your outreach sequence.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          {/* Channel */}
          <div className="grid gap-2">
            <Label htmlFor="edit-channel">Channel</Label>
            <Select
              value={formData.channel}
              onValueChange={(value: ChannelType) =>
                setFormData({ ...formData, channel: value })
              }
            >
              <SelectTrigger id="edit-channel">
                <SelectValue placeholder="Select channel" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="email">
                  <div className="flex items-center gap-2">
                    <Mail className="h-4 w-4" />
                    Email
                  </div>
                </SelectItem>
                <SelectItem value="sms">
                  <div className="flex items-center gap-2">
                    <MessageSquare className="h-4 w-4" />
                    SMS
                  </div>
                </SelectItem>
                <SelectItem value="linkedin">
                  <div className="flex items-center gap-2">
                    <Linkedin className="h-4 w-4" />
                    LinkedIn
                  </div>
                </SelectItem>
                <SelectItem value="voice">
                  <div className="flex items-center gap-2">
                    <Phone className="h-4 w-4" />
                    Voice
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Delay */}
          <div className="grid gap-2">
            <Label htmlFor="edit-delay">Wait (days before this step)</Label>
            <Input
              id="edit-delay"
              type="number"
              min={0}
              max={30}
              value={formData.delay_days}
              onChange={(e) =>
                setFormData({ ...formData, delay_days: parseInt(e.target.value) || 0 })
              }
            />
          </div>

          {/* Subject (email only) */}
          {formData.channel === "email" && (
            <div className="grid gap-2">
              <Label htmlFor="edit-subject">Subject Line</Label>
              <Input
                id="edit-subject"
                placeholder="Enter email subject..."
                value={subjectTemplate}
                onChange={(e) => setSubjectTemplate(e.target.value)}
              />
            </div>
          )}

          {/* Body */}
          <div className="grid gap-2">
            <Label htmlFor="edit-body">
              {formData.channel === "email" ? "Email Body" : "Message"}
            </Label>
            <Textarea
              id="edit-body"
              placeholder="Enter your message..."
              value={formData.body_template}
              onChange={(e) =>
                setFormData({ ...formData, body_template: e.target.value })
              }
              rows={4}
            />
            <p className="text-xs text-muted-foreground">
              Use {"{{first_name}}"}, {"{{company}}"}, etc. for personalization.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button
            type="submit"
            disabled={updateStep.isPending || !formData.body_template?.trim()}
          >
            {updateStep.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  );
}

// ============================================
// Loading Skeleton
// ============================================

function SequenceBuilderSkeleton({ className }: { className?: string }) {
  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
        <div>
          <Skeleton className="h-6 w-40 mb-2" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-9 w-24" />
      </CardHeader>
      <CardContent>
        <div className="relative pl-12 space-y-4">
          <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-border" />
          {[1, 2, 3].map((i) => (
            <div key={i} className="relative">
              <Skeleton className="absolute left-4 w-5 h-5 rounded-full" />
              <div className="border rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default SequenceBuilder;
