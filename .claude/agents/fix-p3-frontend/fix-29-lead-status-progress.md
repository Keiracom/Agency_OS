---
name: Fix 29 - LeadStatusProgress Component
description: Creates LeadStatusProgress component showing lead funnel position
model: claude-sonnet-4-5-20250929
tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
---

# Fix 29: LeadStatusProgress Component Missing

## Gap Reference
- **TODO.md Item:** #29
- **Priority:** P3 Medium (Frontend Components)
- **Location:** `frontend/components/leads/`
- **Issue:** Component planned but not created

## Pre-Flight Checks

1. Check if component exists:
   ```bash
   ls frontend/components/leads/LeadStatusProgress.tsx
   ```

2. Check lead status enum/types:
   ```bash
   grep -rn "LeadStatus\|status.*enum" frontend/lib/api/types.ts
   ```

3. Check existing progress/stepper patterns:
   ```bash
   grep -rn "Progress\|Stepper\|Step" frontend/components/
   ```

## Implementation Steps

1. **Create LeadStatusProgress.tsx:**
   ```typescript
   // frontend/components/leads/LeadStatusProgress.tsx
   "use client";

   import { cn } from "@/lib/utils";
   import { Check, Circle, Loader2 } from "lucide-react";

   type LeadStatus =
     | "new"
     | "enriched"
     | "contacted"
     | "engaged"
     | "responded"
     | "qualified"
     | "converted"
     | "lost";

   interface LeadStatusProgressProps {
     currentStatus: LeadStatus;
     className?: string;
     showLabels?: boolean;
     size?: "sm" | "md" | "lg";
   }

   const STATUS_ORDER: LeadStatus[] = [
     "new",
     "enriched",
     "contacted",
     "engaged",
     "responded",
     "qualified",
     "converted",
   ];

   const STATUS_LABELS: Record<LeadStatus, string> = {
     new: "New",
     enriched: "Enriched",
     contacted: "Contacted",
     engaged: "Engaged",
     responded: "Responded",
     qualified: "Qualified",
     converted: "Converted",
     lost: "Lost",
   };

   const STATUS_DESCRIPTIONS: Record<LeadStatus, string> = {
     new: "Lead added to system",
     enriched: "Data enriched",
     contacted: "First outreach sent",
     engaged: "Opened/clicked",
     responded: "Replied to outreach",
     qualified: "Meeting scheduled",
     converted: "Deal closed",
     lost: "Lead lost",
   };

   export function LeadStatusProgress({
     currentStatus,
     className,
     showLabels = true,
     size = "md",
   }: LeadStatusProgressProps) {
     // Handle "lost" status specially
     if (currentStatus === "lost") {
       return (
         <div className={cn("flex items-center gap-2", className)}>
           <div className="flex h-6 w-6 items-center justify-center rounded-full bg-red-100 text-red-600">
             <Circle className="h-3 w-3 fill-current" />
           </div>
           <span className="text-sm font-medium text-red-600">Lost</span>
         </div>
       );
     }

     const currentIndex = STATUS_ORDER.indexOf(currentStatus);

     const sizeClasses = {
       sm: { step: "h-4 w-4", icon: "h-2 w-2", line: "h-0.5", text: "text-xs" },
       md: { step: "h-6 w-6", icon: "h-3 w-3", line: "h-1", text: "text-sm" },
       lg: { step: "h-8 w-8", icon: "h-4 w-4", line: "h-1.5", text: "text-base" },
     };

     const sizes = sizeClasses[size];

     return (
       <div className={cn("w-full", className)}>
         <div className="flex items-center justify-between">
           {STATUS_ORDER.map((status, index) => {
             const isComplete = index < currentIndex;
             const isCurrent = index === currentIndex;
             const isPending = index > currentIndex;

             return (
               <div key={status} className="flex flex-1 items-center">
                 {/* Step circle */}
                 <div
                   className={cn(
                     "flex items-center justify-center rounded-full transition-colors",
                     sizes.step,
                     {
                       "bg-primary text-primary-foreground": isComplete,
                       "bg-primary text-primary-foreground ring-2 ring-primary ring-offset-2":
                         isCurrent,
                       "bg-muted text-muted-foreground": isPending,
                     }
                   )}
                   title={STATUS_DESCRIPTIONS[status]}
                 >
                   {isComplete ? (
                     <Check className={sizes.icon} />
                   ) : isCurrent ? (
                     <Loader2 className={cn(sizes.icon, "animate-spin")} />
                   ) : (
                     <Circle className={sizes.icon} />
                   )}
                 </div>

                 {/* Connector line */}
                 {index < STATUS_ORDER.length - 1 && (
                   <div
                     className={cn("flex-1 mx-1", sizes.line, {
                       "bg-primary": index < currentIndex,
                       "bg-muted": index >= currentIndex,
                     })}
                   />
                 )}
               </div>
             );
           })}
         </div>

         {/* Labels */}
         {showLabels && (
           <div className="mt-2 flex justify-between">
             {STATUS_ORDER.map((status, index) => {
               const isCurrent = index === currentIndex;
               return (
                 <div
                   key={status}
                   className={cn(
                     "flex-1 text-center",
                     sizes.text,
                     isCurrent
                       ? "font-medium text-foreground"
                       : "text-muted-foreground"
                   )}
                 >
                   {STATUS_LABELS[status]}
                 </div>
               );
             })}
           </div>
         )}
       </div>
     );
   }
   ```

2. **Export from index:**
   ```typescript
   export { LeadStatusProgress } from "./LeadStatusProgress";
   ```

## Acceptance Criteria

- [ ] LeadStatusProgress.tsx created
- [ ] Shows all funnel stages as steps
- [ ] Highlights current status
- [ ] Shows completed stages with checkmark
- [ ] Shows pending stages as muted
- [ ] Handles "lost" status specially (red)
- [ ] Supports multiple sizes (sm, md, lg)
- [ ] Optional labels
- [ ] Tooltips with descriptions
- [ ] Exported from index.ts

## Validation

```bash
# Check file exists
ls frontend/components/leads/LeadStatusProgress.tsx

# Check TypeScript compiles
cd frontend && npx tsc --noEmit

# Check export
grep "LeadStatusProgress" frontend/components/leads/index.ts
```

## Post-Fix

1. Update TODO.md — delete gap row #29
2. Report: "Fixed #29. LeadStatusProgress component created with funnel visualization."
