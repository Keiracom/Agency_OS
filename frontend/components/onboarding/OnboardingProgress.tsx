/**
 * FILE: frontend/components/onboarding/OnboardingProgress.tsx
 * PURPOSE: Main onboarding progress indicator with visual step flow
 * PHASE: Fix #33 - Onboarding Progress Components
 */

"use client";

import { cn } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { OnboardingStep, StepStatus } from "./OnboardingStep";
import { Check } from "lucide-react";

export interface OnboardingStepConfig {
  /** Unique step identifier */
  id: string;
  /** Step title */
  title: string;
  /** Optional step description */
  description?: string;
}

export interface OnboardingProgressProps {
  /** List of steps to display */
  steps: OnboardingStepConfig[];
  /** Index of the current step (0-indexed) */
  currentStepIndex: number;
  /** Optional loading state for current step */
  isLoading?: boolean;
  /** Display variant */
  variant?: "horizontal" | "vertical" | "compact";
  /** Optional title for the progress section */
  title?: string;
  /** Optional click handler for steps */
  onStepClick?: (stepId: string, index: number) => void;
  /** Additional class names */
  className?: string;
}

/**
 * Default onboarding steps for Agency OS
 */
export const DEFAULT_ONBOARDING_STEPS: OnboardingStepConfig[] = [
  {
    id: "account",
    title: "Account Setup",
    description: "Create your account and verify email",
  },
  {
    id: "email",
    title: "Connect Email",
    description: "Link your email for outreach campaigns",
  },
  {
    id: "team",
    title: "Add Team",
    description: "Invite team members to collaborate",
  },
  {
    id: "campaign",
    title: "Create Campaign",
    description: "Set up your first outreach campaign",
  },
  {
    id: "lead",
    title: "First Lead",
    description: "Add or import your first lead",
  },
];

export function OnboardingProgress({
  steps,
  currentStepIndex,
  isLoading = false,
  variant = "vertical",
  title = "Getting Started",
  onStepClick,
  className,
}: OnboardingProgressProps) {
  const completedCount = Math.min(currentStepIndex, steps.length);
  const progressPercent = (completedCount / steps.length) * 100;

  const getStepStatus = (index: number): StepStatus => {
    if (index < currentStepIndex) return "completed";
    if (index === currentStepIndex) return isLoading ? "loading" : "current";
    return "pending";
  };

  if (variant === "compact") {
    return (
      <div className={cn("w-full", className)}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium">{title}</span>
          <span className="text-sm text-muted-foreground">
            {completedCount}/{steps.length}
          </span>
        </div>
        <Progress value={progressPercent} className="h-2" />
        <p className="mt-2 text-sm text-muted-foreground">
          {currentStepIndex < steps.length
            ? `Next: ${steps[currentStepIndex].title}`
            : "All steps completed!"}
        </p>
      </div>
    );
  }

  if (variant === "horizontal") {
    return (
      <div className={cn("w-full", className)}>
        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">{title}</span>
            <span className="text-sm text-muted-foreground">
              {completedCount}/{steps.length} complete
            </span>
          </div>
          <Progress value={progressPercent} className="h-2" />
        </div>

        {/* Horizontal step indicators */}
        <div className="flex items-center justify-between">
          {steps.map((step, index) => {
            const status = getStepStatus(index);
            const isLast = index === steps.length - 1;

            return (
              <div key={step.id} className="flex flex-1 items-center">
                {/* Step circle */}
                <div
                  className={cn(
                    "flex flex-col items-center",
                    onStepClick && status !== "pending" && "cursor-pointer"
                  )}
                  onClick={() => {
                    if (onStepClick && status !== "pending") {
                      onStepClick(step.id, index);
                    }
                  }}
                >
                  <div
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors",
                      {
                        "border-primary bg-primary text-primary-foreground":
                          status === "completed",
                        "border-primary bg-background text-primary":
                          status === "current" || status === "loading",
                        "border-muted bg-muted text-muted-foreground":
                          status === "pending",
                      }
                    )}
                  >
                    {status === "completed" ? (
                      <Check className="h-5 w-5" />
                    ) : (
                      <span className="font-medium">{index + 1}</span>
                    )}
                  </div>
                  <span
                    className={cn("mt-2 text-xs text-center max-w-[80px]", {
                      "text-foreground font-medium": status === "current",
                      "text-muted-foreground": status !== "current",
                    })}
                  >
                    {step.title}
                  </span>
                </div>

                {/* Connector line */}
                {!isLast && (
                  <div
                    className={cn("h-0.5 flex-1 mx-2", {
                      "bg-primary": status === "completed",
                      "bg-muted": status !== "completed",
                    })}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Vertical variant (default)
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{title}</CardTitle>
          <span className="text-sm text-muted-foreground">
            {completedCount}/{steps.length} complete
          </span>
        </div>
        <Progress value={progressPercent} className="h-2" />
      </CardHeader>
      <CardContent>
        <div className="space-y-0">
          {steps.map((step, index) => (
            <OnboardingStep
              key={step.id}
              id={step.id}
              title={step.title}
              description={step.description}
              status={getStepStatus(index)}
              stepNumber={index + 1}
              isLast={index === steps.length - 1}
              onClick={
                onStepClick
                  ? () => onStepClick(step.id, index)
                  : undefined
              }
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default OnboardingProgress;
