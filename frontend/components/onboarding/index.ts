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

// LinkedIn OAuth success state (credential-based components removed in #309)
export { LinkedInSuccess } from "./LinkedInSuccess";
