/**
 * FILE: frontend/components/onboarding/index.ts
 * PURPOSE: Export all onboarding progress components
 * PHASE: Fix #33 - Onboarding Progress Components
 */

export {
  OnboardingProgress,
  DEFAULT_ONBOARDING_STEPS,
  type OnboardingProgressProps,
  type OnboardingStepConfig,
} from "./OnboardingProgress";

export {
  OnboardingStep,
  type OnboardingStepProps,
  type StepStatus,
} from "./OnboardingStep";

export {
  OnboardingChecklist,
  DEFAULT_CHECKLIST_ITEMS,
  type OnboardingChecklistProps,
  type ChecklistItem,
} from "./OnboardingChecklist";

// Re-export existing LinkedIn components for convenience
export { LinkedInCredentialForm } from "./LinkedInCredentialForm";
export { LinkedInTwoFactor } from "./LinkedInTwoFactor";
export { LinkedInConnecting } from "./LinkedInConnecting";
export { LinkedInSuccess } from "./LinkedInSuccess";
