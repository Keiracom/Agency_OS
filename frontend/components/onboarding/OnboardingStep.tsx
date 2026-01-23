/**
 * FILE: frontend/components/onboarding/OnboardingStep.tsx
 * PURPOSE: Individual onboarding step component with visual status indicator
 * PHASE: Fix #33 - Onboarding Progress Components
 */

"use client";

import { cn } from "@/lib/utils";
import { Check, Circle, Loader2 } from "lucide-react";

export type StepStatus = "pending" | "current" | "completed" | "loading";

export interface OnboardingStepProps {
  /** Unique step identifier */
  id: string;
  /** Step title */
  title: string;
  /** Optional step description */
  description?: string;
  /** Step status */
  status: StepStatus;
  /** Step number (1-indexed) */
  stepNumber: number;
  /** Whether this is the last step */
  isLast?: boolean;
  /** Optional click handler */
  onClick?: () => void;
  /** Additional class names */
  className?: string;
}

export function OnboardingStep({
  title,
  description,
  status,
  stepNumber,
  isLast = false,
  onClick,
  className,
}: OnboardingStepProps) {
  const isClickable = onClick && (status === "completed" || status === "current");

  return (
    <div
      className={cn(
        "flex gap-4",
        isClickable && "cursor-pointer",
        className
      )}
      onClick={isClickable ? onClick : undefined}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
    >
      {/* Step indicator column */}
      <div className="flex flex-col items-center">
        <StepIndicator status={status} stepNumber={stepNumber} />
        {!isLast && <StepConnector status={status} />}
      </div>

      {/* Step content */}
      <div className="flex-1 pb-8">
        <h4
          className={cn("font-medium leading-none", {
            "text-foreground": status === "current" || status === "completed",
            "text-muted-foreground": status === "pending",
          })}
        >
          {title}
        </h4>
        {description && (
          <p
            className={cn("mt-1.5 text-sm", {
              "text-muted-foreground": true,
            })}
          >
            {description}
          </p>
        )}
      </div>
    </div>
  );
}

interface StepIndicatorProps {
  status: StepStatus;
  stepNumber: number;
}

function StepIndicator({ status, stepNumber }: StepIndicatorProps) {
  const baseClasses =
    "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors";

  if (status === "completed") {
    return (
      <div className={cn(baseClasses, "border-primary bg-primary text-primary-foreground")}>
        <Check className="h-4 w-4" />
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className={cn(baseClasses, "border-primary bg-background")}>
        <Loader2 className="h-4 w-4 animate-spin text-primary" />
      </div>
    );
  }

  if (status === "current") {
    return (
      <div className={cn(baseClasses, "border-primary bg-background")}>
        <Circle className="h-3 w-3 fill-primary text-primary" />
      </div>
    );
  }

  // pending
  return (
    <div className={cn(baseClasses, "border-muted bg-muted text-muted-foreground")}>
      <span className="text-sm font-medium">{stepNumber}</span>
    </div>
  );
}

interface StepConnectorProps {
  status: StepStatus;
}

function StepConnector({ status }: StepConnectorProps) {
  return (
    <div
      className={cn("mt-2 h-full min-h-[2rem] w-0.5", {
        "bg-primary": status === "completed",
        "bg-muted": status !== "completed",
      })}
    />
  );
}

export default OnboardingStep;
