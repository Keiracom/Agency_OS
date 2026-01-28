---
name: Fix 33 - Onboarding Progress Components
description: Creates onboarding progress indicator components
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 33: Onboarding Progress Components Missing

## Gap Reference
- **TODO.md Item:** #33
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/components/onboarding/`
- **Issue:** Progress indicators missing

## Pre-Flight Checks

1. Check if components exist:
   ```bash
   ls frontend/components/onboarding/
   ```

2. Review ONBOARDING.md for spec:
   ```bash
   cat frontend/ONBOARDING.md
   ```

3. Check existing onboarding flow:
   ```bash
   ls frontend/app/onboarding/
   ```

## Implementation Steps

1. **Create directory:**
   ```bash
   mkdir -p frontend/components/onboarding
   ```

2. **Create OnboardingProgress.tsx:**
   ```typescript
   // frontend/components/onboarding/OnboardingProgress.tsx
   "use client";

   import { cn } from "@/lib/utils";
   import { Check, Circle } from "lucide-react";

   interface OnboardingStep {
     id: string;
     title: string;
     description?: string;
   }

   interface OnboardingProgressProps {
     steps: OnboardingStep[];
     currentStepIndex: number;
     className?: string;
     variant?: "horizontal" | "vertical";
   }

   export function OnboardingProgress({
     steps,
     currentStepIndex,
     className,
     variant = "horizontal",
   }: OnboardingProgressProps) {
     if (variant === "vertical") {
       return (
         <div className={cn("space-y-4", className)}>
           {steps.map((step, index) => {
             const isComplete = index < currentStepIndex;
             const isCurrent = index === currentStepIndex;
             const isPending = index > currentStepIndex;

             return (
               <div key={step.id} className="flex gap-4">
                 {/* Step indicator */}
                 <div className="flex flex-col items-center">
                   <div
                     className={cn(
                       "flex h-8 w-8 items-center justify-center rounded-full border-2",
                       {
                         "border-primary bg-primary text-primary-foreground":
                           isComplete,
                         "border-primary bg-background": isCurrent,
                         "border-muted bg-muted": isPending,
                       }
                     )}
                   >
                     {isComplete ? (
                       <Check className="h-4 w-4" />
                     ) : (
                       <span className="text-sm font-medium">{index + 1}</span>
                     )}
                   </div>
                   {index < steps.length - 1 && (
                     <div
                       className={cn("mt-2 h-12 w-0.5", {
                         "bg-primary": isComplete,
                         "bg-muted": !isComplete,
                       })}
                     />
                   )}
                 </div>

                 {/* Step content */}
                 <div className="flex-1 pt-1">
                   <h4
                     className={cn("font-medium", {
                       "text-foreground": isCurrent || isComplete,
                       "text-muted-foreground": isPending,
                     })}
                   >
                     {step.title}
                   </h4>
                   {step.description && (
                     <p className="mt-1 text-sm text-muted-foreground">
                       {step.description}
                     </p>
                   )}
                 </div>
               </div>
             );
           })}
         </div>
       );
     }

     // Horizontal variant
     return (
       <div className={cn("w-full", className)}>
         <div className="flex items-center justify-between">
           {steps.map((step, index) => {
             const isComplete = index < currentStepIndex;
             const isCurrent = index === currentStepIndex;

             return (
               <div key={step.id} className="flex flex-1 items-center">
                 {/* Step circle */}
                 <div
                   className={cn(
                     "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors",
                     {
                       "border-primary bg-primary text-primary-foreground":
                         isComplete,
                       "border-primary bg-background text-primary": isCurrent,
                       "border-muted bg-muted text-muted-foreground":
                         !isComplete && !isCurrent,
                     }
                   )}
                 >
                   {isComplete ? (
                     <Check className="h-5 w-5" />
                   ) : (
                     <span className="font-medium">{index + 1}</span>
                   )}
                 </div>

                 {/* Connector line */}
                 {index < steps.length - 1 && (
                   <div
                     className={cn("h-1 flex-1 mx-2", {
                       "bg-primary": isComplete,
                       "bg-muted": !isComplete,
                     })}
                   />
                 )}
               </div>
             );
           })}
         </div>

         {/* Labels */}
         <div className="mt-4 flex justify-between">
           {steps.map((step, index) => {
             const isCurrent = index === currentStepIndex;
             return (
               <div
                 key={step.id}
                 className={cn("flex-1 text-center", {
                   "text-foreground font-medium": isCurrent,
                   "text-muted-foreground": !isCurrent,
                 })}
               >
                 <span className="text-sm">{step.title}</span>
               </div>
             );
           })}
         </div>
       </div>
     );
   }
   ```

3. **Create OnboardingChecklist.tsx:**
   ```typescript
   // frontend/components/onboarding/OnboardingChecklist.tsx
   "use client";

   import { cn } from "@/lib/utils";
   import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
   import { Progress } from "@/components/ui/progress";
   import { Check, Circle, ArrowRight } from "lucide-react";
   import Link from "next/link";

   interface ChecklistItem {
     id: string;
     title: string;
     description?: string;
     completed: boolean;
     href?: string;
   }

   interface OnboardingChecklistProps {
     title?: string;
     items: ChecklistItem[];
     className?: string;
   }

   export function OnboardingChecklist({
     title = "Getting Started",
     items,
     className,
   }: OnboardingChecklistProps) {
     const completedCount = items.filter((item) => item.completed).length;
     const progress = (completedCount / items.length) * 100;

     return (
       <Card className={className}>
         <CardHeader>
           <div className="flex items-center justify-between">
             <CardTitle className="text-base">{title}</CardTitle>
             <span className="text-sm text-muted-foreground">
               {completedCount}/{items.length} complete
             </span>
           </div>
           <Progress value={progress} className="h-2" />
         </CardHeader>
         <CardContent>
           <ul className="space-y-3">
             {items.map((item) => (
               <li key={item.id}>
                 {item.href && !item.completed ? (
                   <Link
                     href={item.href}
                     className="flex items-center gap-3 rounded-lg p-2 hover:bg-muted transition-colors"
                   >
                     <ChecklistItemContent item={item} />
                     <ArrowRight className="h-4 w-4 text-muted-foreground ml-auto" />
                   </Link>
                 ) : (
                   <div className="flex items-center gap-3 p-2">
                     <ChecklistItemContent item={item} />
                   </div>
                 )}
               </li>
             ))}
           </ul>
         </CardContent>
       </Card>
     );
   }

   function ChecklistItemContent({ item }: { item: ChecklistItem }) {
     return (
       <>
         <div
           className={cn(
             "flex h-6 w-6 items-center justify-center rounded-full",
             item.completed
               ? "bg-green-100 text-green-600"
               : "bg-muted text-muted-foreground"
           )}
         >
           {item.completed ? (
             <Check className="h-4 w-4" />
           ) : (
             <Circle className="h-4 w-4" />
           )}
         </div>
         <div className="flex-1">
           <span
             className={cn("font-medium", {
               "line-through text-muted-foreground": item.completed,
             })}
           >
             {item.title}
           </span>
           {item.description && (
             <p className="text-sm text-muted-foreground">{item.description}</p>
           )}
         </div>
       </>
     );
   }
   ```

4. **Create index.ts:**
   ```typescript
   // frontend/components/onboarding/index.ts
   export { OnboardingProgress } from "./OnboardingProgress";
   export { OnboardingChecklist } from "./OnboardingChecklist";
   ```

## Acceptance Criteria

- [ ] OnboardingProgress.tsx created
- [ ] Supports horizontal and vertical variants
- [ ] Shows completed, current, pending states
- [ ] Step numbers and checkmarks
- [ ] OnboardingChecklist.tsx created
- [ ] Shows checklist with progress bar
- [ ] Links for incomplete items
- [ ] Exported from index.ts

## Validation

```bash
# Check files exist
ls frontend/components/onboarding/OnboardingProgress.tsx
ls frontend/components/onboarding/OnboardingChecklist.tsx
ls frontend/components/onboarding/index.ts

# Check TypeScript compiles
cd frontend && npx tsc --noEmit
```

## Post-Fix

1. Update TODO.md — delete gap row #33
2. Report: "Fixed #33. Onboarding progress components created (Progress + Checklist)."
